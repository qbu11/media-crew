"""
发布脚本：直接调用平台工具层发布内容到草稿箱。

跳过 CrewAI agent 的 LLM 开销，直接使用 WechatTool / XiaohongshuTool。

Usage:
    uv run python scripts/run_publish.py --platform wechat --input data/outputs/20260324_185208/wechat/article.html
    uv run python scripts/run_publish.py --platform xiaohongshu --input data/outputs/20260324_185208/xiaohongshu/note.md
    uv run python scripts/run_publish.py --platform all --input-dir data/outputs/20260324_185208/
"""

# 修复 Windows GBK 编码问题
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.platform.base import ContentType, PublishContent
from src.tools.platform.wechat import WechatTool
from src.tools.platform.xiaohongshu import XiaohongshuTool


def publish_wechat(html_path: str, metadata_path: str | None = None, use_browser: bool = False) -> dict:
    """发布微信公众号文章到草稿箱。"""
    html_file = Path(html_path)
    if not html_file.exists():
        return {"success": False, "error": f"File not found: {html_path}"}

    html_content = html_file.read_text(encoding="utf-8")

    # Extract body from HTML
    import re
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html_content, re.DOTALL)
    body = body_match.group(1).strip() if body_match else html_content

    # Extract title
    title_match = re.search(r"<title>([^<]+)</title>", html_content)
    title = title_match.group(1) if title_match else ""

    # Extract summary from meta
    summary_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html_content)
    summary = summary_match.group(1) if summary_match else ""

    # Load metadata if available
    if metadata_path:
        meta_file = Path(metadata_path)
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            title = meta.get("title") or title
            summary = meta.get("summary") or summary

    content = PublishContent(
        title=title,
        body=body,
        content_type=ContentType.ARTICLE,
        custom_fields={"summary": summary},
    )

    # Use browser method if requested (fallback when API fails due to IP whitelist)
    config = {"publish_method": "browser"} if use_browser else {}
    tool = WechatTool(config)
    print(f"[wechat] Publishing: {title[:40]}...")
    print(f"[wechat] Method: {tool._publish_method}")
    if tool._publish_method == "api":
        print(f"[wechat] Credentials: {'OK' if tool._has_api_credentials() else 'MISSING'}")

    result = tool.publish(content)

    result = tool.publish(content)

    if result.is_success():
        print(f"[wechat] [OK] Draft saved! media_id: {result.content_id}")
        print(f"[wechat] Manage: https://mp.weixin.qq.com")
        return {"success": True, "media_id": result.content_id, "platform": "wechat"}
    else:
        print(f"[wechat] [FAIL] Failed: {result.error}")
        return {"success": False, "error": result.error, "platform": "wechat"}


