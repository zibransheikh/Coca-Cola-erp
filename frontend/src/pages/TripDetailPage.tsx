import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Trip {
  id: number;
  vehicle_id: number;
  driver_id: number;
  route_id: number | null;
  warehouse_id: number;
  trip_date: string;
  status: string;
  mismatch_notes: string | null;
  cash_count_500: number;
  cash_count_200: number;
  cash_count_100: number;
  cash_count_50: number;
  cash_count_20: number;
  cash_count_10: number;
  cash_coins_amount: string;
}
interface Crates {
  crates_out: string;
  crates_in: number;
}
interface StockSheetRow {
  product_id: number;
  sku: string;
  name: string;
  unit: string;
  base_price: string;
  warehouse_available: string;
  loaded_quantity: string;
  returned_quantity: string;
  damaged_quantity: string;
}
interface Customer {
  id: number;
  name: string;
}
interface MoneyEntry {
  id: number;
  trip_id: number | null;
  customer_id: number;
  amount: string;
  status: string;
  collected_at: string;
}
interface ChequeEntry extends MoneyEntry {
  cheque_given_date: string | null;
  cheque_deposit_date: string | null;
}
interface Reconciliation {
  products: { product_id: number; sku: string; name: string; loaded: string; returned: string; damaged: string; expected_value: string }[];
  expected_sales_value: string;
  cash_collected: string;
  online_collected: string;
  credit_given: string;
  cheque_given: string;
  total_collected: string;
  money_difference: string;
  clean: boolean;
}

interface EditRow {
  loaded: string;
  returned: string;
  damaged: string;
}

const NEW_SHOP_VALUE = "__new__";

const DENOMINATIONS: { key: keyof CashForm; label: string; value: number }[] = [
  { key: "cash_count_500", label: "₹500", value: 500 },
  { key: "cash_count_200", label: "₹200", value: 200 },
  { key: "cash_count_100", label: "₹100", value: 100 },
  { key: "cash_count_50", label: "₹50", value: 50 },
  { key: "cash_count_20", label: "₹20", value: 20 },
  { key: "cash_count_10", label: "₹10", value: 10 },
];

interface CashForm {
  cash_count_500: string;
  cash_count_200: string;
  cash_count_100: string;
  cash_count_50: string;
  cash_count_20: string;
  cash_count_10: string;
  cash_coins_amount: string;
}

const EMPTY_CASH_FORM: CashForm = {
  cash_count_500: "0",
  cash_count_200: "0",
  cash_count_100: "0",
  cash_count_50: "0",
  cash_count_20: "0",
  cash_count_10: "0",
  cash_coins_amount: "0",
};

function statusLabel(status: string) {
  if (status === "awaiting_bank_verification") return "Awaiting Bank Verification";
  if (status === "pending") return "Pending";
  return "Paid";
}

function isPaid(status: string) {
  return status === "cleared";
}

const PAID_BADGE_CLASS = "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300";
const UNPAID_BADGE_CLASS = "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300";

function MoneyStatusBadge({ status }: { status: string }) {
  return <Badge className={isPaid(status) ? PAID_BADGE_CLASS : UNPAID_BADGE_CLASS}>{statusLabel(status)}</Badge>;
}

