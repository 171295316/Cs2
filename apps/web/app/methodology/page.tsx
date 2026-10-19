import Link from 'next/link';
import { api } from '../../lib/api';
import { definitions } from '../../lib/market';
export const revalidate = 15;
type Source = { code: string; name: string; license_status: string; redistribution_allowed: boolean | null; license_reference: string; updated_at: string; grants: { dataset: string; enabled: boolean; license_reference: string }[] };
export default async function Methodology() {
  const { data } = await api<{ items: Source[] }>('/v1/sources', true);
  return <main className="mx-auto max-w-4xl p-8"><Link href="/">← 返回首页</Link>
    <h1 className="my-6 text-3xl font-bold">数据来源与统计方法</h1>
    <section className="my-8"><h2 className="mb-4 text-xl text-sky-300">历史价格</h2>
      <p>从每件物品最早实际取得的记录开始；供应商整体归档起始日不代表每件物品都有同样长的历史。成交中位价、最低卖盘价、最高买盘价独立查询，不拼接不同来源和币种，也不从中位数编造开高低收。</p>
      <p className="mt-4">7D、30D、1Y 是所选结束时间之前的日历窗口；ALL 返回该口径全部实际记录。1h / 1d 选择原始粒度，不平均中位数；缺失区间不插值。数量和最小货币金额按整数保存，未知值不转为零。</p></section>
    <section className="my-8"><h2 className="mb-4 text-xl text-sky-300">供给不是个人 Steam 库存</h2><dl className="space-y-4">{Object.entries(definitions).map(([key, label]) => <div key={key}><dt className="font-bold">{label}</dt><dd className="text-slate-400">{key === 'estimated_total_units' ? '有模型和校准依据的估算，必须同时展示区间、覆盖和方法版本；不是直接观测。' : '只反映该来源能够观测的范围，不能称为全市场真实总存世量。'}</dd></div>)}</dl>
      <p className="mt-4">历史快照只对应当时实际记录，不反推缺失年份；来源或方法版本不同的快照不拼接。原始快照只画实际观测点，不假定采样每日连续。</p></section>
    <section className="my-8"><h2 className="mb-4 text-xl text-sky-300">排行规则</h2><p>只比较同来源、同币种、同口径和原始每日粒度的最新有效记录。默认最多 7 天，超过时效不参与。供给排行需固定方法版本；有区间的估算总量不做单值排名。不同磨损/StatTrak/纪念品变体不混入基础物品榜单。</p></section>
    <section className="my-8"><h2 className="mb-4 text-xl text-sky-300">来源与许可状态</h2>
      {!data ? <p>来源服务暂时不可用。</p> : data.items.length === 0 ? <p>暂无已登记来源。真实数据覆盖尚未建立，不展示虚构历史价格或存世量。</p>
        : <ul className="space-y-4">{data.items.map(s => <li key={s.code} className="break-words rounded border border-slate-700 p-4"><p>{s.name}（{s.code}）</p>
          <p>基础审批：{s.redistribution_allowed && s.license_status === 'approved' ? '已登记，行情/供给仍需专项许可' : '未批准'}</p><p>许可依据：{s.license_reference}</p><p>登记更新时间：{s.updated_at}</p><ul>{s.grants.map(g => <li key={g.dataset}>专项范围：{g.dataset === 'prices' ? '历史价格' : '供给快照'} · {g.enabled ? '已启用' : '已停用'} · 依据：{g.license_reference}</li>)}</ul></li>)}</ul>}
      <p className="mt-4 text-slate-400">ByMykel 仓库代码许可不能替代游戏资产/图片权利。cs2.sh 的普通条款限制将数据再次提供为 API，本网站未经专门许可不会启用。密钥仅保留在服务端。</p></section>
  </main>;
}
