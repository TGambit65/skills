#!/usr/bin/env python3
"""Regression tests for two defects that failed silently. Standard library only: no ffmpeg, numpy or uv.

  python _test_edit_video.py

1. captions.balanced() looped forever when a clause could not be split to fit: a single word, or a `_keep`
   chain, longer than the hard limit. captions.py then hung with no output.
2. finalize.py never read the render's exit code. When the render failed and an older raw file was still on
   disk, it packaged that file as a new version and printed OK.

Neither test runs a real render or reads real media. The finalize test runs the real finalize.py beside
stand-ins for common.py, numpy, render.py and ffmpeg, and stops at the point the fix acts.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
FAILURES: list[str] = []
CHECKS = 0


def check(label: str, got, want) -> None:
    """Record one comparison."""
    global CHECKS
    CHECKS += 1
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


# ---- 1. captions.balanced ------------------------------------------------------------------------------
# captions.py imports common (numpy, soundfile) only for main(); balanced() needs none of it.
sys.modules.setdefault("common", types.SimpleNamespace(canvas=None, load=None, save=None, ws=None))
sys.path.insert(0, str(HERE))
from captions import balanced  # noqa: E402

VERTICAL, HORIZONTAL = (22, 26), (34, 42)   # (target, hard), as captions.main() sets them


def groups_of(texts, limits, nobreak=()):
    """balanced() on a list of words, as groups of word positions; "HANG" if it does not return within 3 seconds.
    The time limit needs SIGALRM, so on Windows a regression here hangs the test instead of failing it."""
    words = [{"w": t} for t in texts]

    def boom(*_):
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, boom) if hasattr(signal, "SIGALRM") else None
    if old is not None:
        signal.alarm(3)
    try:
        return balanced(list(range(len(words))), words, *limits, frozenset(nobreak))
    except TimeoutError:
        return "HANG"
    finally:
        if old is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def split(texts, limits, nobreak=()):
    """The same, as text phrases."""
    groups = groups_of(texts, limits, nobreak)
    return groups if groups == "HANG" else [" ".join(texts[j] for j in g) for g in groups]


KEEP = "Model Context Protocol servers".split()
# These four used to hang.
check("vertical: a 30-char _keep chain stands alone",
      split(["we", "use"] + KEEP + ["today"], VERTICAL, nobreak={2, 3, 4}),
      ["we use", "Model Context Protocol servers", "today"])
check("vertical: one word longer than the hard limit",
      split(["retrieval-augmented-models."], VERTICAL), ["retrieval-augmented-models."])
check("vertical: a short word then a 30-char word",
      split(["see", "github.com/acme/agent-toolkits"], VERTICAL), ["see", "github.com/acme/agent-toolkits"])
check("horizontal: one 36-char word", split(["x" * 36], HORIZONTAL), ["x" * 36])
check("an empty clause returns no phrases", split([], VERTICAL), [])
# These returned before the fix, and must return exactly what they returned then.
check("vertical: an ordinary clause is unchanged",
      split("this is a perfectly ordinary clause of words".split(), VERTICAL),
      ["this is a perfectly", "ordinary clause of words"])
check("horizontal: the same _keep chain fits and is unchanged",
      split(["we", "use"] + KEEP + ["today"], HORIZONTAL, nobreak={2, 3, 4}),
      ["we use", "Model Context Protocol servers today"])
check("a word exactly at the target is unchanged", split(["a" * 22], VERTICAL), ["a" * 22])
# Whatever the input, the result is a partition in order that never breaks inside a _keep chain.
for texts, limits, nobreak in [
    (["a", "bb", "ccc", "dddd", "eeeee", "ffffff", "ggggggg"], VERTICAL, {1, 2, 3, 4, 5}),
    (["retrieval-augmented", "github.com/acme/toolkit", "on."], VERTICAL, {0}),
    (["to", "the", "model", "context", "protocol", "servers", "today", "really"], HORIZONTAL, {0, 4}),
]:
    groups = groups_of(texts, limits, nobreak)
    if groups == "HANG":
        check(f"returns at all: {texts[:2]}", "HANG", "a partition")
        continue
    check(f"partition covers every word in order: {texts[:2]}", [j for g in groups for j in g], list(range(len(texts))))
    check(f"no break inside a _keep chain: {texts[:2]}", [g[-1] for g in groups[:-1] if g[-1] in nobreak], [])


# ---- 2. finalize.py and a failed render ----------------------------------------------------------------
COMMON_STUB = '''
import json, os, subprocess, sys
def ws():
    d = os.path.abspath(sys.argv[1]); return d, json.load(open(os.path.join(d, "config.json")))
def load(*a, **k): return None
def read_wav(*a, **k): raise SystemExit("stub")
def run(cmd, **k): raise SystemExit("stub")
'''


def finalize(render_exit: int) -> tuple[int, str, list[str], bool]:
    """Run the real finalize.py with a render.py that exits `render_exit`, an older raw already on disk.
    Returns (exit code, output, files written to the destination, whether it went on to run ffmpeg).
    Running ffmpeg is the first thing finalize does after the render step; the stand-in leaves a marker file."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        scripts, work, dest = root / "scripts", root / "ws", root / "final"
        scripts.mkdir()
        shutil.copy(HERE / "finalize.py", scripts / "finalize.py")
        (scripts / "common.py").write_text(COMMON_STUB, encoding="utf-8")
        (scripts / "numpy.py").write_text("", encoding="utf-8")
        (scripts / "render.py").write_text(
            f"import sys\nprint('stub render')\nsys.stderr.write('lint: missing asset\\n')\nsys.exit({render_exit})\n",
            encoding="utf-8")
        fake = root / "bin" / "ffmpeg"
        fake.parent.mkdir()
        fake.write_text(f"#!/bin/sh\n: > '{root / 'ffmpeg-was-run'}'\nexit 3\n", encoding="utf-8")
        fake.chmod(0o755)
        raw = work / "hf" / "broll" / "out" / "broll_final_raw.mp4"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"an older render")
        (work / "config.json").write_text('{"source": "x", "fps": 30}', encoding="utf-8")
        done = subprocess.run([sys.executable, str(scripts / "finalize.py"), str(work), "broll", "demo",
                               "--dest", str(dest)], capture_output=True, text=True,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                                   "PATH": str(fake.parent) + os.pathsep + os.environ.get("PATH", "")})
        made = sorted(p.name for p in dest.iterdir()) if dest.is_dir() else []
        return done.returncode, done.stdout + done.stderr, made, (root / "ffmpeg-was-run").exists()


if os.name == "nt":
    print("finalize checks skipped on Windows: they need a stand-in ffmpeg shell script")
else:
    code, output, made, went_on = finalize(render_exit=1)
    check("failed render: finalize exits non-zero", code != 0, True)
    check("failed render: the message says the render failed", "render failed (exit 1)" in output, True)
    check("failed render: the render's own error is shown", "lint: missing asset" in output, True)
    check("failed render: finalize stops before packaging", went_on, False)
    check("failed render: nothing is written to the destination", made, [])

    code, output, made, went_on = finalize(render_exit=0)
    check("successful render: finalize carries on to packaging", went_on, True)
    check("successful render: no render-failed message", "render failed" in output, False)


# --------------------------------------------------------------------------------------------------------
if FAILURES:
    print(f"\nFAILED {len(FAILURES)} of {CHECKS}:")
    for f in FAILURES:
        print("  " + f)
    sys.exit(1)
print(f"all {CHECKS} checks passed")
