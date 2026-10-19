"""Offline ByMykel adapter. Match language/variant records by source ID, never names.

No downloads, license approval, image licensing or production publication are automatic.
Input: actual skins_not_grouped.json or a simple category file from a pinned revision.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from pydantic import HttpUrl

from app.catalog import CatalogImport, Category, ItemInput, VariantInput


def normalize(en: list[dict], zh: list[dict], category: Category, revision: str,
              verified_at: datetime, evidence_url: str) -> CatalogImport:
    translations = {row['id']: row for row in zh}
    grouped: dict[str, ItemInput] = {}
    seen: set[str] = set()
    for row in en:
        external_key = row['id']
        if external_key in seen:
            raise ValueError('duplicate upstream ID')
        seen.add(external_key)
        # Upstream supplies skin_id for wear/StatTrak/souvenir variants.
        base = row.get('skin_id', external_key)
        translated = translations.get(external_key, {})
        if base not in grouped:
            grouped[base] = ItemInput(external_key=base, category=category, name_en=row['name'],
                                      name_zh=translated.get('name'),
                                      market_hash_name=row.get('market_hash_name') if base == external_key else None,
                                      tradable=row.get('tradable'), marketable=row.get('marketable'))
        if base != external_key:
            grouped[base].variants.append(VariantInput(
                external_key=external_key, market_hash_name=row.get('market_hash_name'),
                wear=row.get('wear', {}).get('id'), stattrak=row.get('stattrak'),
                souvenir=row.get('souvenir'), paint_index=row.get('paint_index')))
    # Grouped skin names use source ID until an actual grouped record is supplied.
    # A representative variant name is kept as an explicit display label, not a cross-market match.
    return CatalogImport(source_code='bymykel', dataset_revision=revision, evidence_url=HttpUrl(evidence_url),
                         verified_at=verified_at, items=list(grouped.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--en', type=Path, required=True)
    parser.add_argument('--zh', type=Path)
    parser.add_argument('--category', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--verified-at', required=True)
    parser.add_argument('--evidence-url', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    batch = normalize(json.loads(args.en.read_text()), json.loads(args.zh.read_text()) if args.zh else [],
                      args.category, args.revision, datetime.fromisoformat(args.verified_at), args.evidence_url)
    args.out.write_text(batch.model_dump_json(indent=2))


if __name__ == '__main__':
    main()