export function TripDetailPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  const [trip, setTrip] = useState<Trip | null>(null);
  const [sheet, setSheet] = useState<StockSheetRow[]>([]);
  const [editRows, setEditRows] = useState<Record<number, EditRow>>({});
  const [sheetError, setSheetError] = useState<string | null>(null);
  const [sheetSaving, setSheetSaving] = useState(false);
  const [sheetSearch, setSheetSearch] = useState("");
  const filteredSheet = useMemo(() => {
    const term = sheetSearch.trim().toLowerCase();
    if (!term) return sheet;
    return sheet.filter((row) => [row.sku, row.name].some((v) => v.toLowerCase().includes(term)));
  }, [sheet, sheetSearch]);

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [reconciliation, setReconciliation] = useState<Reconciliation | null>(null);

  const [cashForm, setCashForm] = useState<CashForm>(EMPTY_CASH_FORM);
  const [cashSaving, setCashSaving] = useState(false);

  const [creditEntries, setCreditEntries] = useState<MoneyEntry[]>([]);
  const [newCreditCustomer, setNewCreditCustomer] = useState("");
  const [newCreditAmount, setNewCreditAmount] = useState("");

  const [onlineEntries, setOnlineEntries] = useState<MoneyEntry[]>([]);
  const [newOnlineCustomer, setNewOnlineCustomer] = useState("");
  const [newOnlineAmount, setNewOnlineAmount] = useState("");

  const [chequeEntries, setChequeEntries] = useState<ChequeEntry[]>([]);
  const [newChequeCustomer, setNewChequeCustomer] = useState("");
  const [newChequeAmount, setNewChequeAmount] = useState("");
  const [newChequeGivenDate, setNewChequeGivenDate] = useState("");
  const [newChequeDepositDate, setNewChequeDepositDate] = useState("");

  const [crates, setCrates] = useState<Crates>({ crates_out: "0", crates_in: 0 });
  const [cratesInInput, setCratesInInput] = useState("0");
  const [cratesSaving, setCratesSaving] = useState(false);

  const [shopDialogTarget, setShopDialogTarget] = useState<"credit" | "online" | "cheque" | null>(null);
  const [newShopForm, setNewShopForm] = useState({ name: "", owner_name: "", phone: "" });
  const [shopDialogError, setShopDialogError] = useState<string | null>(null);
  const [shopDialogSaving, setShopDialogSaving] = useState(false);

  const [overrideNotes, setOverrideNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [closeConfirmOpen, setCloseConfirmOpen] = useState(false);

  function syncEditRows(rows: StockSheetRow[]) {
    const next: Record<number, EditRow> = {};
    for (const row of rows) {
      next[row.product_id] = {
        loaded: row.loaded_quantity,
        returned: row.returned_quantity,
        damaged: row.damaged_quantity,
      };
    }
    setEditRows(next);
  }

  function syncCashForm(t: Trip) {
    setCashForm({
      cash_count_500: String(t.cash_count_500),
      cash_count_200: String(t.cash_count_200),
      cash_count_100: String(t.cash_count_100),
      cash_count_50: String(t.cash_count_50),
      cash_count_20: String(t.cash_count_20),
      cash_count_10: String(t.cash_count_10),
      cash_coins_amount: t.cash_coins_amount,
    });
  }

  async function refreshAll() {
    const [tripData, sheetData, reconData, creditData, onlineData, chequeData, cratesData] = await Promise.all([
      api.get<Trip>(`/trips/${tripId}`).then((r) => r.data),
      api.get<StockSheetRow[]>(`/trips/${tripId}/stock-sheet`).then((r) => r.data),
      api.get<Reconciliation>(`/trips/${tripId}/reconciliation`).then((r) => r.data),
      api.get<MoneyEntry[]>(`/trips/${tripId}/credit-entries`).then((r) => r.data),
      api.get<MoneyEntry[]>(`/trips/${tripId}/online-entries`).then((r) => r.data),
      api.get<ChequeEntry[]>(`/trips/${tripId}/cheque-entries`).then((r) => r.data),
      api.get<Crates>(`/trips/${tripId}/crates`).then((r) => r.data),
    ]);
    setTrip(tripData);
    syncCashForm(tripData);
    setSheet(sheetData);
    syncEditRows(sheetData);
    setReconciliation(reconData);
    setCreditEntries(creditData);
    setOnlineEntries(onlineData);
    setChequeEntries(chequeData);
    setCrates(cratesData);
    setCratesInInput(String(cratesData.crates_in));
  }

  async function refreshCustomers() {
    return listResource<Customer>("/customers").then(setCustomers);
  }

  useEffect(() => {
    refreshAll();
    refreshCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId]);

  function updateEditRow(productId: number, field: keyof EditRow, value: string) {
    setEditRows((prev) => ({ ...prev, [productId]: { ...prev[productId], [field]: value } }));
  }

  async function handleSaveSheet() {
    setSheetError(null);
    setSheetSaving(true);
    try {
      await api.put(`/trips/${tripId}/stock-sheet`, {
        rows: sheet.map((row) => ({
          product_id: row.product_id,
          loaded_quantity: Number(editRows[row.product_id]?.loaded || 0),
          returned_quantity: Number(editRows[row.product_id]?.returned || 0),
          damaged_quantity: Number(editRows[row.product_id]?.damaged || 0),
        })),
      });
      await refreshAll();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSheetError(detail || "Could not save — check quantities (e.g. loaded can't go below returned+damaged).");
    } finally {
      setSheetSaving(false);
    }
  }

  const cashTotal = DENOMINATIONS.reduce((sum, d) => sum + Number(cashForm[d.key] || 0) * d.value, 0) + Number(cashForm.cash_coins_amount || 0);

  async function handleSaveCash() {
    setActionError(null);
    setCashSaving(true);
    try {
      await api.put(`/trips/${tripId}/cash-count`, {
        cash_count_500: Number(cashForm.cash_count_500 || 0),
        cash_count_200: Number(cashForm.cash_count_200 || 0),
        cash_count_100: Number(cashForm.cash_count_100 || 0),
        cash_count_50: Number(cashForm.cash_count_50 || 0),
        cash_count_20: Number(cashForm.cash_count_20 || 0),
        cash_count_10: Number(cashForm.cash_count_10 || 0),
        cash_coins_amount: Number(cashForm.cash_coins_amount || 0),
      });
      await refreshAll();
    } catch {
      setActionError("Could not save cash count.");
    } finally {
      setCashSaving(false);
    }
  }

  async function handleSaveCrates() {
    setActionError(null);
    setCratesSaving(true);
    try {
      await api.put(`/trips/${tripId}/crates`, {
        crates_in: Number(cratesInInput || 0),
      });
      await refreshAll();
    } catch {
      setActionError("Could not save crate count.");
    } finally {
      setCratesSaving(false);
    }
  }

  async function handleAddMoneyEntry(kind: "credit" | "online", customerId: string, amount: string) {
    if (!customerId || !amount) return;
    setActionError(null);
    try {
      await api.post(`/trips/${tripId}/${kind}-entries`, {
        customer_id: Number(customerId),
        amount: Number(amount),
      });
      if (kind === "credit") {
        setNewCreditCustomer("");
        setNewCreditAmount("");
      } else {
        setNewOnlineCustomer("");
        setNewOnlineAmount("");
      }
      await refreshAll();
    } catch {
      setActionError(kind === "credit" ? "Could not add credit entry." : "Could not add online payment.");
    }
  }

  async function handleAddChequeEntry(e: React.FormEvent) {
    e.preventDefault();
    if (!newChequeCustomer || !newChequeAmount || !newChequeGivenDate || !newChequeDepositDate) return;
    setActionError(null);
    try {
      await api.post(`/trips/${tripId}/cheque-entries`, {
        customer_id: Number(newChequeCustomer),
        amount: Number(newChequeAmount),
        cheque_given_date: newChequeGivenDate,
        cheque_deposit_date: newChequeDepositDate,
      });
      setNewChequeCustomer("");
      setNewChequeAmount("");
      setNewChequeGivenDate("");
      setNewChequeDepositDate("");
      await refreshAll();
    } catch {
      setActionError("Could not add cheque entry.");
    }
  }

  async function handleDeleteMoneyEntry(kind: "credit" | "online" | "cheque", entryId: number) {
    setActionError(null);
    try {
      await api.delete(`/trips/${tripId}/${kind}-entries/${entryId}`);
      await refreshAll();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(detail || "Could not remove entry.");
    }
  }

  async function handleToggleMoneyEntryStatus(kind: "credit" | "online" | "cheque", entryId: number, paid: boolean) {
    setActionError(null);
    try {
      await api.patch(`/trips/${tripId}/${kind}-entries/${entryId}`, { paid });
      await refreshAll();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(detail || "Could not update status.");
    }
  }

  function openNewShopDialog(target: "credit" | "online" | "cheque") {
    setShopDialogTarget(target);
    setNewShopForm({ name: "", owner_name: "", phone: "" });
    setShopDialogError(null);
  }

  async function handleCreateShop(e: React.FormEvent) {
    e.preventDefault();
    if (!newShopForm.name.trim()) return;
    setShopDialogError(null);
    setShopDialogSaving(true);
    try {
      const { data } = await api.post("/customers", {
        name: newShopForm.name,
        owner_name: newShopForm.owner_name || null,
        phone: newShopForm.phone || null,
      });
      await refreshCustomers();
      if (shopDialogTarget === "credit") setNewCreditCustomer(String(data.id));
      else if (shopDialogTarget === "online") setNewOnlineCustomer(String(data.id));
      else if (shopDialogTarget === "cheque") setNewChequeCustomer(String(data.id));
      setShopDialogTarget(null);
    } catch {
      setShopDialogError("Could not create shop — check the name and try again.");
    } finally {
      setShopDialogSaving(false);
    }
  }

  async function handleClose(notesOverride?: string) {
    setActionError(null);
    try {
      await api.post(`/trips/${tripId}/close`, { override_notes: notesOverride ?? overrideNotes ?? null });
      setCloseConfirmOpen(false);
      await refreshAll();
    } catch {
      setActionError("Could not close trip.");
    }
  }

  function handleCloseClick() {
    if (isClean) {
      handleClose();
    } else {
      setCloseConfirmOpen(true);
    }
  }

  function handleConfirmCloseMismatch() {
    const notes = overrideNotes.trim() || `Closed with a mismatch of ${reconciliation?.money_difference ?? "?"} — confirmed by user`;
    handleClose(notes);
  }

  if (!trip) return <p className="text-muted-foreground">Loading…</p>;

  const isClosed = trip.status === "closed";
  const isClean = reconciliation ? reconciliation.clean : false;

  function ShopSelect({
    value,
    onChange,
    target,
  }: {
    value: string;
    onChange: (v: string) => void;
    target: "credit" | "online" | "cheque";
  }) {
    return (
      <Select
        value={value}
        onValueChange={(v) => {
          if (v === NEW_SHOP_VALUE) openNewShopDialog(target);
          else onChange(v);
        }}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Customer / shop" />
        </SelectTrigger>
        <SelectContent>
          {customers.map((c) => (
            <SelectItem key={c.id} value={String(c.id)}>
              {c.name}
            </SelectItem>
          ))}
          <SelectSeparator />
          <SelectItem value={NEW_SHOP_VALUE}>+ Add new shop</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  const moneyEntryRows = [
    ...creditEntries.map((c) => ({ ...c, mode: "Credit" })),
    ...onlineEntries.map((o) => ({ ...o, mode: "Online" })),
    ...chequeEntries.map((c) => ({ ...c, mode: "Cheque" })),
  ];

  const cratesSold = Number(crates.crates_out || 0) - Number(cratesInInput || 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="outline" size="sm" className="mb-2" onClick={() => navigate("/trips")}>
            ← Back to Trips
          </Button>
          <h2 className="text-xl font-semibold">Trip #{trip.id}</h2>
          <p className="text-sm text-muted-foreground">{trip.trip_date}</p>
        </div>
        <Badge
          className={isClosed ? "bg-secondary text-secondary-foreground" : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"}
        >
          {isClosed ? "Closed" : "Open"}
        </Badge>
      </div>

      {actionError && <p className="text-sm text-destructive">{actionError}</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stock Sheet</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="Search products by name or SKU..."
            value={sheetSearch}
            onChange={(e) => setSheetSearch(e.target.value)}
            className="mb-4 max-w-sm"
          />
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead className="text-right">Warehouse Available</TableHead>
                  <TableHead className="text-right">Loaded</TableHead>
                  <TableHead className="text-right">Returned</TableHead>
                  <TableHead className="text-right">Damaged</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSheet.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No products match your search.
                    </TableCell>
                  </TableRow>
                )}
                {filteredSheet.map((row) => (
                  <TableRow key={row.product_id}>
                    <TableCell>
                      {row.name} <span className="text-muted-foreground">({row.unit})</span>
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">{row.warehouse_available}</TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        disabled={isClosed}
                        className="w-24 ml-auto text-right"
                        value={editRows[row.product_id]?.loaded ?? ""}
                        onChange={(e) => updateEditRow(row.product_id, "loaded", e.target.value)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        disabled={isClosed}
                        className="w-24 ml-auto text-right"
                        value={editRows[row.product_id]?.returned ?? ""}
                        onChange={(e) => updateEditRow(row.product_id, "returned", e.target.value)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        disabled={isClosed}
                        className="w-24 ml-auto text-right"
                        value={editRows[row.product_id]?.damaged ?? ""}
                        onChange={(e) => updateEditRow(row.product_id, "damaged", e.target.value)}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {sheetError && <p className="mt-3 text-sm text-destructive">{sheetError}</p>}
          {!isClosed && (
            <Button className="mt-4" onClick={handleSaveSheet} disabled={sheetSaving}>
              {sheetSaving ? "Saving..." : "Save Stock Sheet"}
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cash Count</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-7">
            {DENOMINATIONS.map((d) => (
              <div key={d.key} className="flex flex-col gap-1">
                <Label className="text-xs text-muted-foreground">{d.label} notes</Label>
                <Input
                  type="number"
                  disabled={isClosed}
                  value={cashForm[d.key]}
                  onChange={(e) => setCashForm((prev) => ({ ...prev, [d.key]: e.target.value }))}
                />
              </div>
            ))}
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Coins (₹)</Label>
              <Input
                type="number"
                step="0.01"
                disabled={isClosed}
                value={cashForm.cash_coins_amount}
                onChange={(e) => setCashForm((prev) => ({ ...prev, cash_coins_amount: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Cash Total:</span>
            <span className="text-lg font-semibold">₹{cashTotal.toFixed(2)}</span>
          </div>
          {!isClosed && (
            <Button className="self-start" onClick={handleSaveCash} disabled={cashSaving}>
              {cashSaving ? "Saving..." : "Save Cash Count"}
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Crates (Empties)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 sm:w-96">
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Crates Out (from Stock Sheet)</Label>
              <Input type="number" disabled value={crates.crates_out} className="bg-muted" />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Crates In (empty)</Label>
              <Input
                type="number"
                disabled={isClosed}
                value={cratesInInput}
                onChange={(e) => setCratesInInput(e.target.value)}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Crates Out is the total Loaded quantity across all "crate" unit products on the Stock Sheet above —
            it updates automatically when the stock sheet is saved.
          </p>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Crates Sold (Out − In):</span>
            <span className="text-lg font-semibold">{cratesSold}</span>
          </div>
          {!isClosed && (
            <Button className="self-start" onClick={handleSaveCrates} disabled={cratesSaving}>
              {cratesSaving ? "Saving..." : "Save Crates"}
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Credit Given</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {creditEntries.length === 0 && <p className="text-sm text-muted-foreground">No credit given on this trip yet.</p>}
          {creditEntries.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Shop</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  {!isClosed && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {creditEntries.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>{customers.find((cu) => cu.id === c.customer_id)?.name ?? "Customer"}</TableCell>
                    <TableCell className="text-right">{c.amount}</TableCell>
                    <TableCell>
                      <MoneyStatusBadge status={c.status} />
                    </TableCell>
                    {!isClosed && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleMoneyEntryStatus("credit", c.id, !isPaid(c.status))}
                          >
                            {isPaid(c.status) ? "Mark Pending" : "Mark Paid"}
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleDeleteMoneyEntry("credit", c.id)}>
                            Remove
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Total Credit Given:</span>
            <span className="font-semibold">{reconciliation?.credit_given ?? "0"}</span>
          </div>
          {!isClosed && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAddMoneyEntry("credit", newCreditCustomer, newCreditAmount);
              }}
              className="flex items-end gap-2"
            >
              <div className="flex flex-1 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Shop</Label>
                <ShopSelect value={newCreditCustomer} onChange={setNewCreditCustomer} target="credit" />
              </div>
              <div className="flex w-40 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newCreditAmount}
                  onChange={(e) => setNewCreditAmount(e.target.value)}
                />
              </div>
              <Button type="submit">Add Credit</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Online Payments</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {onlineEntries.length === 0 && <p className="text-sm text-muted-foreground">No online payments recorded on this trip yet.</p>}
          {onlineEntries.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Shop</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  {!isClosed && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {onlineEntries.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell>{customers.find((cu) => cu.id === o.customer_id)?.name ?? "Customer"}</TableCell>
                    <TableCell className="text-right">{o.amount}</TableCell>
                    <TableCell>
                      <MoneyStatusBadge status={o.status} />
                    </TableCell>
                    {!isClosed && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleMoneyEntryStatus("online", o.id, !isPaid(o.status))}
                          >
                            {isPaid(o.status) ? "Mark Pending" : "Mark Paid"}
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleDeleteMoneyEntry("online", o.id)}>
                            Remove
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Total Online:</span>
            <span className="font-semibold">{reconciliation?.online_collected ?? "0"}</span>
          </div>
          {!isClosed && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAddMoneyEntry("online", newOnlineCustomer, newOnlineAmount);
              }}
              className="flex items-end gap-2"
            >
              <div className="flex flex-1 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Shop</Label>
                <ShopSelect value={newOnlineCustomer} onChange={setNewOnlineCustomer} target="online" />
              </div>
              <div className="flex w-40 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newOnlineAmount}
                  onChange={(e) => setNewOnlineAmount(e.target.value)}
                />
              </div>
              <Button type="submit">Add Online Payment</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cheque Given</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {chequeEntries.length === 0 && <p className="text-sm text-muted-foreground">No cheques recorded on this trip yet.</p>}
          {chequeEntries.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Shop</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Given Date</TableHead>
                  <TableHead>Bank Deposit Date</TableHead>
                  <TableHead>Status</TableHead>
                  {!isClosed && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {chequeEntries.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>{customers.find((cu) => cu.id === c.customer_id)?.name ?? "Customer"}</TableCell>
                    <TableCell className="text-right">{c.amount}</TableCell>
                    <TableCell>{c.cheque_given_date}</TableCell>
                    <TableCell>{c.cheque_deposit_date}</TableCell>
                    <TableCell>
                      <MoneyStatusBadge status={c.status} />
                    </TableCell>
                    {!isClosed && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleMoneyEntryStatus("cheque", c.id, !isPaid(c.status))}
                          >
                            {isPaid(c.status) ? "Mark Pending" : "Mark Paid"}
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleDeleteMoneyEntry("cheque", c.id)}>
                            Remove
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Total Cheque Given:</span>
            <span className="font-semibold">{reconciliation?.cheque_given ?? "0"}</span>
          </div>
          {!isClosed && (
            <form onSubmit={handleAddChequeEntry} className="flex flex-wrap items-end gap-2">
              <div className="flex min-w-48 flex-1 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Given By (Shop)</Label>
                <ShopSelect value={newChequeCustomer} onChange={setNewChequeCustomer} target="cheque" />
              </div>
              <div className="flex w-32 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newChequeAmount}
                  onChange={(e) => setNewChequeAmount(e.target.value)}
                />
              </div>
              <div className="flex w-40 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Date Given</Label>
                <Input
                  type="date"
                  value={newChequeGivenDate}
                  onChange={(e) => setNewChequeGivenDate(e.target.value)}
                />
              </div>
              <div className="flex w-40 flex-col gap-1">
                <Label className="text-xs text-muted-foreground">Bank Deposit Date</Label>
                <Input
                  type="date"
                  value={newChequeDepositDate}
                  onChange={(e) => setNewChequeDepositDate(e.target.value)}
                />
              </div>
              <Button type="submit">Add Cheque</Button>
            </form>
          )}
        </CardContent>
      </Card>

      {reconciliation && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Reconciliation{" "}
              <Badge
                variant={isClean ? undefined : "destructive"}
                className={isClean ? "ml-2 bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "ml-2"}
              >
                {isClean ? "Clean" : "Mismatch"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4 lg:grid-cols-7">
              <div>
                <p className="text-muted-foreground">Expected Sales Value</p>
                <p className="font-medium">{reconciliation.expected_sales_value}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Cash</p>
                <p className="font-medium">{reconciliation.cash_collected}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Online</p>
                <p className="font-medium">{reconciliation.online_collected}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Credit</p>
                <p className="font-medium">{reconciliation.credit_given}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Cheque</p>
                <p className="font-medium">{reconciliation.cheque_given}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Total Collected</p>
                <p className="font-medium">{reconciliation.total_collected}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Difference</p>
                <p className={`font-medium ${Number(reconciliation.money_difference) !== 0 ? "text-destructive" : ""}`}>
                  {reconciliation.money_difference}
                </p>
              </div>
            </div>

            {moneyEntryRows.length > 0 && (
              <div>
                <p className="mb-2 text-sm text-muted-foreground">Shops with credit, online, or cheque payments on this trip</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Shop</TableHead>
                      <TableHead>Mode</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {moneyEntryRows.map((row) => (
                      <TableRow key={`${row.mode}-${row.id}`}>
                        <TableCell>{customers.find((cu) => cu.id === row.customer_id)?.name ?? "Customer"}</TableCell>
                        <TableCell>{row.mode}</TableCell>
                        <TableCell className="text-right">{row.amount}</TableCell>
                        <TableCell>
                          <MoneyStatusBadge status={row.status} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Expected value = (loaded − returned − damaged) × base price, summed across products. Compare against
              cash counted + credit given + online payments + cheques given above.
            </p>
          </CardContent>
        </Card>
      )}

      {!isClosed && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Close Day</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {!isClean && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="override">Manager override notes (optional)</Label>
                <Textarea id="override" value={overrideNotes} onChange={(e) => setOverrideNotes(e.target.value)} />
              </div>
            )}
            <Button onClick={handleCloseClick} className="self-start">
              Close Trip
            </Button>
          </CardContent>
        </Card>
      )}

      {isClosed && trip.mismatch_notes && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Manager Override Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{trip.mismatch_notes}</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={closeConfirmOpen} onOpenChange={setCloseConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reconciliation Mismatch</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            There is a mismatch of {reconciliation?.money_difference} between expected sales value and what's been
            collected. Do you want to proceed and close the trip anyway?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseConfirmOpen(false)}>
              No, Go Back
            </Button>
            <Button onClick={handleConfirmCloseMismatch}>Yes, Close Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={shopDialogTarget !== null} onOpenChange={(open) => !open && setShopDialogTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Shop</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateShop} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="shop_name">Shop Name</Label>
              <Input
                id="shop_name"
                required
                value={newShopForm.name}
                onChange={(e) => setNewShopForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="shop_owner">Owner Name</Label>
              <Input
                id="shop_owner"
                value={newShopForm.owner_name}
                onChange={(e) => setNewShopForm((f) => ({ ...f, owner_name: e.target.value }))}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="shop_phone">Phone</Label>
              <Input
                id="shop_phone"
                value={newShopForm.phone}
                onChange={(e) => setNewShopForm((f) => ({ ...f, phone: e.target.value }))}
              />
            </div>
            {shopDialogError && <p className="text-sm text-destructive">{shopDialogError}</p>}
            <DialogFooter>
              <Button type="submit" disabled={shopDialogSaving}>
                {shopDialogSaving ? "Creating..." : "Create Shop"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
