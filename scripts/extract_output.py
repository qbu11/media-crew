"""Extract platform-specific content from pipeline output."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT_FILE = r"C:\Users\puzzl\AppData\Local\Temp\claude\C--11Projects-Crew\tasks\bd1f174.output"
OUTPUT_DIR = "data/outputs/20260324_185208"

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    full_output = f.read()

# Find all JSON blocks (between ```json and ```)
json_blocks = re.findall(r"```json\s*\n([\s\S]*?)\n```", full_output)
print(f"Found {len(json_blocks)} JSON blocks in output")

# Try each block from last to first (adaptation is last)
for i, block in enumerate(reversed(json_blocks)):
    try:
        data = json.loads(block)
        if "platforms" in data:
            print(f"[OK] Block {len(json_blocks) - 1 - i}: has 'platforms' key")
            for pname in data["platforms"]:
                pdata = data["platforms"][pname]
                pdir = os.path.join(OUTPUT_DIR, pname)
                os.makedirs(pdir, exist_ok=True)

                fname = "article.md" if pname == "wechat" else "note.md"
                with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                    f.write(pdata["content"])

                meta = {k: v for k, v in pdata.items() if k != "content"}
                with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                print(f"  [{pname}] saved to {pdir}/")
                print(f"    Title: {pdata['title']}")
                print(f"    Content: {len(pdata['content'])} chars")
                print(f"    Tags: {pdata.get('tags', [])}")
            break
    except json.JSONDecodeError:
        continue
else:
    # If no clean JSON parse works, the content has real newlines in strings
    # The pipeline already saved per-stage files, use the review stage final_content
    print("[WARN] No parseable platform JSON found, extracting from stage files")

    # Use the review stage output which has final_content
    for i, block in enumerate(reversed(json_blocks)):
        try:
            data = json.loads(block)
            if "final_content" in data:
                fc = data["final_content"]
                print(f"[OK] Found review final_content in block {len(json_blocks) - 1 - i}")

                # Save as wechat version (the deep article)
                wdir = os.path.join(OUTPUT_DIR, "wechat")
                os.makedirs(wdir, exist_ok=True)
                with open(os.path.join(wdir, "article.md"), "w", encoding="utf-8") as f:
                    f.write(fc["content"])
                meta = {k: v for k, v in fc.items() if k != "content"}
                with open(os.path.join(wdir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                print(f"  [wechat] from review final_content: {len(fc['content'])} chars")
                break
        except json.JSONDecodeError:
            continue

print("\nDone!")
