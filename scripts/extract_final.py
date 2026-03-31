"""Extract platform content from CrewAI log - final working version."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG = r"C:\Users\puzzl\AppData\Local\Temp\claude\C--11Projects-Crew\tasks\bd1f174.output"
OUT = "data/outputs/20260324_185208"

with open(LOG, "r", encoding="utf-8") as f:
    log = f.read()

# Extract adapter section (Final Answer at pos 35693)
fa_pos = 35693
close_pos = log.find("\u2514\u2500", fa_pos + 100)
section = log[fa_pos:close_pos]

# Strip box drawing chars
lines = section.split("\n")
clean = []
for line in lines:
    s = line.strip()
    while s.startswith("\u2502"):
        s = s[1:]
    while s.endswith("\u2502"):
        s = s[:-1]
    s = s.strip()
    if s:
        clean.append(s)

# Skip header, join
text_lines = []
started = False
for line in clean:
    if "Final Answer:" in line:
        started = True
        continue
    if not started:
        continue
    if line in ("```json", "```"):
        continue
    text_lines.append(line)

one_line = " ".join(text_lines)

# Fix broken escape sequences from box wrapping
# Pattern: backslash + whitespace + n -> \n
one_line = re.sub(r"\\\s+n", r"\\n", one_line)

# Find JSON boundaries
first_b = one_line.find("{")
last_b = one_line.rfind("}")
candidate = one_line[first_b : last_b + 1]
print(f"JSON candidate: {len(candidate)} chars")


def fix_escapes(s):
    """Fix invalid JSON escape sequences."""
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            next_ch = s[i + 1]
            if next_ch in '"\\\/bfnrtu':
                result.append(ch)
                result.append(next_ch)
                i += 2
            elif next_ch == " ":
                # Backslash before space is a box-wrapping artifact
                result.append(" ")
                i += 2
            else:
                # Invalid escape - skip the backslash
                result.append(next_ch)
                i += 2
        else:
            result.append(ch)
            i += 1
    return "".join(result)


fixed = fix_escapes(candidate)

try:
    data = json.loads(fixed)
    print("[OK] Parsed!")
except json.JSONDecodeError as e:
    print(f"Error: {e}")
    p = e.pos
    print(f"Context around pos {p}: {repr(fixed[max(0, p - 40) : p + 40])}")
    data = None

if data and "platforms" in data:
    for pname, pdata in data["platforms"].items():
        pdir = os.path.join(OUT, pname)
        os.makedirs(pdir, exist_ok=True)
        fname = "article.md" if pname == "wechat" else "note.md"
        with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
            f.write(pdata["content"])
        meta = {k: v for k, v in pdata.items() if k != "content"}
        with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"  [{pname}] {len(pdata['content'])} chars")
        print(f"    Title: {pdata['title']}")
        print(f"    Tags: {pdata.get('tags', [])}")
    print("\nExtraction complete!")
else:
    # Fallback: extract content using regex on the fixed string
    print("\nJSON parse failed, trying regex extraction...")
    for platform in ["wechat", "xiaohongshu"]:
        plat_idx = fixed.find(f'"{platform}"')
        if plat_idx < 0:
            print(f"  [{platform}] not found")
            continue

        sub = fixed[plat_idx:]
        # Extract title
        title_m = re.search(r'"title":\s*"([^"]*)"', sub)
        title = title_m.group(1) if title_m else "Untitled"

        # Extract content: between "content": " and the next unescaped "
        content_start = sub.find('"content":')
        if content_start >= 0:
            # Find the opening quote of the value
            val_start = sub.find('"', content_start + len('"content":'))
            if val_start >= 0:
                val_start += 1  # skip the opening quote
                # Find the closing quote (not preceded by backslash)
                pos = val_start
                while pos < len(sub):
                    if sub[pos] == '"' and sub[pos - 1] != "\\":
                        break
                    pos += 1
                content_escaped = sub[val_start:pos]
                # Unescape
                content = content_escaped.replace("\\n", "\n").replace('\\"', '"')

                pdir = os.path.join(OUT, platform)
                os.makedirs(pdir, exist_ok=True)
                fname = "article.md" if platform == "wechat" else "note.md"
                with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
                    f.write(content)

                # Extract summary and tags
                summary_m = re.search(r'"summary":\s*"([^"]*)"', sub)
                tags_m = re.search(r'"tags":\s*\[([^\]]*)\]', sub)
                summary = summary_m.group(1) if summary_m else ""
                tags = []
                if tags_m:
                    tags = [t.strip().strip('"') for t in tags_m.group(1).split(",")]

                meta = {"title": title, "summary": summary, "tags": tags}
                with open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                print(f"  [{platform}] {len(content)} chars (regex)")
                print(f"    Title: {title}")
                print(f"    Tags: {tags}")
            else:
                print(f"  [{platform}] content value start not found")
        else:
            print(f"  [{platform}] content key not found")

    print("\nDone!")
