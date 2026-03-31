"""Extract platform content from CrewAI log output, v3."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG_FILE = r"C:\Users\puzzl\AppData\Local\Temp\claude\C--11Projects-Crew\tasks\bd1f174.output"
OUTPUT_DIR = "data/outputs/20260324_185208"

with open(LOG_FILE, "r", encoding="utf-8") as f:
    log = f.read()

# Find "Final Answer:" blocks (the actual content starts after this marker)
# Pattern: "Final Answer:\n│  ```json\n│  {...}\n│  ```"
# Each box line starts with "│  " and the content is between the │ bars

# Split log by the box header pattern
answer_sections = re.split(r"✅ Agent Final Answer ─+┐", log)
print(f"Found {len(answer_sections) - 1} Final Answer sections")

extracted = []
for i, section in enumerate(answer_sections[1:], 1):
    # Extract agent name
    agent_match = re.search(r"Agent:\s*(\S+)", section)
    agent_name = agent_match.group(1) if agent_match else f"unknown_{i}"

    # Extract content between │ bars until the closing └─
    # Find the closing border
    close_idx = section.find("└─")
    if close_idx < 0:
        close_idx = len(section)

    box_content = section[:close_idx]

    # Remove the box-drawing borders: each line is like "│  content  │"
    lines = box_content.split("\n")
    clean_lines = []
    for line in lines:
        # Remove leading "│" and trailing "│"
        stripped = line.strip()
        if stripped.startswith("│"):
            stripped = stripped[1:]
        if stripped.endswith("│"):
            stripped = stripped[:-1]
        clean_lines.append(stripped.strip())

    clean_text = "\n".join(clean_lines).strip()

    # Remove "Agent: xxx" and "Final Answer:" prefix
    clean_text = re.sub(r"^.*?Final Answer:\s*", "", clean_text, flags=re.DOTALL)

    # Remove code fences
    clean_text = re.sub(r"^```json\s*", "", clean_text)
    clean_text = re.sub(r"\s*```\s*$", "", clean_text)
    clean_text = clean_text.strip()

    extracted.append((agent_name, clean_text))
    print(f"  [{i}] Agent '{agent_name}': {len(clean_text)} chars")

# The last section is the platform adapter
if len(extracted) >= 4:
    adapter_name, adapter_text = extracted[3]  # 4th agent = platform adapter
    print(f"\nProcessing platform adapter output ({adapter_name})...")

    try:
        data = json.loads(adapter_text)
        print("[OK] JSON parsed!")
        if "platforms" in data:
            for pname, pdata in data["platforms"].items():
                pdir = os.path.join(OUTPUT_DIR, pname)
                os.makedirs(pdir, exist_ok=True)

                fname = "article.md" if pname == "wechat" else "note.md"
                with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                    f.write(pdata["content"])

                meta = {k: v for k, v in pdata.items() if k != "content"}
                with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                print(f"  [{pname}] Saved!")
                print(f"    Title: {pdata['title']}")
                print(f"    Content: {len(pdata['content'])} chars")
                print(f"    Tags: {pdata.get('tags', [])}")
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}")
        print(f"  First 200 chars: {adapter_text[:200]}")
        print(f"  Last 200 chars: {adapter_text[-200:]}")

        # The adapter output may be truncated in the log due to line-wrapping
        # Let's reconstruct from the lines that were split by the box drawing

        # Try: find the "platforms" data within the full section
        # Re-read the raw section for the 4th answer
        raw_section = answer_sections[4] if len(answer_sections) > 4 else ""
        # Collect all content between box borders
        all_lines = []
        for line in raw_section.split("\n"):
            s = line.strip()
            if s.startswith("│") and s.endswith("│"):
                inner = s[1:-1].strip()
                all_lines.append(inner)
            elif s.startswith("│"):
                inner = s[1:].strip()
                all_lines.append(inner)

        # Join with proper handling - the box wraps long lines
        # Adjacent lines that don't start with a JSON key should be joined
        joined = ""
        for line in all_lines:
            if not line or line in ("", "Agent: 平台适配师", "Final Answer:"):
                continue
            if line.startswith("```"):
                continue
            joined += line

        # Now try to parse
        # Find outermost braces
        first_b = joined.find("{")
        last_b = joined.rfind("}")
        if first_b >= 0 and last_b > first_b:
            candidate = joined[first_b : last_b + 1]
            try:
                data = json.loads(candidate)
                print("[OK] Reconstructed JSON parsed!")
                if "platforms" in data:
                    for pname, pdata in data["platforms"].items():
                        pdir = os.path.join(OUTPUT_DIR, pname)
                        os.makedirs(pdir, exist_ok=True)

                        fname = "article.md" if pname == "wechat" else "note.md"
                        with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                            f.write(pdata["content"])

                        meta = {k: v for k, v in pdata.items() if k != "content"}
                        with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                            json.dump(meta, f, ensure_ascii=False, indent=2)

                        print(f"  [{pname}] Saved!")
                        print(f"    Title: {pdata['title']}")
                        print(f"    Content: {len(pdata['content'])} chars")
            except json.JSONDecodeError as e2:
                print(f"[ERROR] Reconstructed JSON also failed: {e2}")
                # Last resort: use the review stage's final_content for wechat
                # and let me construct xiaohongshu manually
                print("\n[FALLBACK] Using review stage final_content...")

                if len(extracted) >= 3:
                    review_text = extracted[2][1]  # 3rd agent = reviewer
                    try:
                        review_data = json.loads(review_text)
                        fc = review_data.get("final_content", {})
                        if fc:
                            wdir = os.path.join(OUTPUT_DIR, "wechat")
                            os.makedirs(wdir, exist_ok=True)
                            with open(os.path.join(wdir, "article.md"), "w", encoding="utf-8") as f:
                                f.write(fc["content"])
                            meta = {k: v for k, v in fc.items() if k != "content"}
                            with open(os.path.join(wdir, "metadata.json"), "w", encoding="utf-8") as f:
                                json.dump(meta, f, ensure_ascii=False, indent=2)
                            print(f"  [wechat] Saved from review! Title: {fc['title']}")
                    except json.JSONDecodeError:
                        print("  Review JSON also failed")

print("\n=== Done ===")
