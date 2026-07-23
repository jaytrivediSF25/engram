"""engram command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .store import (
    DEFAULT_ANCHOR_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_WINDOW_TOKENS,
    Store,
    StoreNotFound,
)


def _die(msg: str, code: int = 1) -> "NoReturn":  # noqa: F821
    print(f"engram: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _read_content(args) -> str:
    if args.text is not None:
        content = args.text
    elif args.file is not None:
        try:
            with open(args.file) as f:
                content = f.read()
        except OSError as e:
            _die(f"cannot read {args.file}: {e}")
    else:
        if sys.stdin.isatty():
            _die("no input: pass --text/--file or pipe content on stdin")
        content = sys.stdin.read()
    if not content.strip():
        _die("input is empty")
    return content


# ── subcommands ──────────────────────────────────────────────────────────


def cmd_init(args) -> None:
    store = Store.create(
        os.getcwd(),
        window_tokens=args.window_tokens,
        anchor_tokens=args.anchor_tokens,
        model=args.model,
    )
    print(f"initialized engram store for {store.config['project_path']}")
    print(
        f"  window {store.window_tokens} tokens "
        f"(anchor {store.anchor_budget} + sliding {store.sliding_budget}), "
        f"model {store.model}"
    )


def cmd_add(args) -> None:
    from .compact import CompactionError, compact
    from .tokens import count_tokens

    store = Store.load_or_create(os.getcwd())
    content = _read_content(args)

    if args.anchor:
        actual = count_tokens(content, store.model)
        if actual > store.anchor_budget:
            print(
                f"engram: anchor content is {actual} tokens (cap {store.anchor_budget}); compacting",
                file=sys.stderr,
            )
            try:
                content = compact(content, store.model, store.anchor_budget)
            except CompactionError as e:
                _die(str(e))
            actual = count_tokens(content, store.model)
        store.set_anchor(content, actual)
        print(f"anchor set ({actual} tokens)")
        return

    try:
        result = store.add_chat(content, counter=count_tokens, compactor=compact)
    except CompactionError as e:
        _die(f"chat stored, but eviction aborted — {e}")
    print(f"stored chat #{result.chat.id} ({result.chat.tokens} tokens)")
    if result.anchor_built:
        print(
            f"anchor built from {len(result.evicted)} founding chat(s) "
            f"({store.state['anchor_tokens_actual']} tokens, pinned)"
        )
    elif result.evicted:
        ids = ", ".join(f"#{c.id}" for c in result.evicted)
        print(f"evicted oldest chat(s) {ids}")


def render_context(store: Store) -> str | None:
    anchor = store.anchor
    chats = store.chats()
    if not anchor and not chats:
        return None
    parts: list[str] = []
    if anchor:
        parts.append("## Project anchor (founding context)\n\n" + anchor.rstrip())
    if chats:
        body = "\n\n".join(
            f"### Chat #{c.id} ({c.created_at})\n\n{c.content.rstrip()}" for c in chats
        )
        parts.append("## Recent chats (oldest → newest)\n\n" + body)
    return "\n\n".join(parts)


def cmd_context(args) -> None:
    try:
        store = Store.load(os.getcwd())
    except StoreNotFound:
        print("(no engram context yet for this project)")
        return

    if args.json:
        print(
            json.dumps(
                {
                    "anchor": store.anchor,
                    "chats": [c.__dict__ for c in store.chats()],
                },
                indent=2,
            )
        )
        return

    rendered = render_context(store)
    print(rendered if rendered else "(no engram context yet for this project)")


def cmd_claude(args) -> None:
    """Launch Claude Code with the anchored sliding window active.

    Sets ENGRAM_ACTIVE so the SessionStart/SessionEnd hooks (which are inert
    otherwise) inject the context at start and capture the session at exit.
    """
    try:
        if render_context(Store.load(os.getcwd())) is None:
            raise StoreNotFound(os.getcwd())
    except StoreNotFound:
        print(
            "engram: no context for this project yet — this session will seed it",
            file=sys.stderr,
        )
    os.environ["ENGRAM_ACTIVE"] = "1"
    try:
        os.execvp("claude", ["claude", *args.extra])
    except FileNotFoundError:
        _die("`claude` not found on PATH — install Claude Code first")


def cmd_hook_session_start(args) -> None:
    """SessionStart hook: inject this project's engram context into the session.

    Inert unless the session was launched via `engram` (ENGRAM_ACTIVE=1),
    so plain `claude` sessions are untouched.
    """
    if not os.environ.get("ENGRAM_ACTIVE"):
        return
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    cwd = payload.get("cwd") or os.getcwd()
    try:
        rendered = render_context(Store.load(cwd))
    except StoreNotFound:
        return
    if not rendered:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "Prior project context from engram (anchored sliding window — "
                        "a pinned summary of founding context plus recent sessions):\n\n"
                        + rendered
                    ),
                }
            }
        )
    )


def cmd_hook_session_end(args) -> None:
    """SessionEnd hook: capture the session transcript as a new chat tile.

    Inert unless the session was launched via `engram` (ENGRAM_ACTIVE=1).
    """
    if not os.environ.get("ENGRAM_ACTIVE"):
        return
    from .capture import condense_transcript
    from .compact import CompactionError, compact
    from .tokens import count_tokens

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    cwd = payload.get("cwd")
    transcript_path = payload.get("transcript_path")
    if not cwd or not transcript_path:
        return

    condensed = condense_transcript(transcript_path)
    if condensed is None:
        return

    store = Store.load_or_create(cwd)
    try:
        result = store.add_chat(condensed, counter=count_tokens, compactor=compact)
        print(f"engram: captured session as chat #{result.chat.id}")
    except CompactionError as e:
        # Chat is stored; eviction retries next time compaction succeeds.
        print(f"engram: chat stored, eviction deferred — {e}", file=sys.stderr)


def cmd_status(args) -> None:
    try:
        store = Store.load(os.getcwd())
    except StoreNotFound:
        _die("no engram store for this project — run `engram init` or `engram add`")
    chats = store.chats()
    sliding = sum(c.tokens for c in chats)
    anchor_actual = store.state.get("anchor_tokens_actual", 0)
    print(f"project : {store.config['project_path']}")
    print(f"model   : {store.model}")
    print(f"window  : {store.window_tokens} tokens")
    print(
        f"anchor  : {'built' if store.state['anchor_built'] else '(not built yet)'}"
        + (f" — {anchor_actual}/{store.anchor_budget} tokens" if store.state["anchor_built"] else f" — cap {store.anchor_budget} tokens")
    )
    print(f"sliding : {sliding}/{store.sliding_budget} tokens across {len(chats)} chat(s)")
    for c in chats:
        preview = " ".join(c.content.split())[:60]
        print(f"  #{c.id:>4}  {c.tokens:>7} tok  {c.created_at}  {preview}")


def cmd_reset(args) -> None:
    try:
        store = Store.load(os.getcwd())
    except StoreNotFound:
        _die("no engram store for this project")
    if not args.force:
        reply = input(f"delete engram store for {store.config['project_path']}? [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("aborted")
            return
    store.reset()
    print("store deleted")


# ── entry point ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="engram",
        description="Anchored sliding window context manager: a pinned, "
        "LLM-compacted anchor of founding context plus a token-budgeted "
        "sliding window of recent chats.",
    )
    p.add_argument("--version", action="version", version=f"engram {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="create the store for the current directory")
    sp.add_argument("--window-tokens", type=int, default=DEFAULT_WINDOW_TOKENS)
    sp.add_argument("--anchor-tokens", type=int, default=DEFAULT_ANCHOR_TOKENS)
    sp.add_argument("--model", default=DEFAULT_MODEL)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="store a chat (stdin, --text, or --file)")
    sp.add_argument("--text", help="chat content as an argument")
    sp.add_argument("--file", help="read chat content from a file")
    sp.add_argument(
        "--anchor",
        action="store_true",
        help="write this content directly into the pinned anchor slot",
    )
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("context", help="print anchor + recent chats for injection")
    sp.add_argument("--json", action="store_true", help="machine-readable output")
    sp.set_defaults(func=cmd_context)

    sp = sub.add_parser(
        "claude", help="launch Claude Code with this project's context preloaded"
    )
    sp.add_argument(
        "extra", nargs=argparse.REMAINDER, help="extra args passed through to claude"
    )
    sp.set_defaults(func=cmd_claude)

    sp = sub.add_parser("status", help="show tiles and token budgets")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser(
        "hook-session-start", help="(Claude Code hook) inject context at session start"
    )
    sp.set_defaults(func=cmd_hook_session_start)

    sp = sub.add_parser(
        "hook-session-end", help="(Claude Code hook) capture the session at exit"
    )
    sp.set_defaults(func=cmd_hook_session_end)

    sp = sub.add_parser("reset", help="delete the store for the current directory")
    sp.add_argument("--force", action="store_true", help="skip confirmation")
    sp.set_defaults(func=cmd_reset)

    return p


COMMANDS = {
    "init",
    "add",
    "context",
    "status",
    "reset",
    "claude",
    "hook-session-start",
    "hook-session-end",
}


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    # Bare `engram` (or `engram <claude flags>`) launches Claude with the
    # anchored window; anything else is a normal subcommand.
    if not argv or argv[0] not in COMMANDS | {"-h", "--help", "--version"}:
        cmd_claude(argparse.Namespace(extra=list(argv)))
        return
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ValueError as e:
        _die(str(e))


if __name__ == "__main__":
    main()
