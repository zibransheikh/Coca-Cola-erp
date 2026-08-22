import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Warehouse {
  id: number;
  name: string;
}

interface Product {
  id: number;
  sku: string;
  name: string;
  unit: string;
}

interface StockLevel {
  product_id: number;
  sku: string;
  name: string;
  unit: string;
  batch_id: number | null;
  batch_number: string | null;
  quantity: string;
  base_price: string;
}

interface PurchaseItemRow {
  product_id: string;
  quantity: string;
  unit_cost: string;
}

const emptyItem = (): PurchaseItemRow => ({ product_id: "", quantity: "", unit_cost: "" });

export function InventoryPage() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [warehouseId, setWarehouseId] = useState<string>("");
  const [stock, setStock] = useState<StockLevel[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [supplierName, setSupplierName] = useState("");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [items, setItems] = useState<PurchaseItemRow[]>([emptyItem()]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    listResource<Warehouse>("/warehouses").then((data) => {
      setWarehouses(data);
      if (data.length > 0) setWarehouseId(String(data[0].id));
    });
    listResource<Product>("/products").then(setProducts);
  }, []);

  async function refreshStock(whId: string) {
    if (!whId) return;
    const { data } = await api.get<StockLevel[]>(`/warehouses/${whId}/stock`);
    setStock(data);
  }

  useEffect(() => {
    refreshStock(warehouseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [warehouseId]);

  const filteredStock = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return stock;
    return stock.filter((row) =>
      [row.sku, row.name, row.batch_number ?? ""].some((v) => v.toLowerCase().includes(term))
    );
  }, [stock, search]);

  const totalStockValue = useMemo(
    () => stock.reduce((sum, row) => sum + Number(row.quantity) * Number(row.base_price), 0),
    [stock]
  );

  function openDialog() {
    setSupplierName("");
    setPurchaseDate("");
    setItems([emptyItem()]);
    setError(null);
    setDialogOpen(true);
  }

  function updateItem(index: number, field: keyof PurchaseItemRow, value: string) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/purchases", {
        warehouse_id: Number(warehouseId),
        supplier_name: supplierName,
        purchase_date: purchaseDate,
        items: items
          .filter((it) => it.product_id && it.quantity && it.unit_cost)
          .map((it) => ({
            product_id: Number(it.product_id),
            quantity: Number(it.quantity),
            unit_cost: Number(it.unit_cost),
          })),
      });
      setDialogOpen(false);
      await refreshStock(warehouseId);
    } catch {
      setError("Could not record purchase. Check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Inventory</h2>
        <Button onClick={openDialog}>Record Purchase</Button>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <Label>Warehouse</Label>
        <Select value={warehouseId} onValueChange={setWarehouseId}>
          <SelectTrigger className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {warehouses.map((w) => (
              <SelectItem key={w.id} value={String(w.id)}>
                {w.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Current Stock</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="Search by SKU, product, or batch..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-4 max-w-sm"
          />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Unit Price</TableHead>
                <TableHead className="text-right">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStock.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    {stock.length === 0 ? "No stock recorded yet." : "No stock matches your search."}
                  </TableCell>
                </TableRow>
              )}
              {filteredStock.map((row) => (
                <TableRow key={`${row.product_id}-${row.batch_id ?? "none"}`}>
                  <TableCell>{row.sku}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.unit}</TableCell>
                  <TableCell>{row.batch_number ?? "—"}</TableCell>
                  <TableCell className="text-right">{row.quantity}</TableCell>
                  <TableCell className="text-right">{Number(row.base_price).toFixed(2)}</TableCell>
                  <TableCell className="text-right">
                    {(Number(row.quantity) * Number(row.base_price)).toFixed(2)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="mt-4 flex items-center justify-end gap-2 border-t pt-4 text-sm">
            <span className="text-muted-foreground">Total Stock Value in Warehouse:</span>
            <span className="text-lg font-semibold">₹{totalStockValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
          </div>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Record Purchase</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="supplier">Supplier Name</Label>
              <Input id="supplier" required value={supplierName} onChange={(e) => setSupplierName(e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="purchase_date">Purchase Date</Label>
              <Input
                id="purchase_date"
                type="date"
                required
                value={purchaseDate}
                onChange={(e) => setPurchaseDate(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label>Items</Label>
              {items.map((item, index) => (
                <div key={index} className="flex gap-2">
                  <Select value={item.product_id} onValueChange={(v) => updateItem(index, "product_id", v)}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Product" />
                    </SelectTrigger>
                    <SelectContent>
                      {products.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    type="number"
                    placeholder="Qty"
                    className="w-24"
                    value={item.quantity}
                    onChange={(e) => updateItem(index, "quantity", e.target.value)}
                  />
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="Unit Cost"
                    className="w-28"
                    value={item.unit_cost}
                    onChange={(e) => updateItem(index, "unit_cost", e.target.value)}
                  />
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={() => setItems((prev) => [...prev, emptyItem()])}>
                Add Item
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Saving..." : "Save Purchase"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
