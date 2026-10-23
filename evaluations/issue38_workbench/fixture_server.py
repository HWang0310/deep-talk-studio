#!/usr/bin/env python3
"""Offline-only loopback server for the Issue #38 browser smoke.

This process is deliberately labelled ``fixture`` by WorkbenchFlow.  It is
only for checking browser layout, keyboard flow, persistence and typed
failure states; it must never be used as evidence of DeepSeek creative
quality, Bilibili availability, rights clearance, or a publish-ready episode.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from deeptalk_studio.bilibili_reference_provider import (
    SearchItem,
    SearchOutcome,
    VideoMetadataOutcome,
)
from deeptalk_studio.reference_discovery import build_reference_candidate_set
from deeptalk_studio.webui import DEFAULT_HOST, make_server
from deeptalk_studio.workbench.flow import WorkbenchFlow


class OfflineProvider:
    """Deterministic discovery provider; it never opens a network socket."""

    _bvids = (
        "BV1hi000000A",
        "BV1hi000000B",
        "BV1hi000000C",
        "BV1hi000000D",
        "BV1hi000000E",
    )

    def search_videos(self, query: str, page: int = 1) -> SearchOutcome:
        items = tuple(
            SearchItem(
                bvid=bvid,
                title=f"{query} · 离线浏览器夹具参考 {index}",
                uploader="Issue38 fixture",
                published_at="2026-10-21T00:00:00+00:00",
                snippet_view_count=100000 - index * 1000,
                description="offline fixture only",
            )
            for index, bvid in enumerate(self._bvids, start=1)
        )
        return SearchOutcome(
            status="ok", items=items, http_status=200, api_code=0, message=""
        )

    def fetch_video_metadata(self, bvid: str) -> VideoMetadataOutcome:
        return VideoMetadataOutcome(
            status="ok",
            title=f"离线元数据 {bvid}",
            uploader="Issue38 fixture",
            published_at="2026-10-21T00:00:00+00:00",
            view_count=100000,
            duration_sec=120,
            api_code=0,
            message="",
        )


def _fixture_discovery(topic, urls, count=5):
    """Keep direct flow starts deterministic if the harness calls one."""

    provider = OfflineProvider()
    artifact = build_reference_candidate_set(topic, list(urls), provider=provider)
    artifact["candidates"] = artifact.get("candidates", [])[:count]
    return artifact


def _fixture_fetcher(url):
    return {"ok": False, "url": str(url), "error": "Issue38 offline fixture: no network"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue #38 offline fixture WebUI server")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    provider = OfflineProvider()
    flow = WorkbenchFlow(
        root,
        discovery_runner=_fixture_discovery,
        provider_factory=lambda settings: (_ for _ in ()).throw(
            RuntimeError("Issue38 fixture does not provide an LLM")
        ),
        fetcher=_fixture_fetcher,
        connection_kind="fixture",
    )

    # Saving settings normally invalidates the previous connection observation
    # (correct for a real provider).  Keep the fixture label truthful for this
    # offline harness after that normal reset; this wrapper never changes the
    # product's real-provider semantics or stores a credential in the fixture.
    original_save_settings = flow.save_settings

    def fixture_save_settings(payload):
        result = original_save_settings(payload)
        flow._record_connection_observation({"connection_kind": "fixture"})
        result["connection_kind"] = "fixture"
        return result

    flow.save_settings = fixture_save_settings
    # Persist only the non-secret provenance label so the browser cannot
    # mistake this offline server for a real provider connection.
    flow._record_connection_observation({"connection_kind": "fixture"})
    server = make_server(
        args.port,
        output_dir=root / "discoveries",
        provider_factory=lambda: provider,
        flow=flow,
    )
    print(f"http://{DEFAULT_HOST}:{server.server_address[1]}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
