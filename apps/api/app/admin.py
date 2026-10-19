"""Local-only, explicit rights approval. This command is never exposed over HTTP."""
import argparse

from app.catalog import stable_id
from app.db import SessionLocal
from app.models import Source, SourceGrant


def main():
    parser = argparse.ArgumentParser(description='Register source approval after checking redistribution rights')
    parser.add_argument('--scope', choices=['catalog', 'prices', 'supply'], default='catalog')
    parser.add_argument('--code', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--homepage', required=True)
    parser.add_argument('--license-reference', required=True)
    parser.add_argument('--confirm-redistribution-rights', action='store_true', required=True)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        source = Source(id=stable_id('source:' + args.code), code=args.code, name=args.name,
                        homepage=args.homepage, license_status='approved',
                        license_reference=args.license_reference, redistribution_allowed=True)
        db.merge(source)
        db.flush()
        if args.scope != 'catalog':
            db.merge(SourceGrant(id=stable_id('grant:' + source.id + ':' + args.scope), source_id=source.id,
                                 dataset=args.scope, license_reference=args.license_reference, enabled=True))


if __name__ == '__main__':
    main()
