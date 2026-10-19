import Link from 'next/link';
import { api } from '../lib/api';
import { exactAmount } from '../lib/market';
type RankData = { status: string; reason: string | null; source: string | null; metric_kind: string;
  currency: string | null; minor_unit_exponent: number | null;
  items: { item_id: string; name_zh: string | null; name_en: string; value: string; as_of: string;
    coverage: string; methodology: string; evidence_url: string }[] };
export default async function Rankings({ source }: { source?: string }) {
  const { data } = await api<RankData>(`/v1/rankings?${new URLSearchParams(source ? { source } : {})}`);
  return <section className="my-8 rounded-xl border border-slate-700 bg-slate-900 p-6"><h2 className="text-xl">近期有效样本排行</h2>
    <p className="my-3 text-sm text-slate-400">同一来源 · USD 每日成交中位价 · 最近 7 天各物品最新记录 · 基础物品，不混入不同变体</p>
    <form className="my-4 flex gap-3"><input aria-label="排行来源代码" name="source" defaultValue={source || ''} placeholder="输入已授权来源代码" /><button className="rounded bg-sky-700 px-4">查看排行</button></form>
    {!data ? <p>排行服务暂时不可用。</p> : data.items.length === 0 ? <p>{data.reason || '暂无可核实数据'}</p>
      : <ol className="space-y-4">{data.items.map((r, i) => <li key={r.item_id} className="border-t border-slate-700 pt-3">
        <Link className="text-sky-300" href={`/items/${r.item_id}`}>{i + 1}. {r.name_zh || r.name_en}</Link>
        <p>{exactAmount(r.value, data.minor_unit_exponent || 0)} {data.currency} · 来源 {data.source} · 截至 {r.as_of}</p>
        <p className="text-sm text-slate-400">{r.coverage} · {r.methodology}</p>
      </li>)}</ol>}
  </section>;
}
