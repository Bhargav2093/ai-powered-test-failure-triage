"""Renders a terminal-style demo GIF of a real `triage` run, without needing
a live pty or a display - just PIL drawing pre-scripted frames.

The scripted transcript below is copied verbatim from a real run against the
committed sample fixtures (see samples/sample-triage-report.md), so the GIF
shows genuine tool output, not made-up text. Re-running the CLI command shown
in the recording reproduces the exact same report.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = "C:/Windows/Fonts/consola.ttf"
_FONT_SIZE = 16
_LINE_HEIGHT = 21
_PAD_X = 18
_PAD_Y = 16
_BG = (30, 30, 30)
_FG = (212, 212, 212)
_PROMPT = (78, 201, 176)
_SUCCESS = (106, 200, 106)
_FLAKY = (229, 192, 92)
_REGRESSION = (224, 108, 96)
_INFRA = (100, 170, 230)
_MUTED = (140, 140, 140)

_COMMAND = (
    "triage --junit-xml tests/fixtures/real_framework_failure/junit-report.xml \\\n"
    "    tests/fixtures/synthetic/mixed_failures.xml --format markdown"
)

# (text, color) - one entry per rendered line, in order. This is the real
# output of `triage --format markdown` against the committed sample fixtures.
_OUTPUT_LINES = [
    ("", _FG),
    ("Triaged 5 failure(s) into 3 cluster(s). Wrote markdown report to stdout", _SUCCESS),
    ("", _FG),
    ("# Test Failure Triage Report", _FG),
    ("", _FG),
    ("| Category   | Count |", _MUTED),
    ("|------------|-------|", _MUTED),
    ("| flaky      | 2     |", _MUTED),
    ("| regression | 2     |", _MUTED),
    ("| infra      | 1     |", _MUTED),
    ("", _FG),
    ("## [REGRESSION] PostsApiTests.getSinglePostReturnsValidSchema (+1 more)", _REGRESSION),
    ("2 tests failed with a matching regression signature (representative:", _FG),
    ("getSinglePostReturnsValidSchema - expected [999] but found [1]). No known", _FG),
    ("flaky/infra signal matched - treat as a genuine candidate regression until", _FG),
    ("a human rules it out.", _FG),
    ("", _FG),
    ("## [FLAKY] LoginTests.loginButtonClickable (+1 more)", _FLAKY),
    ("2 tests failed with a matching flaky signature (representative:", _FG),
    ("loginButtonClickable - element click intercepted: Element is not clickable", _FG),
    ("at point (120, 340)). Likely environment/timing-related rather than a real", _FG),
    ("product defect - consider adding explicit waits or a retry policy.", _FG),
    ("", _FG),
    ("## [INFRA] ApiHealthTests.pingInternalService (+0 more)", _INFRA),
    ("1 test failed with a matching infra signature (representative:", _FG),
    ("pingInternalService - Connection refused: connect). Likely an", _FG),
    ("environment/connectivity problem outside the application under test.", _FG),
    ("", _FG),
]

_CANVAS_W = 920
_TYPE_CHARS_PER_FRAME = 3
_TYPE_FRAME_MS = 35
_OUTPUT_FRAME_MS = 110
_HEADER_FRAME_MS = 260
_FINAL_HOLD_MS = 3000


def _font() -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_FONT_PATH, _FONT_SIZE)


def _wrapped_prompt_lines(typed: str) -> list[tuple[str, tuple[int, int, int], bool]]:
    """Split the (possibly partial) command into display lines.

    Returns (text, color, is_first_line) so only the first line gets the
    "$ " prompt prefix, matching how a real shell wraps a backslash-continued
    command.
    """
    lines = typed.split("\n")
    out = []
    for i, line in enumerate(lines):
        out.append((line, _FG, i == 0))
    return out


def render() -> Image.Image:
    font = _font()
    frames: list[Image.Image] = []
    durations: list[int] = []

    def add_frame(lines: list[tuple[str, tuple[int, int, int]]], duration_ms: int, cursor: bool = False) -> None:
        height = _PAD_Y * 2 + max(1, len(lines)) * _LINE_HEIGHT
        img = Image.new("RGB", (_CANVAS_W, height), _BG)
        draw = ImageDraw.Draw(img)
        y = _PAD_Y
        for text, color in lines:
            draw.text((_PAD_X, y), text, font=font, fill=color)
            y += _LINE_HEIGHT
        if cursor:
            last_text = lines[-1][0] if lines else ""
            cursor_x = _PAD_X + draw.textlength(last_text, font=font)
            cursor_y = y - _LINE_HEIGHT
            draw.rectangle(
                [cursor_x, cursor_y + 2, cursor_x + 9, cursor_y + _LINE_HEIGHT - 2],
                fill=_FG,
            )
        frames.append(img)
        durations.append(duration_ms)

    # Phase 1: type the command out, character by character.
    for n in range(0, len(_COMMAND) + 1, _TYPE_CHARS_PER_FRAME):
        typed = _COMMAND[:n]
        prompt_lines = _wrapped_prompt_lines(typed)
        display = [
            ((f"$ {text}" if is_first else f"    {text}"), _FG)
            for text, _color, is_first in prompt_lines
        ]
        add_frame(display, _TYPE_FRAME_MS, cursor=True)

    full_command_lines = [
        ((f"$ {text}" if is_first else f"    {text}"), _FG)
        for text, _color, is_first in _wrapped_prompt_lines(_COMMAND)
    ]
    add_frame(full_command_lines, 500, cursor=True)
    add_frame(full_command_lines, 500, cursor=False)

    # Phase 2: reveal the real triage output, one line at a time.
    revealed: list[tuple[str, tuple[int, int, int]]] = list(full_command_lines)
    for text, color in _OUTPUT_LINES:
        revealed = revealed + [(text, color)]
        duration = _HEADER_FRAME_MS if text.startswith("##") or text.startswith("Triaged") else _OUTPUT_FRAME_MS
        add_frame(revealed, duration)

    # Final: hold on the completed report with a fresh prompt.
    final = revealed + [("$ ", _PROMPT)]
    add_frame(final, _FINAL_HOLD_MS, cursor=True)

    # Pad every frame to the tallest frame's height (GIF frames share one canvas).
    max_h = max(f.height for f in frames)
    padded = []
    for f in frames:
        if f.height == max_h:
            padded.append(f)
        else:
            canvas = Image.new("RGB", (_CANVAS_W, max_h), _BG)
            canvas.paste(f, (0, 0))
            padded.append(canvas)

    padded[0].save(
        Path(__file__).resolve().parent.parent / "samples" / "demo.gif",
        save_all=True,
        append_images=padded[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return padded[0]


if __name__ == "__main__":
    render()
    out = Path(__file__).resolve().parent.parent / "samples" / "demo.gif"
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
