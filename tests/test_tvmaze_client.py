"""Unit tests for TVMaze client auth wiring (no live network)."""

from __future__ import annotations

import httpx

from streamtv.utils.metadata_providers import TVMazeClient, create_metadata_manager


def test_tvmaze_client_auth_none_without_credentials() -> None:
    client = TVMazeClient()
    assert client._auth() is None
    client2 = TVMazeClient(username="only_user")
    assert client2._auth() is None
    client3 = TVMazeClient(api_key="only_key")
    assert client3._auth() is None


def test_tvmaze_client_auth_basic_when_complete() -> None:
    client = TVMazeClient(username="demo", api_key="secret-key")
    auth = client._auth()
    assert isinstance(auth, httpx.BasicAuth)
    # httpx BasicAuth encodes username:password
    header = auth._auth_header
    assert header.startswith("Basic ")


def test_tvmaze_client_strips_whitespace() -> None:
    client = TVMazeClient(username="  demo  ", api_key="  key  ")
    assert client.username == "demo"
    assert client.api_key == "key"
    assert client._auth() is not None


def test_create_metadata_manager_wires_tvmaze_credentials() -> None:
    mgr = create_metadata_manager(
        enable_tvdb=False,
        enable_tvmaze=True,
        enable_tmdb=False,
        tvmaze_username="maze_user",
        tvmaze_api_key="maze_key",
    )
    assert mgr.tvmaze is not None
    assert mgr.tvmaze.username == "maze_user"
    assert mgr.tvmaze.api_key == "maze_key"
    assert mgr.tvdb is None
    assert mgr.tmdb is None


def test_create_metadata_manager_disables_tvmaze() -> None:
    mgr = create_metadata_manager(enable_tvmaze=False)
    assert mgr.tvmaze is None
