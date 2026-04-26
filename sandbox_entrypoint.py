#!/usr/bin/env python3
"""
Runs inside the gVisor container.
Reads a JSON payload from stdin: {"code": "...", "provider": {"title": "...", "completed": false}}
Executes the code with a BaseProvider injected, then prints the result as JSON to stdout.

Security model (defence in depth):
- exec() runs with __builtins__: {} — no stdlib access via name lookup
- signal.SIGALRM enforces a hard in-process timeout
- gVisor (runsc) provides OS-level syscall isolation, containing any Python-level
  sandbox escapes via object introspection (e.g. __class__.__mro__ traversal)
- --network=none on the Docker invocation blocks all outbound network access
"""
import json
import signal
import sys

EXEC_TIMEOUT = 8  # seconds — less than the outer Docker timeout (10s)


class BaseProvider:
    def __init__(self, data: dict):
        self.title = data["title"]
        self.completed = data["completed"]


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Code execution exceeded {EXEC_TIMEOUT}s")


def main():
    try:
        payload = json.loads(sys.stdin.read())
        code = payload["code"]
        provider = BaseProvider(payload["provider"])
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        sys.exit(1)

    restricted_globals = {
        "__builtins__": {},
        "provider": provider,
        "json": json,
        "print": print,
    }

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(EXEC_TIMEOUT)
    try:
        exec(code, restricted_globals, {})  # noqa: S102
    finally:
        signal.alarm(0)  # cancel alarm regardless of outcome


if __name__ == "__main__":
    main()
