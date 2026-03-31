"""
Final extraction: read the log, find the adapter's answer section,
and extract the wechat/xiaohongshu content by parsing the \\n-escaped
markdown content strings directly.
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG_FILE = r"C:\Users\puzzl\AppData\Local\Temp\claude\C--11Projects-Crew\tasks\bd1f174.output"
OUTPUT_DIR = "data/outputs/20260324_185208"

with open(LOG_FILE, "r", encoding="utf-8") as f:
    log = f.read()

# ---- Strategy: extract the raw text between box borders for each agent ----
# Split by the answer header
sections = log.split("✅ Agent Final Answer")

def clean_box_section(section: str) -> str:
    """Remove all box-drawing characters and rejoin wrapped lines."""
    # Find end of box
    end = section.find("└─")
    if end < 0:
        end = len(section)
    box = section[:end]

    # Process each line
    result_chars = []
    for line in box.split("\n"):
        # Strip box borders
        s = line.replace("│", "").strip()
        if s:
            result_chars.append(s)

    return "\n".join(result_chars)


# Get the 4th answer (platform adapter, index 4 since first split is before any answer)
if len(sections) >= 5:
    raw_adapter = clean_box_section(sections[4])

    # Remove header lines
    lines = raw_adapter.split("\n")
    content_lines = []
    started = False
    for line in lines:
        if "Final Answer:" in line:
            started = True
            continue
        if not started:
            continue
        if line.strip() in ("```json", "```", ""):
            continue
        content_lines.append(line)

    # Join all content lines into one string, preserving the JSON structure
    # The key insight: the box wrapping splits JSON lines at ~75 chars
    # We need to rejoin them into valid JSON
    # Lines that are continuations of a string value don't start with "
    full_text = ""
    for line in content_lines:
        stripped = line.strip()
        # If this line starts a new JSON key or structural element, add newline
        if re.match(r'^["{\}\[\],]', stripped) or re.match(r'^[a-z_]', stripped):
            full_text += "\n" + stripped
        else:
            # Continuation of previous line - join with space
            full_text += " " + stripped

    full_text = full_text.strip()

    # Find outermost braces
    first = full_text.find("{")
    last = full_text.rfind("}")
    if first >= 0 and last > first:
        json_candidate = full_text[first:last+1]

        # The "content" fields have \\n (literal backslash-n) for newlines in markdown
        # But the box wrapping introduced real newlines + spaces within string values
        # We need to remove those real newlines within strings

        # Approach: find all "content": "..." fields and fix them
        # Actually, let's try a different approach: just remove all newlines
        # and reconstruct
        one_line = json_candidate.replace("\n", " ")
        # Collapse multiple spaces
        one_line = re.sub(r"  +", " ", one_line)

        try:
            data = json.loads(one_line)
            print("[OK] Parsed adapter JSON!")
            if "platforms" in data:
                for pname, pdata in data["platforms"].items():
                    pdir = os.path.join(OUTPUT_DIR, pname)
                    os.makedirs(pdir, exist_ok=True)
                    fname = "article.md" if pname == "wechat" else "note.md"
                    # The content has \\n which json.loads already converted to \n
                    with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                        f.write(pdata["content"])
                    meta = {k: v for k, v in pdata.items() if k != "content"}
                    with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    print(f"  [{pname}] {len(pdata['content'])} chars")
                    print(f"    Title: {pdata['title']}")
                    print(f"    Summary: {pdata.get('summary', '')[:60]}...")
                    print(f"    Tags: {pdata.get('tags', [])}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Still can't parse: {e}")
            # Show around error position
            pos = e.pos
            print(f"  Around pos {pos}: ...{one_line[max(0,pos-60):pos+60]}...")

            # LAST RESORT: manually extract using regex on the one-line version
            print("\n[FALLBACK] Regex extraction...")

            for platform in ["wechat", "xiaohongshu"]:
                # Find "platform": { "title": "...", "content": "...", ...}
                # Use a pattern that captures the title and content
                title_pat = rf'"{platform}":\s*\{{\s*"title":\s*"([^"]*)"'
                title_m = re.search(title_pat, one_line)

                # For content, it's a long string with escaped chars
                # Find "content": " and then match until the next ", "summary"
                content_pat = rf'"content":\s*"(.*?)",\s*"summary"'
                # Search starting from the platform section
                platform_start = one_line.find(f'"{platform}"')
                if platform_start >= 0:
                    sub = one_line[platform_start:]
                    content_m = re.search(content_pat, sub)
                    summary_pat = r'"summary":\s*"(.*?)",\s*"tags"'
                    summary_m = re.search(summary_pat, sub)
                    tags_pat = r'"tags":\s*\[(.*?)\]'
                    tags_m = re.search(tags_pat, sub)

                    if title_m and content_m:
                        title = title_m.group(1)
                        # Unescape the content
                        content_raw = content_m.group(1)
                        content = content_raw.replace("\\n", "\n").replace('\\"', '"')
                        summary = summary_m.group(1) if summary_m else ""
                        tags_str = tags_m.group(1) if tags_m else ""
                        tags = [t.strip().strip('"') for t in tags_str.split(",")]

                        pdir = os.path.join(OUTPUT_DIR, platform)
                        os.makedirs(pdir, exist_ok=True)
                        fname = "article.md" if platform == "wechat" else "note.md"
                        with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                            f.write(content)
                        meta = {"title": title, "summary": summary, "tags": tags}
                        with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                            json.dump(meta, f, ensure_ascii=False, indent=2)
                        print(f"  [{platform}] {len(content)} chars")
                        print(f"    Title: {title}")
                    else:
                        print(f"  [{platform}] Could not extract via regex")
                        if title_m:
                            print(f"    Title found: {title_m.group(1)}")
                        if not content_m:
                            print("    Content not found")

print("\n=== Done ===")
