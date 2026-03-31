"""
Extract platform content by joining box-drawn lines and fixing JSON escaping.
The CrewAI log wraps long JSON values across multiple lines with │ box borders.
We need to rejoin them and fix the escaped newlines.
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

# Split by the Final Answer box header
sections = re.split(r"✅ Agent Final Answer ─+┐", log)

def extract_box_content(section: str) -> str:
    """Extract text from box-drawing bordered section, joining wrapped lines."""
    close_idx = section.find("└─")
    if close_idx < 0:
        close_idx = len(section)
    box = section[:close_idx]

    lines = box.split("\n")
    parts = []
    for line in lines:
        s = line.rstrip()
        # Remove trailing │
        if s.endswith("│"):
            s = s[:-1]
        # Remove leading │
        stripped = s.lstrip()
        if stripped.startswith("│"):
            stripped = stripped[1:]
        # Remove leading/trailing whitespace but preserve intended spaces
        stripped = stripped.strip()
        if stripped:
            parts.append(stripped)

    # Skip header lines (Agent name, empty lines)
    text_parts = []
    past_header = False
    for p in parts:
        if p.startswith("Final Answer:"):
            past_header = True
            continue
        if not past_header:
            continue
        if p in ("```json", "```"):
            continue
        text_parts.append(p)

    # Now we have lines like:
    # "platforms": {
    # "wechat": {
    # "title":
    # "用了3个月..." (this is a continuation of the previous line)
    # We need to join continuation lines (lines that are part of a JSON string value
    # split by box wrapping)

    # Strategy: join all lines, then fix the JSON
    joined = "\n".join(text_parts)
    return joined


def fix_json_from_box(text: str) -> dict | None:
    """Try to fix and parse JSON that was split by box-drawing borders."""
    # The text has real newlines where the box wrapping broke lines
    # Within JSON string values, these should be removed (they're artifacts)
    # But \n sequences within strings are intentional

    # Approach: process line by line, detecting if we're inside a JSON string
    # A line that starts with a JSON key pattern like "key": starts a new field
    # Other lines are continuations of the previous value

    lines = text.split("\n")
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line starts a JSON structure or key
        if re.match(r'^\s*[{}\[\],]', line) or re.match(r'^\s*"[^"]*"\s*:', line):
            fixed_lines.append(line)
        else:
            # This is a continuation of the previous line
            if fixed_lines:
                fixed_lines[-1] += " " + line.strip()
            else:
                fixed_lines.append(line)
        i += 1

    result = "\n".join(fixed_lines)

    # Find the outermost JSON object
    first_b = result.find("{")
    last_b = result.rfind("}")
    if first_b < 0 or last_b <= first_b:
        return None

    candidate = result[first_b:last_b + 1]

    # Try parsing
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # More aggressive fix: replace real newlines within string values
    # Remove all newlines that aren't preceded by a comma, brace, or bracket
    # This is risky but may work for our specific case
    cleaned = re.sub(r'(?<=[^,\{\}\[\]"])\n\s*(?=[^"\{\}\[\]])', ' ', candidate)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    return None


# Process the 4th section (platform adapter)
if len(sections) >= 5:
    adapter_section = sections[4]
    adapter_text = extract_box_content(adapter_section)
    print(f"Adapter text: {len(adapter_text)} chars")

    data = fix_json_from_box(adapter_text)
    if data and "platforms" in data:
        for pname, pdata in data["platforms"].items():
            pdir = os.path.join(OUTPUT_DIR, pname)
            os.makedirs(pdir, exist_ok=True)
            fname = "article.md" if pname == "wechat" else "note.md"
            with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                f.write(pdata["content"])
            meta = {k: v for k, v in pdata.items() if k != "content"}
            with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            print(f"[OK] {pname}: {len(pdata['content'])} chars")
            print(f"  Title: {pdata['title']}")
    else:
        print("[WARN] Could not parse adapter JSON, falling back to review data")

        # Use review stage (3rd answer) for wechat content
        if len(sections) >= 4:
            review_text = extract_box_content(sections[3])
            review_data = fix_json_from_box(review_text)
            if review_data and "final_content" in review_data:
                fc = review_data["final_content"]
                wdir = os.path.join(OUTPUT_DIR, "wechat")
                os.makedirs(wdir, exist_ok=True)
                with open(os.path.join(wdir, "article.md"), "w", encoding="utf-8") as f:
                    f.write(fc["content"])
                meta = {k: v for k, v in fc.items() if k != "content"}
                with open(os.path.join(wdir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                print(f"[OK] wechat from review: {len(fc['content'])} chars")
                print(f"  Title: {fc['title']}")
            else:
                print("[ERROR] Could not parse review JSON either")

                # Last resort: use the writing stage (2nd answer) directly
                if len(sections) >= 3:
                    write_text = extract_box_content(sections[2])
                    write_data = fix_json_from_box(write_text)
                    if write_data and "content" in write_data:
                        wdir = os.path.join(OUTPUT_DIR, "wechat")
                        os.makedirs(wdir, exist_ok=True)
                        with open(os.path.join(wdir, "article.md"), "w", encoding="utf-8") as f:
                            f.write(write_data["content"])
                        meta = {k: v for k, v in write_data.items() if k != "content"}
                        with open(os.path.join(wdir, "metadata.json"), "w", encoding="utf-8") as f:
                            json.dump(meta, f, ensure_ascii=False, indent=2)
                        print(f"[OK] wechat from writer: {len(write_data['content'])} chars")

print("\n=== Done ===")
