import Link from 'next/link';
import { api, categories, type Catalog } from '../../lib/api';

export default async function Items({ searchParams }: {
  searchParams: Promise<{ query?: string; category?: string; cursor?: string }>;
}) {
  const { query = '', category = '', cursor = '' } = await searchParams;
  const params = new URLSearchParams({ query, limit: '20' });
  if (category) params.set('category', category);
  if (cursor) params.set('cursor', cursor);
  const { data, status } = await api<Catalog>(`/v1/items?${params}`);
  const next = new URLSearchParams(params);
  if (data?.next_cursor) next.set('cursor', data.next_cursor);
  return <main className="mx-auto max-w-5xl p-8">
    <Link href="/">← 返回首页</Link>
    <h1 className="my-6 text-3xl font-semibold">饰品目录</h1>
    <p className="mb-6 text-slate-400">来源 ID 匹配 · 中英文检索 · 未知交易属性保留未知</p>
    <form className="flex flex-wrap gap-3">
      <input name="query" defaultValue={query} placeholder="输入饰品名称" aria-label="搜索饰品" />
      <select name="category" defaultValue={category} aria-label="分类" className="rounded border border-slate-600 bg-slate-900 p-3">
        <option value="">全部分类</option>
        {Object.entries(categories).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select>
      <button className="rounded bg-sky-700 px-5 py-3" type="submit">搜索</button>
    </form>
    {!data ? <p role="status" className="mt-8 text-amber-300">{status === 422 ? '查询参数或分页已失效，请重新搜索。' : '目录服务暂时不可用，请稍后重试。'}</p>
      : data.items.length === 0 ? <p role="status" className="mt-8 text-slate-400">暂无可核实数据。尚未导入授权目录，或没有符合条件的饰品。</p>
      : <ul className="my-8 grid gap-4 md:grid-cols-2">{data.items.map(item => <li key={item.id} className="rounded-xl border border-slate-700 bg-slate-900 p-5">
        <Link href={`/items/${item.id}`} className="text-lg text-sky-300">{item.name_zh || item.name_en}</Link>
        <p>{item.name_en}</p><p className="text-sm text-slate-400">{categories[item.category] || item.category} · 更新 {item.updated_at}</p>
      </li>)}</ul>}
    {data?.next_cursor && <Link className="mt-6 inline-block text-sky-300" href={`/items?${next}`}>下一页 →</Link>}
    {cursor && <Link className="ml-5 text-sky-300" href={`/items?${new URLSearchParams({ query, category })}`}>返回第一页</Link>}
  </main>;
}
