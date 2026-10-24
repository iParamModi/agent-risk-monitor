"""src/common/tokens.py rendering + src/external/count_tokens.py stats (no tokenizer download needed)."""
from src.common.tokens import count_tokens, render_visible
from src.external.count_tokens import length_stats


def msg(role, text, tool_call=None, action_text=None):
    return {"role": role, "text": text, "tool_call": tool_call, "action_text": action_text}


def record(proposed=None):
    return {
        "visible": {"trajectory": [
            msg("user", "Share the report."),
            msg("agent", "I will share it.", tool_call={"name": "share_file", "args": {"path": "/r.pdf"}}),
            msg("tool", "Done."),
            msg("agent", "", action_text="Complete{done}"),
        ], "proposed_action": proposed},
        "hidden": {"secret": "HIDDEN_FACT"},
        "gold": {"risk_label": "UNSAFE", "source_note": "GOLD_NOTE"},
    }


def test_render_has_every_turn_and_action():
    text = render_visible(record())
    assert text.startswith("[user] Share the report.")
    assert 'action: {"name": "share_file", "args": {"path": "/r.pdf"}}' in text
    assert "[tool] Done." in text and "[agent]\naction: Complete{done}" in text


def test_render_never_includes_hidden_or_gold():
    text = render_visible(record())
    assert "HIDDEN_FACT" not in text and "GOLD_NOTE" not in text and "UNSAFE" not in text


def test_render_adds_proposed_action():
    text = render_visible(record({"name": "delete_file", "args": {"path": "/a"}}))
    assert text.endswith('[proposed_action] {"name": "delete_file", "args": {"path": "/a"}}')


class FakeTokenizer:
    class Enc:
        def __init__(self, ids):
            self.ids = ids

    def encode(self, text, add_special_tokens=True):
        return self.Enc(text.split())


def test_count_tokens_uses_rendered_text():
    rec = record()
    assert count_tokens(rec, FakeTokenizer()) == len(render_visible(rec).split())


def test_length_stats():
    st = length_stats([100, 3000, 5000, 9000])
    assert st["records"] == 4 and st["max"] == 9000 and st["median"] == 4000
    assert st["over"] == {"2048": 3, "4096": 2, "8192": 1}
    assert length_stats([]) == {"records": 0}
