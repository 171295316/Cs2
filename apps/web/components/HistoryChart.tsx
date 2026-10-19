'use client';
import { useEffect, useRef } from 'react';
import { createChart, ColorType, LineSeries, type UTCTimestamp, type LineData, type WhitespaceData } from 'lightweight-charts';

export type ChartPoint = { as_of: string; value: string };
export default function HistoryChart({ points, exponent = 0, cadence = 86400, connect = true }: {
  points: ChartPoint[]; exponent?: number; cadence?: number; connect?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  // 图表使用秒级时间轴；不能把同一秒内的两条真实记录压成重复时间点。
  const times = points.map(p => Math.floor(Date.parse(p.as_of) / 1000));
  const timeSafe = times.every((t, i) => Number.isFinite(t) && (!i || t > times[i - 1]));
  const safe = points.every(p => Number.isSafeInteger(Number(p.value)));
  useEffect(() => {
    if (!host.current || !safe || !timeSafe || !points.length) return;
    const chart = createChart(host.current, { height: 300, autoSize: true,
      layout: { background: { type: ColorType.Solid, color: '#0f172a' }, textColor: '#cbd5e1', attributionLogo: true },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      timeScale: { timeVisible: cadence < 86400 },
    });
    const series = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2, lineVisible: connect, pointMarkersVisible: true,
      priceFormat: { type: 'price', precision: exponent, minMove: 1 / 10 ** exponent } });
    const data: (LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp>)[] = [];
    points.forEach((p, index) => {
      const seconds = Math.floor(Date.parse(p.as_of) / 1000);
      if (connect && index && seconds - Math.floor(Date.parse(points[index - 1].as_of) / 1000) > cadence) {
        // Separate line segments: one whitespace point alone can still be bridged by some chart modes.
        const previousSegment = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2,
          lastValueVisible: false, priceLineVisible: false, pointMarkersVisible: true,
          priceFormat: { type: 'price', precision: exponent, minMove: 1 / 10 ** exponent } });
        previousSegment.setData(data.splice(0));
      }
      data.push({ time: seconds as UTCTimestamp, value: Number(p.value) / 10 ** exponent });
    });
    series.setData(data);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [points, exponent, cadence, safe, timeSafe, connect]);
  if (!safe) return <p>数值超过图表安全精度，请查看下方原始记录。</p>;
  if (!timeSafe) return <p>记录时间超出图表秒级精度，请查看下方原始记录。</p>;
  return <div className="min-w-0 max-w-full overflow-hidden"><div className="w-full min-w-0 max-w-full overflow-hidden" ref={host} role="img" aria-label="仅由可核实记录绘制的历史趋势，缺口不连线" />
    <a className="text-xs text-slate-400" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">图表由 TradingView Lightweight Charts 提供</a></div>;
}
