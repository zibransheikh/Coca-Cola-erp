import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface StockRow {
  warehouse_name: string;
  sku: string;
  name: string;
  unit: string;
  quantity: string;
}
interface SalesByProductRow {
  sku: string;
  name: string;
  total_quantity: string;
  total_revenue: string;
}
interface SalesByCustomerRow {
  customer_name: string;
  invoice_count: number;
  total_amount: string;
}
interface CollectionsSummary {
  cash_total: string;
  online_total: string;
  credit_total: string;
  grand_total: string;
}
interface AgingRow {
  customer_name: string;
  credit_limit: string;
  current_0_30: string;
  days_31_60: string;
  days_61_90: string;
  over_90: string;
  total_outstanding: string;
  over_limit: boolean;
}
interface TripCreditRow {
  customer_name: string;
  amount: string;
  trip_date: string;
  driver_name: string;
}

export function ReportsPage() {
  const [stock, setStock] = useState<StockRow[]>([]);
  const [salesByProduct, setSalesByProduct] = useState<SalesByProductRow[]>([]);
  const [salesByCustomer, setSalesByCustomer] = useState<SalesByCustomerRow[]>([]);
  const [collections, setCollections] = useState<CollectionsSummary | null>(null);
  const [aging, setAging] = useState<AgingRow[]>([]);
  const [tripCredits, setTripCredits] = useState<TripCreditRow[]>([]);
  const [creditSearch, setCreditSearch] = useState("");

  const filteredCredits = useMemo(() => {
    const term = creditSearch.trim().toLowerCase();
    if (!term) return tripCredits;
    return tripCredits.filter((row) =>
      [row.customer_name, row.driver_name, row.trip_date].some((v) => v.toLowerCase().includes(term))
    );
  }, [tripCredits, creditSearch]);

  useEffect(() => {
    api.get<StockRow[]>("/reports/stock").then((r) => setStock(r.data));
    api.get<SalesByProductRow[]>("/reports/sales-by-product").then((r) => setSalesByProduct(r.data));
    api.get<SalesByCustomerRow[]>("/reports/sales-by-customer").then((r) => setSalesByCustomer(r.data));
    api.get<CollectionsSummary>("/reports/collections-summary").then((r) => setCollections(r.data));
    api.get<AgingRow[]>("/reports/customer-aging").then((r) => setAging(r.data));
    api.get<TripCreditRow[]>("/reports/trip-credits").then((r) => setTripCredits(r.data));
  }, []);

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Reports</h2>
      <Tabs defaultValue="stock">
        <TabsList>
          <TabsTrigger value="stock">Stock</TabsTrigger>
          <TabsTrigger value="sales-product">Sales by Product</TabsTrigger>
          <TabsTrigger value="sales-customer">Sales by Customer</TabsTrigger>
          <TabsTrigger value="collections">Collections</TabsTrigger>
          <TabsTrigger value="aging">Customer Aging</TabsTrigger>
          <TabsTrigger value="trip-credits">Current Credits</TabsTrigger>
        </TabsList>

        <TabsContent value="stock">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Warehouse Stock</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Warehouse</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead>Unit</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stock.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.warehouse_name}</TableCell>
                      <TableCell>{row.sku}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell>{row.unit}</TableCell>
                      <TableCell className="text-right">{row.quantity}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sales-product">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sales by Product</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead className="text-right">Quantity Sold</TableHead>
                    <TableHead className="text-right">Revenue</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {salesByProduct.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.sku}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell className="text-right">{row.total_quantity}</TableCell>
                      <TableCell className="text-right">{row.total_revenue}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sales-customer">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sales by Customer</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead className="text-right">Invoices</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {salesByCustomer.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.customer_name}</TableCell>
                      <TableCell className="text-right">{row.invoice_count}</TableCell>
                      <TableCell className="text-right">{row.total_amount}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="collections">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Collections Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {collections && (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Cash</p>
                    <p className="text-lg font-semibold">{collections.cash_total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Online</p>
                    <p className="text-lg font-semibold">{collections.online_total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Credit</p>
                    <p className="text-lg font-semibold">{collections.credit_total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Grand Total</p>
                    <p className="text-lg font-semibold">{collections.grand_total}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="aging">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Customer Credit Aging</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead className="text-right">0-30d</TableHead>
                    <TableHead className="text-right">31-60d</TableHead>
                    <TableHead className="text-right">61-90d</TableHead>
                    <TableHead className="text-right">90d+</TableHead>
                    <TableHead className="text-right">Total Outstanding</TableHead>
                    <TableHead className="text-right">Credit Limit</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {aging.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.customer_name}</TableCell>
                      <TableCell className="text-right">{row.current_0_30}</TableCell>
                      <TableCell className="text-right">{row.days_31_60}</TableCell>
                      <TableCell className="text-right">{row.days_61_90}</TableCell>
                      <TableCell className="text-right">{row.over_90}</TableCell>
                      <TableCell className="text-right font-medium">{row.total_outstanding}</TableCell>
                      <TableCell className="text-right">{row.credit_limit}</TableCell>
                      <TableCell>
                        {row.over_limit && <Badge variant="destructive">Over Limit</Badge>}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trip-credits">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Current Credits</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                placeholder="Search by shop, driver, or trip date..."
                value={creditSearch}
                onChange={(e) => setCreditSearch(e.target.value)}
                className="mb-4 max-w-sm"
              />
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Shop</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Trip Date</TableHead>
                    <TableHead>Driver</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCredits.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground">
                        {tripCredits.length === 0 ? "No credit given yet." : "No credits match your search."}
                      </TableCell>
                    </TableRow>
                  )}
                  {filteredCredits.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.customer_name}</TableCell>
                      <TableCell className="text-right">{row.amount}</TableCell>
                      <TableCell>{row.trip_date}</TableCell>
                      <TableCell>{row.driver_name}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
