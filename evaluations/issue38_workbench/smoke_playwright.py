#!/usr/bin/env python3
"""Run the Issue #38 offline browser acceptance path.

The script drives the documented Playwright CLI wrapper against a caller-owned
loopback fixture server.  It intentionally uses a non-secret fixture key only
to prove that the UI masks credentials; it never prints or persists that
value, and it never calls a model or a public network service.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from pathlib import Path
from typing import List, Sequence


FIXTURE_KEY = "sk-fixture-not-real"


class SmokeFailure(RuntimeError):
    """A browser acceptance assertion failed."""


def _default_pwcli() -> Path:
    codex_home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(codex_home) / "skills" / "playwright" / "scripts" / "playwright_cli.sh"


def _redact(text: str) -> str:
    return text.replace(FIXTURE_KEY, "<fixture-key-redacted>")


def _health(url: str) -> dict:
    with urllib.request.urlopen(url.rstrip("/") + "/healthz", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload != {"ok": True, "service": "deeptalk-webui"}:
        raise SmokeFailure(f"unexpected /healthz payload: {payload!r}")
    return payload


def _write_fixture_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 800)


def run(args: argparse.Namespace) -> dict:
    url = args.url.rstrip("/") + "/"
    pwcli = Path(args.pwcli).expanduser()
    if not pwcli.is_file():
        raise SmokeFailure(f"Playwright CLI wrapper not found: {pwcli}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_session = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in args.session)
    health = _health(url)
    session = args.session
    assertions: List[str] = []

    def cli(*parts: str) -> str:
        command = [str(pwcli), f"-s={session}", *parts]
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = _redact(completed.stdout or "")
        if completed.returncode:
            raise SmokeFailure(f"Playwright command failed ({' '.join(parts[:2])}):\n{output}")
        return output

    opened = False
    started = time.monotonic()
    try:
        open_args = ["open", url]
        if args.headed:
            open_args.append("--headed")
        cli(*open_args)
        opened = True

        # Settings are saved through the actual controls.  The fixture server
        # re-labels the post-save observation as fixture without changing the
        # production provider semantics.
        cli("click", "#settings-panel > summary")
        cli("fill", "#st-model", "fixture-model")
        cli("fill", "#st-key", FIXTURE_KEY)
        cli("click", "#settings-save")
        cli(
            "eval",
            "() => { const key = document.querySelector('#st-key'); const text = document.querySelector('#settings-connection').textContent; if (!key || key.type !== 'password' || key.value !== '' || !text.includes('测试夹具')) throw new Error('settings masking/fixture label failed'); return 'settings-ok'; }",
        )
        assertions.append("settings_masked_and_fixture_label")

        cli("fill", "#topic", "本市图书馆夜间开放试点")
        cli("click", "#search-btn")
        cli(
            "eval",
            "() => { const count = document.querySelectorAll('#result .candidate').length; if (count !== 5) throw new Error('expected five fixture candidates, got ' + count); return 'five-candidates-ok'; }",
        )
        assertions.append("five_offline_reference_candidates")

        with tempfile.TemporaryDirectory(prefix="deeptalk-issue38-audio-") as temp_root:
            wav_path = Path(temp_root) / "smoke.wav"
            _write_fixture_wav(wav_path)
            cli("click", "#audio-file")
            cli("upload", str(wav_path))
            cli("click", "#audio-import")
            cli(
                "eval",
                "() => { const summary = document.querySelector('#audio-import-summary').textContent; const preview = document.querySelector('#audio-preview'); if (!summary.includes('SHA-256') || !summary.includes('1,644 bytes') || preview.hidden) throw new Error('audio import/preview failed'); return 'audio-import-ok'; }",
            )
            assertions.append("audio_import_hash_and_preview")

            cli("click", "#audio-deliver")
            cli(
                "eval",
                "() => { const text = document.body.textContent; const timeline = document.querySelectorAll('#audio-timeline li').length; const artifacts = document.querySelectorAll('#audio-artifacts a').length; if (!text.includes('WAITING_FOR_OWNER_REVIEW')) throw new Error('typed owner-review gate missing'); if (timeline || artifacts) throw new Error('delivery produced timeline/artifacts despite missing reviewed material'); return 'owner-review-gate-ok'; }",
            )
            assertions.append("typed_owner_review_gate")

            cli("reload")
            cli(
                "eval",
                "() => { const text = document.body.textContent; if (!text.includes('SHA-256') || !text.includes('WAITING_FOR_OWNER_REVIEW')) throw new Error('state did not survive reload'); return 'reload-persistence-ok'; }",
            )
            assertions.append("audio_and_failure_state_persisted")

        cli("resize", "375", "900")
        cli(
            "eval",
            "() => { if (window.innerWidth !== 375 || document.documentElement.scrollWidth > window.innerWidth) throw new Error('narrow layout overflows: ' + document.documentElement.scrollWidth); return 'mobile-layout-ok'; }",
        )
        assertions.append("mobile_375_no_horizontal_overflow")
        cli("eval", "() => { document.querySelector('#topic').focus(); return 'focus-ok'; }")
        for _ in range(8):
            cli("press", "Tab")
        cli(
            "eval",
            "() => { if (!document.activeElement || document.activeElement === document.body) throw new Error('keyboard focus was lost'); return 'keyboard-ok'; }",
        )
        assertions.append("keyboard_focus_reaches_controls")

        mobile_shot = output_dir / f"issue38-{safe_session}-mobile.png"
        cli("screenshot", "--filename", str(mobile_shot), "--full-page")
        cli("resize", "1440", "1000")
        desktop_shot = output_dir / f"issue38-{safe_session}-desktop.png"
        cli("screenshot", "--filename", str(desktop_shot), "--full-page")
        assertions.append("desktop_and_mobile_screenshots")
    finally:
        if opened and not args.keep_open:
            try:
                cli("close")
            except SmokeFailure:
                pass

    return {
        "status": "PASS",
        "url": url,
        "health": health,
        "assertions": assertions,
        "screenshots": [
            str(output_dir / f"issue38-{safe_session}-desktop.png"),
            str(output_dir / f"issue38-{safe_session}-mobile.png"),
        ],
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "limitations": [
            "offline fixture only; no DeepSeek or other paid model call",
            "owner API key, private audio, rights decisions, and real creative quality remain unverified",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="fixture server URL")
    parser.add_argument("--session", default="deeptalk-issue38-smoke")
    parser.add_argument("--pwcli", default=str(_default_pwcli()))
    parser.add_argument("--output-dir", default="output/playwright")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(args)
    except (OSError, SmokeFailure, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": _redact(str(exc))}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
