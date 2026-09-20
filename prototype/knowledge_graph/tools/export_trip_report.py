"""Export a fresh saved synthetic trip assessment through the controlled renderer."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neo4j_kg.assessment import TripService
from neo4j_kg.common import ArchiveError, EvidenceUnavailable
from neo4j_kg.config import connect
from neo4j_kg.decision_brief import render_trip_report
from neo4j_kg.service import InputError
from neo4j_kg.store import Neo4jStore
from neo4j_kg.trip_state import TripStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trip-id', required=True)
    parser.add_argument('--credentials-file', type=Path, required=True)
    parser.add_argument('--revision', required=True, help='Pinned, validated Neo4j release')
    parser.add_argument('--state-file', type=Path, default=ROOT / '.runtime/trips.sqlite3')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output path; saved reports are not overwritten.')
    if not args.state_file.is_file():
        parser.error('The saved trip database does not exist.')
    driver = None
    try:
        driver, database = connect(args.credentials_file)
        graph = Neo4jStore(driver, database, args.revision)
        service = TripService(graph, TripStore(args.state_file))
        assessment = service.assess({'trip_id': args.trip_id})
        report = render_trip_report(assessment)
        # Exclusive private creation: no external scripts, model prose, or arbitrary
        # JSON file can be substituted for this service-produced assessment.
        import os
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            output.write(report)
        print('Saved synthetic assessment snapshot. Operational permission is not issued.')
    except (ArchiveError, EvidenceUnavailable, InputError):
        parser.exit(1, 'Unable to export a valid saved assessment; no permission is available.\n')
    finally:
        if driver is not None:
            driver.close()


if __name__ == '__main__':
    main()
