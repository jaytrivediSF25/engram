"""Security tests: secret redaction, file permissions, injection fencing."""

import os
import stat

import pytest

import engram.store as store_mod
from engram.secure import redact, secure_write_text
from engram.store import Store


def word_counter(text, model=None):
    return len(text.split())


def stub_compactor(founding_text, model, anchor_budget):
    return "ANCHOR"


# ── secret redaction ──────────────────────────────────────────────────────


# Fixtures are assembled from fragments so no literal token sits in the source
# (that would trip secret scanners / push protection) — but the reassembled
# runtime string still matches the redaction patterns. All-zero bodies keep them
# obviously fake.
_FAKE_SECRETS = [
    "sk-ant-" + "0" * 40,          # Anthropic
    "sk-" + "0" * 40,              # OpenAI
    "AKIA" + "0" * 16,             # AWS access key id
    "ghp_" + "0" * 36,             # GitHub PAT
    "AIza" + "0" * 35,             # Google API key
    "xoxb-" + "0" * 24,            # Slack bot token shape
    "sk_" + "live_" + "0" * 24,    # Stripe secret key shape
]


@pytest.mark.parametrize("secret", _FAKE_SECRETS)
def test_known_secret_shapes_are_redacted(secret):
    out = redact(f"here is my key: {secret} ok")
    assert secret not in out
    assert "redacted" in out


def test_assignment_form_redacted():
    for line in [
        'API_KEY="supersecretvalue123"',
        "DATABASE_PASSWORD=hunter2hunter2",
        "aws_secret_access_key: wJalrXUtnFEMIabcdefghijklmnop",
    ]:
        out = redact(line)
        assert "supersecret" not in out
        assert "hunter2hunter2" not in out
        assert "wJalrXUtnFEMIabcdefghijklmnop" not in out


def test_private_key_block_redacted():
    blob = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    out = redact(f"key follows\n{blob}\ndone")
    assert "MIIEpAIBAAKCAQEA" not in out
    assert "‹redacted:PRIVATE_KEY›" in out


def test_ordinary_text_untouched():
    text = "We chose Flask over Node. Budget is $2000. Deadline Q3."
    assert redact(text) == text


def test_redaction_happens_on_capture(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "ROOT", tmp_path / "projects")
    store = Store.create(tmp_path / "proj", window_tokens=10_000, anchor_tokens=2_000)
    token = "ghp_" + "0" * 36
    store.add_chat(f"deploying with token {token} now", word_counter, stub_compactor)
    stored = store.chats()[0].content
    assert token not in stored
    assert "redacted" in stored


# ── file permissions ──────────────────────────────────────────────────────


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_store_files_are_private(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "ROOT", tmp_path / "projects")
    store = Store.create(tmp_path / "proj", window_tokens=10_000, anchor_tokens=2_000)
    store.add_chat("some project detail here", word_counter, stub_compactor)

    for rel in ("config.json", "state.json"):
        mode = stat.S_IMODE(os.stat(store.root / rel).st_mode)
        assert mode == 0o600, f"{rel} is {oct(mode)}, expected 0600"
    assert stat.S_IMODE(os.stat(store.root).st_mode) == 0o700
    chat_file = next((store.root / "chats").glob("*.json"))
    assert stat.S_IMODE(os.stat(chat_file).st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_secure_write_is_atomic_and_private(tmp_path):
    target = tmp_path / "sub" / "file.txt"
    secure_write_text(target, "hello")
    assert target.read_text() == "hello"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    # no leftover temp file
    assert not list(tmp_path.rglob("*.tmp"))
