import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatTile } from "@/components/dashboard/StatTile";
import { SalesTrendChart } from "@/components/dashboard/SalesTrendChart";
import { CollectionsTrendChart } from "@/components/dashboard/CollectionsTrendChart";
import { RouteSalesTrendChart } from "@/components/dashboard/RouteSalesTrendChart";

interface BestSellingProduct {
  product_id: number;
  name: string;
  quantity: string;
}
interface DashboardSummary {
  today_sales: string;
  cash_collected_today: string;
  online_collected_today: string;
  pending_credits_total: string;
  vehicles_on_route: number;
  warehouse_stock_products: number;
  near_expiry_count: number;
  low_stock_count: number;
  daily_expenses: string;
  profit_today: string;
  best_selling_products: BestSellingProduct[];
}
interface DashboardTrends {
  daily_sales: { date: string; total: string }[];
  daily_collections: { date: string; cash: string; online: string; credit: string }[];
}
interface RouteSalesTrend {
  route_names: string[];
  points: Record<string, string | number>[];
}

function money(value: string) {
  return `₹${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

const PERIOD_OPTIONS = [
  { value: "week", label: "1 Week" },
  { value: "15d", label: "15 Days" },
  { value: "month", label: "1 Month" },
  { value: "year", label: "1 Year" },
  { value: "all", label: "All Time" },
];

export function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<DashboardTrends | null>(null);
  const [routeTrend, setRouteTrend] = useState<RouteSalesTrend | null>(null);
  const [period, setPeriod] = useState("15d");

  const periodLabel = PERIOD_OPTIONS.find((p) => p.value === period)?.label ?? "";

  useEffect(() => {
    api.get<DashboardSummary>("/dashboard/summary").then((r) => setSummary(r.data));
  }, []);

  useEffect(() => {
    api.get<DashboardTrends>("/dashboard/trends", { params: { period } }).then((r) => setTrends(r.data));
    api.get<RouteSalesTrend>("/dashboard/route-sales-trend", { params: { period } }).then((r) => setRouteTrend(r.data));
  }, [period]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Welcome, {user?.full_name}</h2>
          <p className="text-sm text-muted-foreground">Here's how today is looking.</p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((p) => (
              <SelectItem key={p.value} value={p.value}>
                {p.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <StatTile label="Today's Sales" value={money(summary.today_sales)} />
          <StatTile label="Cash Collected" value={money(summary.cash_collected_today)} />
          <StatTile label="Online Collected" value={money(summary.online_collected_today)} />
          <StatTile label="Pending Credits" value={money(summary.pending_credits_total)} />
          <StatTile label="Daily Expenses" value={money(summary.daily_expenses)} />
          <StatTile
            label="Profit Today"
            value={money(summary.profit_today)}
            hint="Sales − approved expenses (not full COGS)"
            tone={Number(summary.profit_today) >= 0 ? "good" : "bad"}
          />
          <StatTile label="Vehicles on Route" value={String(summary.vehicles_on_route)} />
          <StatTile label="Warehouse Stock" value={`${summary.warehouse_stock_products} products`} />
          <StatTile label="Near Expiry" value={String(summary.near_expiry_count)} hint="Batches expiring within 30 days" />
          <StatTile label="Low Stock" value={String(summary.low_stock_count)} hint="At or below reorder level" />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Sales — {periodLabel}</CardTitle>
          </CardHeader>
          <CardContent>{trends && <SalesTrendChart data={trends.daily_sales} />}</CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Best Selling (this month)</CardTitle>
          </CardHeader>
          <CardContent>
            {summary && summary.best_selling_products.length === 0 && (
              <p className="text-sm text-muted-foreground">No sales yet this month.</p>
            )}
            <ol className="flex flex-col gap-2">
              {summary?.best_selling_products.map((p, i) => (
                <li key={p.product_id} className="flex items-center justify-between text-sm">
                  <span>
                    <span className="text-muted-foreground">{i + 1}.</span> {p.name}
                  </span>
                  <span className="font-medium">{p.quantity}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Collections by Mode — {periodLabel}</CardTitle>
        </CardHeader>
        <CardContent>{trends && <CollectionsTrendChart data={trends.daily_collections} />}</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sales by Route — {periodLabel}</CardTitle>
        </CardHeader>
        <CardContent>{routeTrend && <RouteSalesTrendChart data={routeTrend} />}</CardContent>
      </Card>
    </div>
  );
}
