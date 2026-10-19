import Link from 'next/link';
import Rankings from '../components/Rankings';
import { categories } from '../lib/api';
export default async function Home({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const { source } = await searchParams;
  return <main className="mx-auto max-w-6xl p-6 md:p-12">
    <header className="mb-12 flex flex-wrap items-center justify-between gap-5"><strong className="text-2xl text-sky-300">CS2 Market</strong>
      <nav className="flex gap-5 text-sm"><Link href="/items">饰品目录</Link><Link href="/methodology">数据方法</Link></nav></header>
    <section className="mb-8"><p className="mb-4 text-sm tracking-widest text-sky-300">来源透明 · 口径独立 · 历史可追溯</p>
      <h1 className="mb-5 text-3xl font-bold md:text-5xl">CS2 饰品历史价格与存世量</h1>
      <p className="max-w-3xl text-slate-400">从每件物品最早可核实的记录开始，分别查看成交价格、挂单价格和市场供给。每个数字都有来源、日期与适用范围。</p></section>
    <form action="/items" className="mb-8 flex gap-3"><input className="min-w-0 flex-1" name="query" placeholder="搜索 AK-47、武器箱、贴纸、刀具…" aria-label="搜索饰品"/><button className="rounded bg-sky-700 px-6">搜索</button></form>
    <div className="flex flex-wrap gap-2">{Object.entries(categories).map(([key, label]) => <Link className="rounded-full border border-slate-700 px-4 py-2 text-sm hover:border-sky-400" key={key} href={`/items?category=${key}`}>{label}</Link>)}</div>
    <div className="my-8 grid gap-4 md:grid-cols-3">{[
      ['历史价格', '成交、卖盘、买盘独立查询；缺口不补价。'], ['可观察供给', '独立实例、公开样本、在售数量各自呈现。'], ['可核实依据', '来源、原始日期、覆盖与方法随记录展示。'],
    ].map(([title, text]) => <article key={title} className="rounded-xl border border-slate-700 p-5"><h2 className="mb-3 text-lg text-sky-200">{title}</h2><p className="text-sm text-slate-400">{text}</p></article>)}</div>
    <Rankings source={source} />
    <aside className="rounded-xl border border-slate-700 p-6"><h2 className="mb-2 text-xl">数据覆盖说明</h2>
      <p className="text-slate-400">默认未启用第三方数据源，不显示虚构报价或数量。只有授权数据导入后，目录与图表才会展示记录。没有数据不代表数量为零。</p>
      <Link className="mt-4 inline-block text-sky-300" href="/methodology">查看来源与统计方法 →</Link></aside>
  </main>;
}
