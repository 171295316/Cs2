import Link from 'next/link';
import PricePanel, { type MarketParams } from '../../../components/PricePanel';
import { notFound } from 'next/navigation';
import { api, categories, type Item, type Provenance, type Variant } from '../../../lib/api';

export default async function Detail({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<MarketParams> }) {
  const { id } = await params;
  const filters = await searchParams;
  const result = await api<Item & { provenance: Provenance[] }>(`/v1/items/${encodeURIComponent(id)}`);
  if (result.status === 404 || result.status === 422) notFound();
  if (!result.data) return <main className="mx-auto max-w-5xl p-8"><Link href="/items">← 饰品目录</Link><p role="status">目录服务暂时不可用，请稍后重试。</p></main>;
  const item = result.data;
  const variants = await api<{ items: Variant[] }>(`/v1/items/${encodeURIComponent(id)}/variants`);
  return <main className="mx-auto max-w-5xl p-8">
    <Link href="/items">← 饰品目录</Link>
    <h1 className="my-6 text-3xl">{item.name_zh || item.name_en}</h1><p>{item.name_en}</p>
    <p className="text-slate-400">{categories[item.category]} · {item.canonical_key}</p>
    <h2 className="mb-3 mt-8 text-xl">可核实变体</h2>
    {!variants.data ? <p>变体服务暂时不可用。</p> : variants.data.items.length === 0 ? <p>暂无可核实变体数据。</p>
      : <ul className="space-y-3">{variants.data.items.map(v => <li key={v.id} className="rounded border border-slate-700 p-4">
        <p>{v.market_hash_name || v.variant_key}</p>
        <p className="text-sm text-slate-400">磨损：{v.wear || '未知'} · StatTrak：{v.stattrak === null ? '未知' : v.stattrak ? '是' : '否'} · 纪念品：{v.souvenir === null ? '未知' : v.souvenir ? '是' : '否'}</p>
      </li>)}</ul>}
    <PricePanel id={id} params={filters} />
    <h2 className="mb-4 text-xl">目录来源与核验时间</h2>
    <ul className="space-y-4">{item.provenance.map(p => <li key={`${p.source}:${p.external_key}`} className="break-all rounded border border-slate-700 p-4">
      <p>{p.name} · {p.external_key}</p><p>核验时间：{p.as_of}</p><p>数据版本：{p.dataset_revision}</p>
      <a href={p.evidence_url} rel="noreferrer" target="_blank" className="text-sky-300">原始来源证据</a>
      <p className="text-sm text-slate-400">许可依据：{p.license_reference}</p>
    </li>)}</ul><Link className="mt-8 inline-block text-sky-300" href="/methodology">查看数据方法与限制 →</Link>
  </main>;
}