def publish_xiaohongshu(
    note_path: str,
    metadata_path: str | None = None,
    images: list[str] | None = None,
) -> dict:
    """发布小红书笔记到草稿箱（通过 Chrome CDP 自动化）。"""
    note_file = Path(note_path)
    if not note_file.exists():
        return {"success": False, "error": f"File not found: {note_path}"}

    note_content = note_file.read_text(encoding="utf-8")

    title = ""
    tags: list[str] = []
    summary = ""

    if metadata_path:
        meta_file = Path(metadata_path)
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            title = meta.get("title", "")
            tags = meta.get("tags", [])
            summary = meta.get("summary", "")

    if not title:
        # Try to extract title from markdown (# Title format)
        import re
        title_match = re.search(r'^#\s+(.+)$', note_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            lines = note_content.strip().split("\n")
            title = lines[0][:20] if lines else "无标题"

    # Truncate title to max 20 chars for XHS
    title = title[:20] if len(title) > 20 else title

    # Truncate body to max 1000 chars for XHS
    if len(note_content) > 1000:
        note_content = note_content[:1000]
        # Try to truncate at a sentence boundary
        last_period = note_content.rfind('。')
        last_exclamation = note_content.rfind('！')
        last_newline = note_content.rfind('\n')
        last_boundary = max(last_period, last_exclamation, last_newline)
        if last_boundary > 500:  # Only truncate if we have enough content left
            note_content = note_content[:last_boundary + 1]

    # Auto-discover images if not provided
    if not images:
        images = _find_xhs_images(note_file.parent)

    content = PublishContent(
        title=title,
        body=note_content,
        content_type=ContentType.IMAGE_TEXT,
        images=images or [],
        tags=tags,
        custom_fields={"summary": summary},
    )

    tool = XiaohongshuTool()
    print(f"[xiaohongshu] Publishing: {title[:30]}...")
    print(f"[xiaohongshu] Images: {len(content.images)}")
    print(f"[xiaohongshu] Tags: {tags}")

    result = tool.publish(content)

    if result.is_success():
        print(f"[xiaohongshu] [OK] Draft saved! id: {result.content_id}")
        print(f"[xiaohongshu] Detail: {result.status_detail}")
        return {
            "success": True,
            "content_id": result.content_id,
            "url": result.content_url,
            "platform": "xiaohongshu",
        }
    else:
        print(f"[xiaohongshu] [FAIL] Failed: {result.error}")
        return {"success": False, "error": result.error, "platform": "xiaohongshu"}


def _find_xhs_images(note_dir: Path) -> list[str]:
    """Auto-discover images for XHS note from nearby directories."""
    images = []
    # Check for images in the note directory
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        images.extend(str(p) for p in note_dir.glob(ext))

    # Check generated_images/xiaohongshu/single/
    gen_dir = Path.cwd() / "generated_images" / "xiaohongshu" / "single"
    if gen_dir.exists() and not images:
        for ext in ("*.png", "*.jpg"):
            images.extend(str(p) for p in gen_dir.glob(ext))

    return sorted(images)[:9]  # XHS max 18, but keep conservative


def publish_all(input_dir: str, use_browser: bool = False) -> list[dict]:
    """发布所有平台内容。"""
    base = Path(input_dir)
    results = []

    # WeChat
    wechat_html = base / "wechat" / "article.html"
    wechat_meta = base / "wechat" / "metadata.json"
    if wechat_html.exists():
        r = publish_wechat(
            str(wechat_html),
            str(wechat_meta) if wechat_meta.exists() else None,
            use_browser=use_browser,
        )
        results.append(r)
    else:
        print(f"[wechat] Skipped: {wechat_html} not found")

    # Xiaohongshu
    xhs_note = base / "xiaohongshu" / "note.md"
    xhs_meta = base / "xiaohongshu" / "metadata.json"
    if xhs_note.exists():
        r = publish_xiaohongshu(
            str(xhs_note),
            str(xhs_meta) if xhs_meta.exists() else None,
        )
        results.append(r)
    else:
        print(f"[xiaohongshu] Skipped: {xhs_note} not found")

    return results


def main():
    parser = argparse.ArgumentParser(description="发布内容到各平台草稿箱")
    parser.add_argument("--platform", choices=["wechat", "xiaohongshu", "all"], required=True)
    parser.add_argument("--input", help="输入文件路径 (HTML/MD)")
    parser.add_argument("--input-dir", help="输入目录 (用于 --platform all)")
    parser.add_argument("--metadata", help="metadata.json 路径")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    parser.add_argument("--browser", action="store_true", help="使用浏览器方式发布 (微信)")
    args = parser.parse_args()

    if args.dry_run:
        print("[dry-run] Would publish to:", args.platform)
        return

    if args.platform == "all":
        if not args.input_dir:
            print("Error: --input-dir required for --platform all")
            sys.exit(1)
        results = publish_all(args.input_dir, use_browser=args.browser)
    elif args.platform == "wechat":
        if not args.input:
            print("Error: --input required")
            sys.exit(1)
        results = [publish_wechat(args.input, args.metadata, use_browser=args.browser)]
    elif args.platform == "xiaohongshu":
        if not args.input:
            print("Error: --input required")
            sys.exit(1)
        results = [publish_xiaohongshu(args.input, args.metadata)]
    else:
        results = []

    # Summary
    print("\n--- Publish Results ---")
    for r in results:
        status = "[OK]" if r.get("success") else "[FAIL]"
        platform = r.get("platform", "unknown")
        if r.get("success"):
            print(f"  {status} {platform}: {r.get('media_id') or r.get('content_id')}")
        else:
            print(f"  {status} {platform}: {r.get('error')}")

    # Write results to JSON
    output_path = Path(args.input_dir or ".") / "publish_results.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
