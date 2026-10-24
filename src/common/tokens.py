"""Token counts with the Qwen3 tokenizer (DATASET.md section 2.4, PLAN Step 16).

Counts only the visible part, rendered as plain text. The prompt template (instructions, policies,
answer) is added later by prompt_builder.py and is not part of meta.n_tokens.
"""
import json

TOKENIZER_REPO = "Qwen/Qwen3-8B"       # all Qwen3 sizes share this tokenizer
TOKENIZER_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def load_tokenizer():
    from tokenizers import Tokenizer    # imported here so the rest of src/ does not need it
    return Tokenizer.from_pretrained(TOKENIZER_REPO, revision=TOKENIZER_REVISION)


def render_call(call: dict) -> str:
    return json.dumps({"name": call["name"], "args": call["args"]}, ensure_ascii=False)


def render_visible(rec: dict) -> str:
    """The visible part as text: one '[role] text' block per turn, actions on their own line."""
    blocks = []
    for msg in rec["visible"]["trajectory"]:
        lines = [f"[{msg['role']}] {msg['text']}".rstrip()]
        if msg["tool_call"]:
            lines.append("action: " + render_call(msg["tool_call"]))
        if msg["action_text"]:
            lines.append("action: " + msg["action_text"])
        blocks.append("\n".join(lines))
    if rec["visible"]["proposed_action"]:
        blocks.append("[proposed_action] " + render_call(rec["visible"]["proposed_action"]))
    return "\n\n".join(blocks)


def count_tokens(rec: dict, tokenizer) -> int:
    return len(tokenizer.encode(render_visible(rec), add_special_tokens=False).ids)
