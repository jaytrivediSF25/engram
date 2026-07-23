"""Eviction / anchor logic tests — token counter and compactor are stubbed."""

import pytest

import acw.store as store_mod
from acw.store import Store


def word_counter(text: str, model: str) -> int:
    return len(text.split())


def stub_compactor(founding_text: str, model: str, anchor_budget: int) -> str:
    return f"ANCHOR<{founding_text.count('---') + 1} chats>"


def failing_compactor(founding_text: str, model: str, anchor_budget: int) -> str:
    raise RuntimeError("api down")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "ROOT", tmp_path / "projects")
    # window 30, anchor 10 → sliding budget 20 (word-count "tokens")
    return Store.create(tmp_path / "proj", window_tokens=30, anchor_tokens=10)


def chat_text(n: int, words: int = 8) -> str:
    return " ".join([f"chat{n}"] * words)


def test_no_eviction_under_budget(store):
    r1 = store.add_chat(chat_text(1), word_counter, stub_compactor)
    r2 = store.add_chat(chat_text(2), word_counter, stub_compactor)
    assert r1.evicted == [] and r2.evicted == []
    assert [c.id for c in store.chats()] == [1, 2]
    assert store.anchor is None


def test_first_eviction_builds_anchor_once(store):
    store.add_chat(chat_text(1), word_counter, stub_compactor)
    store.add_chat(chat_text(2), word_counter, stub_compactor)
    r3 = store.add_chat(chat_text(3), word_counter, stub_compactor)  # 24 > 20

    assert [c.id for c in r3.evicted] == [1]
    assert r3.anchor_built is True
    assert store.anchor == "ANCHOR<1 chats>"
    assert store.state["anchor_built"] is True
    assert [c.id for c in store.chats()] == [2, 3]

    # Later evictions drop tiles but never touch the anchor.
    r4 = store.add_chat(chat_text(4), word_counter, failing_compactor)
    assert [c.id for c in r4.evicted] == [2]
    assert r4.anchor_built is False
    assert store.anchor == "ANCHOR<1 chats>"  # pinned, unchanged
    assert [c.id for c in store.chats()] == [3, 4]


def test_multi_chat_eviction_compacts_all_founding_chats(store):
    store.add_chat(chat_text(1, 6), word_counter, stub_compactor)
    store.add_chat(chat_text(2, 6), word_counter, stub_compactor)
    r = store.add_chat(chat_text(3, 18), word_counter, stub_compactor)  # 30 > 20
    assert [c.id for c in r.evicted] == [1, 2]
    assert store.anchor == "ANCHOR<2 chats>"


def test_newest_chat_never_evicted(store):
    r = store.add_chat(chat_text(1, 50), word_counter, stub_compactor)  # over budget alone
    assert r.evicted == []
    assert [c.id for c in store.chats()] == [1]


def test_compaction_failure_aborts_eviction(store):
    store.add_chat(chat_text(1), word_counter, stub_compactor)
    store.add_chat(chat_text(2), word_counter, stub_compactor)
    with pytest.raises(RuntimeError, match="api down"):
        store.add_chat(chat_text(3), word_counter, failing_compactor)
    # New chat stored, nothing evicted, no anchor.
    assert [c.id for c in store.chats()] == [1, 2, 3]
    assert store.anchor is None
    assert store.state["anchor_built"] is False
    # Retry with a working compactor recovers.
    r = store.add_chat(chat_text(4), word_counter, stub_compactor)
    assert len(r.evicted) >= 1 and store.anchor is not None


def test_anchor_must_be_smaller_than_window(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "ROOT", tmp_path / "projects")
    with pytest.raises(ValueError):
        Store.create(tmp_path / "proj", window_tokens=100, anchor_tokens=100)
