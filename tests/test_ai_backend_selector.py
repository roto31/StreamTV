"""Unit tests for AI backend selection (no live bridge required)."""

from streamtv.utils.ai_backend_selector import resolve_backend


def test_resolve_auto_prefers_fm_when_available() -> None:
    assert (
        resolve_backend("auto", fm_available=True, ollama_available=True)
        in ("foundation_models", "ollama")
    )


def test_resolve_explicit_fm() -> None:
    assert (
        resolve_backend("foundation_models", fm_available=True, ollama_available=False)
        == "foundation_models"
    )
    assert (
        resolve_backend("foundation_models", fm_available=False, ollama_available=True)
        == "none"
    )


def test_resolve_explicit_ollama() -> None:
    assert (
        resolve_backend("ollama", fm_available=True, ollama_available=True) == "ollama"
    )
    assert (
        resolve_backend("ollama", fm_available=True, ollama_available=False) == "none"
    )


def test_resolve_none() -> None:
    assert resolve_backend("none", fm_available=True, ollama_available=True) == "none"


def test_resolve_auto_falls_back_to_ollama() -> None:
    assert (
        resolve_backend("auto", fm_available=False, ollama_available=True) == "ollama"
    )


def test_resolve_auto_none_when_neither() -> None:
    assert resolve_backend("auto", fm_available=False, ollama_available=False) == "none"
