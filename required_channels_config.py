"""Repository-pinned channels plus existing runtime membership configuration."""
import json
import os
from pathlib import Path

DEFAULTS_FILE = Path(__file__).with_name("required_channels.defaults.json")


def pinned_channels():
    with DEFAULTS_FILE.open(encoding="utf-8") as stream:
        return json.load(stream)


def merge_channels(runtime, defaults, environ=None, include_pending=False):
    environ = os.environ if environ is None else environ
    runtime = runtime if isinstance(runtime, list) else []
    existing = {row["link"]: dict(row) for row in runtime
                if isinstance(row, dict) and row.get("link")}
    result = []
    for configured in defaults:
        link = configured["link"]
        previous = existing.pop(link, {})
        row = {**previous, **configured, "pinned": True}
        # Preserve previously resolved private IDs when the source has a placeholder.
        if not row.get("chat_id") and previous.get("chat_id"):
            row["chat_id"] = previous["chat_id"]
        env_value = str(environ.get(configured.get("chat_id_env", ""), "")).strip()
        if env_value.startswith("-") and env_value[1:].isdigit():
            row["chat_id"] = int(env_value)
        row["verification_pending"] = not bool(row.get("chat_id") or row.get("username"))
        # A newly staged invite URL alone cannot be used with getChatMember.
        # Do not create an impossible gate; retain any pre-existing gate as-is.
        if include_pending or not row["verification_pending"] or previous:
            result.append(row)
    # Keep every existing requirement that is not in the pinned list.
    result.extend(existing.values())
    return result


def load_channels(runtime_file, include_pending=False):
    try:
        with open(runtime_file, encoding="utf-8") as stream:
            runtime = json.load(stream)
    except (OSError, ValueError):
        runtime = []
    return merge_channels(runtime, pinned_channels(), include_pending=include_pending)
