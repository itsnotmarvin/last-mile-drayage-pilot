"""Local graph inspection and check CLI; stdin/file input is never a tool argument."""

import argparse
import json
from pathlib import Path
import sys

from .mcp_server import strict_loads
from .service import CheckingService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    context = commands.add_parser("context")
    context.add_argument("topic", choices=["summary", "induction", "route_directions", "port_street", "coverage"])
    check = commands.add_parser("check")
    check.add_argument("--input", required=True, help="JSON file containing synthetic facts, or - for stdin")
    args = parser.parse_args()
    service = CheckingService()
    if args.command == "context":
        result = service.context(args.topic)
    else:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text()
        result = service.check(strict_loads(raw))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
