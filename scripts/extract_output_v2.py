"""Extract platform content from CrewAI log output (bd1f174.output).

The raw_output.md was truncated by CrewAI's token limit, but the full agent
outputs are in the log file. We extract the final platform adapter's answer.
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

# The log uses box-drawing UI. Agent output appears after "Final Answer:" blocks.
# Each agent's answer is between "Final Answer:" and the next box border.
# We need the platform adapter's answer (last one).

# Strategy: Find all text between "Final Answer:" and the closing box border
# The box border pattern is: └─────...┘
final_answers = []
pattern = r"Final Answer:\s*\n│\s*(.*?)│\s*\n└─"
# That won't work well due to multi-line. Let's do a simpler approach.

# Find each "Agent: X" + "Final Answer:" block
agent_pattern = r"Agent:\s*(.*?)\s*│.*?Final Answer:\s*\n(.*?)└──"
matches = list(re.finditer(agent_pattern, log, re.DOTALL))
print(f"Found {len(matches)} agent answer blocks")

for m in matches:
    agent_name = m.group(1).strip()
    answer_raw = m.group(2)
    # Clean the box drawing characters
    lines = answer_raw.split("\n")
    clean_lines = []
    for line in lines:
        # Remove leading │ and trailing │
        line = re.sub(r"^\s*│\s*", "", line)
        line = re.sub(r"\s*│\s*$", "", line)
        clean_lines.append(line)
    answer_text = "\n".join(clean_lines).strip()
    final_answers.append((agent_name, answer_text))
    print(f"  Agent '{agent_name}': {len(answer_text)} chars")

# The platform adapter is the last agent
if final_answers:
    adapter_name, adapter_answer = final_answers[-1]
    print(f"\nPlatform adapter: '{adapter_name}'")

    # Extract JSON from adapter answer (may be wrapped in ```json```)
    json_match = re.search(r"```json\s*\n([\s\S]*?)\n\s*```", adapter_answer)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find outermost JSON object
        first = adapter_answer.find("{")
        last = adapter_answer.rfind("}")
        json_str = adapter_answer[first : last + 1] if first >= 0 else ""

    print(f"JSON candidate: {len(json_str)} chars")

    try:
        data = json.loads(json_str)
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

                print(f"[OK] {pname}/")
                print(f"  Title: {pdata['title']}")
                print(f"  Content: {len(pdata['content'])} chars")
                print(f"  Tags: {pdata.get('tags', [])}")
        print("\nDone!")
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed at pos {e.pos}: {e.msg}")
        # Show context around failure
        start = max(0, e.pos - 80)
        end = min(len(json_str), e.pos + 80)
        print(f"Context: ...{json_str[start:end]}...")
        print("\nFalling back to manual extraction...")

        # The JSON may have the content truncated in the log too
        # Let's try to extract the review stage's final_content instead
        # and use that as wechat content, then construct xiaohongshu from scratch
        review_name, review_answer = final_answers[-2] if len(final_answers) >= 2 else (None, None)
        if review_name:
            print(f"\nTrying review stage from agent '{review_name}'...")
            json_match2 = re.search(r"```json\s*\n([\s\S]*?)\n\s*```", review_answer)
            if json_match2:
                try:
                    review_data = json.loads(json_match2.group(1))
                    fc = review_data.get("final_content", {})
                    if fc and fc.get("content"):
                        wdir = os.path.join(OUTPUT_DIR, "wechat")
                        os.makedirs(wdir, exist_ok=True)
                        with open(os.path.join(wdir, "article.md"), "w", encoding="utf-8") as f:
                            f.write(fc["content"])
                        meta = {k: v for k, v in fc.items() if k != "content"}
                        with open(os.path.join(wdir, "metadata.json"), "w", encoding="utf-8") as f:
                            json.dump(meta, f, ensure_ascii=False, indent=2)
                        print(f"[OK] wechat/ (from review final_content)")
                        print(f"  Title: {fc['title']}")
                        print(f"  Content: {len(fc['content'])} chars")
                except json.JSONDecodeError as e2:
                    print(f"Review JSON also failed: {e2}")
