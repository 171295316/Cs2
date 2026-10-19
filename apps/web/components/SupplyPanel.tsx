import { api } from '../lib/api';
import type { MarketParams } from './PricePanel';
import HistoryChart from './HistoryChart';
export const definitions: Record<string, string> = {
  observed_distinct_instances: '已发现独立实例数', public_inventory_units: '公开库存可见样本',
  listed_units: '平台在售数量', estimated_total_units: '有依据的估算总量',
};
type Snapshot = { as_of: string; quantity: string; coverage: string; sampling_method: string;
  methodology_version: string; confidence_low: string | null; confidence_high: string | null;
  model_evidence_url: string | null; evidence_url: string; source_record_key: string };
export type SupplyData = { status: string; reason: string | null; source: string | null; metric_kind: string;
  metric_definition: string; as_of: string | null; earliest_available_at: string | null; methodology: string | null;
  series: Snapshot[]; options: { source: string; metric_type: string; methodology_version: string }[] };
export default async function SupplyPanel({ id, params }: { id: string; params: MarketParams }) {
  const query = new URLSearchParams();
  if (params.variant_id) query.set('variant_id', params.variant_id);
  if (params.supply_source) query.set('source', params.supply_source);
  if (params.metric_type) query.set('metric_type', params.metric_type);
  if (params.methodology_version) query.set('methodology_version', params.methodology_version);
  if (params.supply_range) query.set('range', params.supply_range);
  const { data } = await api<SupplyData>(`/v1/items/${encodeURIComponent(id)}/supply?${query}`);
  return <section className="my-8 rounded-xl border border-slate-700 p-5">
    <h2 className="mb-4 text-xl">市场供给 / 存世量</h2>
    <form className="mb-5 flex flex-wrap gap-3">
      {params.variant_id && <input type="hidden" name="variant_id" value={params.variant_id} />}
      <label>口径<select name="metric_type" defaultValue={params.metric_type || 'observed_distinct_instances'} aria-label="供给口径">
        {Object.entries(definitions).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>来源<select name="supply_source" defaultValue={params.supply_source || data?.source || ''}><option value="">自动选择唯一来源</option>
        {[...new Set(data?.options.map(o => o.source))].map(s => <option key={s}>{s}</option>)}</select></label>
      <label>方法版本<select name="methodology_version" defaultValue={params.methodology_version || data?.methodology || ''}><option value="">自动选择唯一方法</option>
        {[...new Set(data?.options.map(o => o.methodology_version))].map(s => <option key={s}>{s}</option>)}</select></label>
      <label>范围<select name="supply_range" defaultValue={params.supply_range || 'ALL'}>{['7D','30D','1Y','ALL'].map(s => <option key={s}>{s}</option>)}</select></label>
      <button className="rounded bg-sky-700 px-4" type="submit">更新供给</button>
    </form>
    {!data ? <p role="status">供给服务暂时不可用，请检查查询条件或稍后重试。</p> : data.status !== 'ok'
      ? <p role="status">{data.reason || '暂无可核实数据'}</p>
      : <><p>{data.metric_definition}</p><p className="my-3 text-sm text-slate-400">来源：{data.source} · 方法：{data.methodology} · 最早快照：{data.earliest_available_at} · 截至：{data.as_of}</p>
        <HistoryChart points={data.series.map(p => ({ as_of: p.as_of, value: p.quantity }))} connect={false} />
        <details><summary>实际快照与来源证明（{data.series.length} 条）</summary><div className="max-h-96 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>时间（UTC）</th><th>数量</th><th>方法与局限</th></tr></thead>
          <tbody>{data.series.map(p => <tr key={p.source_record_key} className="border-t border-slate-700"><td>{p.as_of}</td><td>{p.quantity}
            {p.confidence_low !== null && <p>估计区间：{p.confidence_low}–{p.confidence_high}</p>}</td><td><p>{p.coverage}</p><p>{p.sampling_method}</p>
            <a className="text-sky-300" href={p.evidence_url} rel="noreferrer" target="_blank">快照来源证明</a>
            {p.model_evidence_url && <a className="ml-4 text-sky-300" href={p.model_evidence_url} rel="noreferrer" target="_blank">模型校准依据</a>}</td></tr>)}</tbody></table></div></details></>}
    <p className="mt-4 text-sm text-amber-200">在售数量、公开样本、独立实例和估算总量是四种独立口径，均不代表个人 Steam 库存。原始快照只画实际观测点，不补造往年数据，也不假定缺失日数量相同。</p>
  </section>;
}
