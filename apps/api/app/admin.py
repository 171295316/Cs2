"""Local-only, explicit rights approval. This command is never exposed over HTTP."""
import argparse

from sqlalchemy import select

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
    parser.add_argument('--confirm-redistribution-rights', action='store_true')
    parser.add_argument('--disable', action='store_true', help='撤销指定范围授权')
    args = parser.parse_args()
    if not args.disable and not args.confirm_redistribution_rights:
        parser.error('启用来源必须显式确认已经核验再分发权利')
    with SessionLocal.begin() as db:
        if args.disable:
            source = db.scalar(select(Source).where(Source.code == args.code))
            if source is None:
                parser.error('来源不存在')
            if args.scope == 'catalog':
                source.redistribution_allowed = False
            else:
                grant = db.scalar(select(SourceGrant).where(SourceGrant.source_id == source.id,
                                                           SourceGrant.dataset == args.scope))
                if grant is None:
                    parser.error('专项授权不存在')
                grant.enabled = False
            return
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
