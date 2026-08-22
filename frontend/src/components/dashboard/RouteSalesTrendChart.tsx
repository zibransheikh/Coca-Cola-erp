import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface RouteSalesTrend {
  route_names: string[];
  points: Record<string, string | number>[];
}

// Fixed-order 8-slot categorical palette (dataviz skill references/palette.md,
// validated for adjacent-pairlist use — lines/bars/stacks — in both modes).
// Routes are assigned slots in this exact order and never cycled; a 9th
// route folds into "Other" (gray, outside the validated set) rather than
// generating a new hue.
const ROUTE_COLORS = [
  "#2a78d6", // 1 blue
  "#eb6834", // 2 orange
  "#1baf7a", // 3 aqua
  "#eda100", // 4 yellow
  "#e87ba4", // 5 magenta
  "#008300", // 6 green
  "#4a3aa7", // 7 violet
  "#e34948", // 8 red
];
const OTHER_COLOR = "#8c8c8c";
const AXIS_INK = "#898781";
const GRID_COLOR = "#e1e0d9";

function formatShortDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatCurrency(value: number) {
  return `₹${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function colorFor(routeName: string, index: number) {
  return routeName === "Other" ? OTHER_COLOR : ROUTE_COLORS[index % ROUTE_COLORS.length];
}

export function RouteSalesTrendChart({ data }: { data: RouteSalesTrend }) {
  const { route_names, points } = data;

  if (route_names.length === 0) {
    return <p className="text-sm text-muted-foreground">No route sales in this period yet.</p>;
  }

  return (
    <div>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
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
              formatter={(value, name) => [formatCurrency(Number(value)), String(name)]}
              labelFormatter={(label) => formatShortDate(String(label))}
              contentStyle={{ fontSize: 13 }}
            />
            <Legend formatter={(value) => <span style={{ color: AXIS_INK }}>{value}</span>} iconType="circle" iconSize={8} />
            {route_names.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={colorFor(name, i)}
                strokeWidth={2}
                dot={{ r: 3, fill: colorFor(name, i), strokeWidth: 0 }}
                activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-muted-foreground">View as table</summary>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="pr-4 font-normal">Date</th>
              {route_names.map((name) => (
                <th key={name} className="pr-4 font-normal">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {points.map((row) => (
              <tr key={String(row.date)}>
                <td className="pr-4">{row.date}</td>
                {route_names.map((name) => (
                  <td key={name} className="pr-4">
                    {row[name]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
