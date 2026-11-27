"""Keepalive healer must not soft-restart a channel a tuner client is watching."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamtv.api.channels import router as channels_router

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "heal_keepalive_tunes.py"


@pytest.fixture(scope="module")
def heal() -> ModuleType:
    spec = importlib.util.spec_from_file_location("heal_keepalive_tunes", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    ("clients", "skip"),
    [(None, True), (1, True), (2, True), (0, False)],
)
def test_should_skip_for_clients(heal: ModuleType, clients: int | None, skip: bool) -> None:
    assert heal.should_skip_for_clients(clients) is skip


def _client_with_streams(streams: dict[str, object]) -> TestClient:
    app = FastAPI()
    app.include_router(channels_router, prefix="/api")
    app.state.channel_manager = SimpleNamespace(_streams=streams)
    return TestClient(app)


def test_stream_clients_reports_connected_count() -> None:
    stream = SimpleNamespace(_client_count=1, _is_running=True)
    client = _client_with_streams({"1984.2": stream})
    resp = client.get("/api/channels/by-number/1984.2/stream-clients")
    assert resp.status_code == 200
    assert resp.json() == {"channel": "1984.2", "running": True, "clients": 1}


def test_stream_clients_zero_when_not_running() -> None:
    client = _client_with_streams({})
    resp = client.get("/api/channels/by-number/80/stream-clients")
    assert resp.status_code == 200
    assert resp.json() == {"channel": "80", "running": False, "clients": 0}


def test_record_keepalive_requires_two_consecutive(heal: ModuleType) -> None:
    state: dict = {"channels": {}}
    assert heal.record_keepalive_sample(state, "1992.2", keepalive_only=True) == 1
    assert heal.should_heal_for_consecutive(1, min_fails=2) is False
    assert heal.record_keepalive_sample(state, "1992.2", keepalive_only=True) == 2
    assert heal.should_heal_for_consecutive(2, min_fails=2) is True
    assert heal.record_keepalive_sample(state, "1992.2", keepalive_only=False) == 0
    assert heal.should_heal_for_consecutive(0, min_fails=2) is False


def test_default_tune_sec_at_least_30(heal: ModuleType) -> None:
    assert heal.TUNE_SEC >= 30
    assert heal.MIN_CONSECUTIVE_FAILS >= 2
