export type Item = {
  id: string; canonical_key: string; category: string; name_en: string; name_zh: string | null;
  market_hash_name: string | null; image_url: string | null; updated_at: string;
  tradable: boolean | null; marketable: boolean | null;
};
export type Provenance = {
  source: string; name: string; external_key: string; variant_id: string | null;
  as_of: string; dataset_revision: string; evidence_url: string; license_reference: string;
};
export type Variant = { id: string; variant_key: string; market_hash_name: string | null;
  wear: string | null; stattrak: boolean | null; souvenir: boolean | null; paint_index: number | null; };
export type Catalog = { status: string; items: Item[]; next_cursor: string | null; };
export const categories: Record<string, string> = {
  skin: '枪皮', knife: '刀', glove: '手套', case: '武器箱', collection_package: '收藏包',
  sticker: '贴纸', capsule: '胶囊', agent: '探员', music_kit: '音乐盒', keychain: '挂件',
  graffiti: '涂鸦', patch: '布章', tool: '工具', other: '其他',
};
export async function api<T>(path: string): Promise<{ data: T | null; status: number }> {
  try {
    const response = await fetch(`${process.env.API_URL || 'http://localhost:8000'}${path}`, {
      cache: 'no-store', signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return { data: null, status: response.status };
    return { data: await response.json() as T, status: response.status };
  } catch { return { data: null, status: 503 }; }
}
