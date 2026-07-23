"""CLI tests — network functions stubbed via monkeypatch."""

import pytest

import engram.compact
import engram.store as store_mod
import engram.tokens
from engram.cli import main


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "ROOT", tmp_path / "projects")
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setattr(engram.tokens, "count_tokens", lambda text, model: len(text.split()))
    monkeypatch.setattr(
        engram.compact, "compact", lambda text, model, budget: "compacted anchor"
    )
    return proj


def test_init_and_status(project, capsys):
    main(["init", "--window-tokens", "30", "--anchor-tokens", "10"])
    out = capsys.readouterr().out
    assert "initialized" in out

    main(["status"])
    out = capsys.readouterr().out
    assert "window  : 30 tokens" in out
    assert "not built yet" in out


def test_add_context_roundtrip(project, capsys):
    main(["init", "--window-tokens", "30", "--anchor-tokens", "10"])
    capsys.readouterr()

    main(["add", "--text", "alpha " * 8])
    assert "stored chat #1 (8 tokens)" in capsys.readouterr().out
    main(["add", "--text", "beta " * 8])
    capsys.readouterr()
    main(["add", "--text", "gamma " * 8])  # 24 > 20 → evict #1, build anchor
    out = capsys.readouterr().out
    assert "anchor built from 1 founding chat(s)" in out

    main(["context"])
    out = capsys.readouterr().out
    assert "## Project anchor (founding context)" in out
    assert "compacted anchor" in out
    assert "Chat #2" in out and "Chat #3" in out
    assert "Chat #1" not in out  # evicted


def test_context_without_store(project, capsys):
    main(["context"])
    assert "no engram context yet" in capsys.readouterr().out


def test_add_anchor_direct(project, capsys):
    main(["add", "--anchor", "--text", "the founding facts"])
    assert "anchor set (3 tokens)" in capsys.readouterr().out
    main(["context"])
    assert "the founding facts" in capsys.readouterr().out


def test_reset_force(project, capsys):
    main(["add", "--text", "hello world"])
    capsys.readouterr()
    main(["reset", "--force"])
    assert "store deleted" in capsys.readouterr().out
    main(["context"])
    assert "no engram context yet" in capsys.readouterr().out


def test_empty_input_errors(project, capsys):
    with pytest.raises(SystemExit):
        main(["add", "--text", "   "])
