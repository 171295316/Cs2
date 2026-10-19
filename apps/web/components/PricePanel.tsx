import { exactAmount } from '../lib/market';
import { api } from '../lib/api';
import HistoryChart from './HistoryChart';
export type MarketParams = Record<string, string | undefined>;
export type PricePoint = { as_of: string; minor_units: string; volume: string | null; evidence_url: string;
  coverage: string; methodology: string; source_record_key: string };
export type PriceData = { status: string; reason: string | null; source: string | null; currency: string;
  price_kind: string; resolution: string; minor_unit_exponent: number; earliest_available_at: string | null;
  latest_at: string | null; as_of: string | null; gaps: { from: string; to: string }[]; series: PricePoint[];
  options: { source: string; currency: string; price_kind: string; resolution: string }[] };
export default async function PricePanel({ id, params }: { id: string; params: MarketParams }) {
  const query = new URLSearchParams();
  for (const name of ['variant_id', 'source', 'currency', 'price_kind', 'resolution', 'range']) {
    if (params[name]) query.set(name, params[name]!);
  }
  const { data, status } = await api<PriceData>(`/v1/items/${encodeURIComponent(id)}/prices?${query}`);
  const kinds: Record<string, string> = { sale_median: '成交价中位数', ask_min: '最低卖盘价', bid_max: '最高买盘价' };
  const values = data?.series.map(p => BigInt(p.minor_units)) || [];
  const min = values.length ? values.reduce((a, b) => a < b ? a : b).toString() : null;
  const max = values.length ? values.reduce((a, b) => a > b ? a : b).toString() : null;
  return <section className="my-8 rounded-xl border border-slate-700 p-5">
    <h2 className="mb-4 text-xl">历史价格</h2>
    <form className="mb-5 flex flex-wrap gap-3">
      {params.variant_id && <input type="hidden" name="variant_id" value={params.variant_id} />}
      <label>来源<select name="source" defaultValue={params.source || data?.source || ''} aria-label="价格来源"><option value="">自动选择唯一来源</option>
        {[...new Set(data?.options.map(o => o.source))].map(s => <option key={s}>{s}</option>)}</select></label>
      <label>币种<select name="currency" defaultValue={params.currency || 'USD'}>{['USD','CNY','JPY','EUR','GBP'].map(c => <option key={c}>{c}</option>)}</select></label>
      <label>价格口径<select name="price_kind" defaultValue={params.price_kind || 'sale_median'}>{Object.entries(kinds).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      <label>时间范围<select name="range" defaultValue={params.range || 'ALL'}>{['7D','30D','1Y','ALL'].map(t => <option key={t}>{t}</option>)}</select></label>
      <label>记录粒度<select name="resolution" defaultValue={params.resolution || '1d'}><option value="1d">每日</option><option value="1h">每小时</option></select></label>
      <button className="rounded bg-sky-700 px-4" type="submit">更新价格</button>
    </form>
    {!data ? <p role="status">{status === 422 ? '查询参数无效，请重新选择。' : '价格服务暂时不可用。'}</p>
      : data.status !== 'ok' ? <p role="status">{data.reason || '暂无可核实数据'}</p>
      : <><p>来源：{data.source} · {kinds[data.price_kind]} · {data.currency} · {data.resolution}</p>
        <p className="my-2 text-sm text-slate-400">最早实际记录：{data.earliest_available_at} · 最新记录：{data.latest_at}</p>
        <p>所选区间最低：{exactAmount(min!, data.minor_unit_exponent)} · 最高：{exactAmount(max!, data.minor_unit_exponent)} {data.currency}</p>
        <HistoryChart points={data.series.map(p => ({ as_of: p.as_of, value: p.minor_units }))} exponent={data.minor_unit_exponent} cadence={data.resolution === '1h' ? 3600 : 86400} />
        {data.gaps.length > 0 && <p className="my-3 text-amber-300">存在 {data.gaps.length} 处记录缺口，图表不插值、不跨缺口连线。</p>}
        <details className="mt-4"><summary>原始记录、来源证据与方法（{data.series.length} 条）</summary>
          <div className="max-h-96 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>时间（UTC）</th><th>金额</th><th>覆盖与方法</th></tr></thead><tbody>
            {data.series.map(p => <tr key={p.source_record_key} className="border-t border-slate-700"><td>{p.as_of}</td><td>{exactAmount(p.minor_units, data.minor_unit_exponent)} {data.currency}</td>
              <td><a href={p.evidence_url} className="text-sky-300" rel="noreferrer" target="_blank">来源证据</a><p>{p.coverage}</p><p>{p.methodology}</p></td></tr>)}
          </tbody></table></div></details></>}
    <p className="mt-4 text-sm text-slate-400">仅展示有授权和原始时间记录的数据。不同来源、币种、成交/挂单价格分别查询；不将中位成交价编造成开高低收 K 线。</p>
  </section>;
}
