import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface DailySalesPoint {
  date: string;
  total: string;
}

// Validated categorical/sequential palette (see dataviz skill references/palette.md).
const SALES_LINE_COLOR = "#2a78d6"; // sequential blue, light-mode step ~450
const AXIS_INK = "#898781"; // muted ink — text never wears the series color
const GRID_COLOR = "#e1e0d9"; // recessive hairline, solid (never dashed)

function formatShortDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatCurrency(value: number) {
  return `₹${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function SalesTrendChart({ data }: { data: DailySalesPoint[] }) {
  const chartData = data.map((d) => ({ ...d, total: Number(d.total) }));

  return (
    <div>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
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
              formatter={(value) => [formatCurrency(Number(value)), "Sales"]}
              labelFormatter={(label) => formatShortDate(String(label))}
              contentStyle={{ fontSize: 13 }}
            />
            <Line
              type="monotone"
              dataKey="total"
              stroke={SALES_LINE_COLOR}
              strokeWidth={2}
              dot={{ r: 3, fill: SALES_LINE_COLOR, strokeWidth: 0 }}
              activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-muted-foreground">View as table</summary>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="pr-4 font-normal">Date</th>
              <th className="font-normal">Sales</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.date}>
                <td className="pr-4">{row.date}</td>
                <td>{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
