#!/usr/bin/env python3
"""
Runs inside the gVisor container.
Reads a JSON payload from stdin: {"code": "...", "provider": {"title": "...", "completed": false}}
Executes the code with a BaseProvider injected, then prints the result as JSON to stdout.
"""
import json
import sys


class BaseProvider:
    def __init__(self, data: dict):
        self.title = data["title"]
        self.completed = data["completed"]


def main():
    payload = json.loads(sys.stdin.read())
    code = payload["code"]
    provider = BaseProvider(payload["provider"])

    restricted_globals = {
        "__builtins__": {},
        "provider": provider,
        "json": json,
        "print": print,
    }

    exec(code, restricted_globals, {})  # noqa: S102


if __name__ == "__main__":
    main()
