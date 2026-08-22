import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface DailyCollectionPoint {
  date: string;
  cash: string;
  online: string;
  credit: string;
}

// Validated 3-slot categorical palette (see dataviz skill references/palette.md;
// validated all-pairs light+dark via scripts/validate_palette.js). Aqua (credit)
// has a contrast WARN vs the light surface — mitigated below with a legend,
// tooltip, and the "View as table" fallback rather than color alone.
const COLORS = {
  cash: "#2a78d6", // slot 1 — blue
  online: "#eb6834", // slot 2 — orange
  credit: "#1baf7a", // slot 3 — aqua
};
const AXIS_INK = "#898781";
const GRID_COLOR = "#e1e0d9";

function formatShortDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatCurrency(value: number) {
  return `₹${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

const LEGEND_LABELS: Record<string, string> = { cash: "Cash", online: "Online", credit: "Credit" };

export function CollectionsTrendChart({ data }: { data: DailyCollectionPoint[] }) {
  const chartData = data.map((d) => ({
    date: d.date,
    cash: Number(d.cash),
    online: Number(d.online),
    credit: Number(d.credit),
  }));

  return (
    <div>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }} barGap={2}>
            <CartesianGrid vertical={false} stroke={GRID_COLOR} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              tick={{ fontSize: 12, fill: AXIS_INK }}
              axisLine={{ stroke: GRID_COLOR }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => formatCurrency(v)}
              tick={{ fontSize: 12, fill: AXIS_INK }}
              axisLine={false}
              tickLine={false}
              width={64}
            />
            <Tooltip
              formatter={(value, name) => [formatCurrency(Number(value)), LEGEND_LABELS[String(name)] ?? String(name)]}
            />
            <Legend
              formatter={(value) => <span style={{ color: AXIS_INK }}>{LEGEND_LABELS[value] ?? value}</span>}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="cash" stackId="a" fill={COLORS.cash} maxBarSize={24} />
            <Bar dataKey="online" stackId="a" fill={COLORS.online} maxBarSize={24} />
            <Bar dataKey="credit" stackId="a" fill={COLORS.credit} maxBarSize={24} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-muted-foreground">View as table</summary>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="pr-4 font-normal">Date</th>
              <th className="pr-4 font-normal">Cash</th>
              <th className="pr-4 font-normal">Online</th>
              <th className="font-normal">Credit</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.date}>
                <td className="pr-4">{row.date}</td>
                <td className="pr-4">{row.cash}</td>
                <td className="pr-4">{row.online}</td>
                <td>{row.credit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
