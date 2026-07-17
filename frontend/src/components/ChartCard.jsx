import { useEffect, useRef } from "react";

// Zero third-party: hand-rolled Canvas 2D charts (line / bar / stacked-bar /
// donut) replacing recharts. Supports click-to-navigate via onSliceClick.
const PALETTE = ["#3aa0ff", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#22d3ee"];

export default function ChartCard({ title, subtitle, type, data, xKey, series, onSliceClick, height = 220 }) {
  const canvasRef = useRef(null);
  const regionsRef = useRef([]);

  useEffect(() => {
    draw();
    const onResize = () => draw();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, type]);

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 320;
    canvas.width = w * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, height);
    regionsRef.current = [];

    const styles = getComputedStyle(document.documentElement);
    const textColor = (styles.getPropertyValue("--text-soft") || "#9aa8c2").trim() || "#9aa8c2";
    const gridColor = (styles.getPropertyValue("--border") || "#24314a").trim() || "#24314a";

    if (!data || data.length === 0) {
      ctx.fillStyle = textColor;
      ctx.font = "13px sans-serif";
      ctx.fillText("No data for this filter", 12, height / 2);
      return;
    }

    if (type === "donut") drawDonut(ctx, w, height, textColor);
    else drawXY(ctx, w, height, textColor, gridColor);
  }

  function drawXY(ctx, w, h, textColor, gridColor) {
    const padding = { top: 10, right: 10, bottom: 24, left: 34 };
    const plotW = w - padding.left - padding.right;
    const plotH = h - padding.top - padding.bottom;

    const stackedTotals = type === "stacked-bar"
      ? data.map((d) => series.reduce((sum, s) => sum + (Number(d[s.key]) || 0), 0))
      : [];
    const allValues = data.flatMap((d) => series.map((s) => Number(d[s.key]) || 0));
    const maxVal = Math.max(1, type === "stacked-bar" ? Math.max(...stackedTotals, 1) : Math.max(...allValues, 1));

    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    ctx.font = "10px ui-monospace, Menlo, Consolas, monospace";
    ctx.fillStyle = textColor;
    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {
      const y = padding.top + plotH - (plotH * i) / ySteps;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
      ctx.fillText(String(Math.round((maxVal * i) / ySteps)), 2, y + 3);
    }

    const n = data.length;
    const slotW = plotW / n;

    if (type === "line") {
      series.forEach((s, si) => {
        const color = s.color || PALETTE[si % PALETTE.length];
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        data.forEach((d, i) => {
          const x = padding.left + slotW * i + slotW / 2;
          const y = padding.top + plotH - (Number(d[s.key]) / maxVal) * plotH;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
        data.forEach((d, i) => {
          const x = padding.left + slotW * i + slotW / 2;
          const y = padding.top + plotH - (Number(d[s.key]) / maxVal) * plotH;
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          regionsRef.current.push({ x: x - 7, y: y - 7, w: 14, h: 14, index: i, seriesKey: s.key });
        });
      });
    } else if (type === "bar") {
      const groupW = slotW * 0.7;
      const barW = groupW / series.length;
      data.forEach((d, i) => {
        series.forEach((s, si) => {
          const val = Number(d[s.key]) || 0;
          const barH = (val / maxVal) * plotH;
          const x = padding.left + slotW * i + (slotW - groupW) / 2 + barW * si;
          const y = padding.top + plotH - barH;
          ctx.fillStyle = s.color || PALETTE[si % PALETTE.length];
          ctx.fillRect(x, y, Math.max(1, barW - 2), barH);
          regionsRef.current.push({ x, y, w: Math.max(1, barW - 2), h: barH, index: i, seriesKey: s.key });
        });
      });
    } else if (type === "stacked-bar") {
      data.forEach((d, i) => {
        let yOffset = 0;
        series.forEach((s, si) => {
          const val = Number(d[s.key]) || 0;
          const barH = (val / maxVal) * plotH;
          const x = padding.left + slotW * i + slotW * 0.2;
          const y = padding.top + plotH - yOffset - barH;
          ctx.fillStyle = s.color || PALETTE[si % PALETTE.length];
          ctx.fillRect(x, y, slotW * 0.6, barH);
          regionsRef.current.push({ x, y, w: slotW * 0.6, h: barH, index: i, seriesKey: s.key });
          yOffset += barH;
        });
      });
    }

    ctx.fillStyle = textColor;
    ctx.font = "10px ui-monospace, Menlo, Consolas, monospace";
    ctx.textAlign = "center";
    data.forEach((d, i) => {
      const x = padding.left + slotW * i + slotW / 2;
      ctx.fillText(String(d[xKey] ?? "").slice(0, 8), x, h - 6);
    });
    ctx.textAlign = "left";
  }

  function drawDonut(ctx, w, h, textColor) {
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) / 2 - 10;
    const innerRadius = radius * 0.6;
    const total = data.reduce((sum, d) => sum + (Number(d.value) || 0), 0) || 1;
    let angle = -Math.PI / 2;

    data.forEach((d, i) => {
      const slice = (Number(d.value) / total) * Math.PI * 2;
      const color = d.color || PALETTE[i % PALETTE.length];
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, angle, angle + slice);
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
      regionsRef.current.push({
        donut: true, cx, cy, radius, innerRadius, startAngle: angle, endAngle: angle + slice, index: i,
      });
      angle += slice;
    });

    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(cx, cy, innerRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";

    ctx.fillStyle = textColor;
    ctx.font = "13px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(String(total), cx, cy + 4);
    ctx.textAlign = "left";
  }

  function handleClick(e) {
    if (!onSliceClick) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    for (const region of regionsRef.current) {
      if (region.donut) {
        const dx = x - region.cx;
        const dy = y - region.cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist >= region.innerRadius && dist <= region.radius) {
          let a = Math.atan2(dy, dx);
          if (a < region.startAngle) a += Math.PI * 2;
          if (a >= region.startAngle && a <= region.endAngle) {
            onSliceClick(data[region.index], region.index);
            return;
          }
        }
      } else if (x >= region.x && x <= region.x + region.w && y >= region.y && y <= region.y + region.h) {
        onSliceClick(data[region.index], region.index, region.seriesKey);
        return;
      }
    }
  }

  return (
    <div className="chart-card">
      <h3>{title}</h3>
      {subtitle && <p className="chart-subtitle">{subtitle}</p>}
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: `${height}px`, cursor: onSliceClick ? "pointer" : "default" }}
        onClick={handleClick}
      />
      {series && series.length > 1 && (
        <div className="chart-legend">
          {series.map((s, i) => (
            <span key={s.key} className="chart-legend-item">
              <span className="chart-legend-swatch" style={{ background: s.color || PALETTE[i % PALETTE.length] }} />
              {s.label || s.key}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
