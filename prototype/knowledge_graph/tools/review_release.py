"""Read-only source/release review. Never imports or activates a graph release.

Exit 0: report produced; exit 2: readiness is blocked; exit 1: invalid inputs.
The output is JSON on stdout, or a new owner-only file; existing files are refused.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neo4j_kg.common import ArchiveError
from neo4j_kg.release_readiness import assess_readiness
from neo4j_kg.source_review import compare_releases, review_packet, source_inventory
from trip_app.operations import private_write


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('inventory', 'packet', 'compare', 'readiness'):
        command = commands.add_parser(name)
        command.add_argument('--output', type=Path)
        if name == 'compare':
            command.add_argument('--baseline', type=Path, required=True)
            command.add_argument('--candidate', type=Path, required=True)
        else:
            command.add_argument('--release', type=Path, default=ROOT/'data/neo4j_release.json')
        if name == 'readiness':
            command.add_argument('--scope', type=Path, default=ROOT/'data/release_scope.json')
            command.add_argument('--capture', type=Path)
    args = parser.parse_args(argv)
    def read(path):
        return json.loads(path.read_text())
    try:
        if args.command == 'compare':
            result = compare_releases(read(args.baseline), read(args.candidate))
        elif args.command == 'readiness':
            result = assess_readiness(read(args.release), read(args.scope), args.capture)
        else:
            result = (source_inventory if args.command == 'inventory' else review_packet)(read(args.release))
        encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        if args.output:
            private_write(args.output, encoded)
        else:
            sys.stdout.write(encoded)
        return 2 if args.command == 'readiness' and result['status'] == 'blocked' else 0
    except (ArchiveError, OSError, ValueError, TypeError, KeyError, AttributeError):
        parser.exit(1, 'Review failed: check release integrity, scope, input paths and that the output file is new. No activation performed.\n')


if __name__ == '__main__':
    sys.exit(main())
