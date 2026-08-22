import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Customer {
  id: number;
  name: string;
}
interface PendingPayment {
  id: number;
  amount: string;
  created_at: string;
}
interface Reconciliation {
  id: number;
  bank_transaction_id: number;
  pending_payment_id: number | null;
  matched_customer_id: number | null;
  matched_customer_name: string | null;
  confidence_score: string;
  match_method: string | null;
  status: string;
  transaction_date: string;
  account_holder_name: string | null;
  amount: string;
  reference_number: string | null;
  narration: string | null;
}
interface CreditLogRow {
  id: number;
  trip_id: number;
  customer_id: number;
  customer_name: string;
  amount: string;
  status: string;
  trip_date: string;
  driver_id: number;
  driver_name: string;
}
interface ChequeLogRow extends CreditLogRow {
  cheque_given_date: string | null;
  cheque_deposit_date: string | null;
}
interface OpenTrip {
  id: number;
  driver_id: number;
  trip_date: string;
  status: string;
}
interface EmployeeRef {
  id: number;
  name: string;
}

function ConfidenceBadge({ score }: { score: string }) {
  const n = Number(score);
  const cls =
    n >= 95
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
      : n >= 80
        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
        : "bg-secondary text-secondary-foreground";
  return <Badge className={cls}>{n.toFixed(1)}%</Badge>;
}

function TransactionRow({
  row,
  children,
}: {
  row: Reconciliation;
  children?: React.ReactNode;
}) {
  return (
    <TableRow>
      <TableCell>{row.transaction_date}</TableCell>
      <TableCell>{row.account_holder_name ?? "—"}</TableCell>
      <TableCell className="text-right">{row.amount}</TableCell>
      <TableCell>{row.matched_customer_name ?? "—"}</TableCell>
      <TableCell>
        <ConfidenceBadge score={row.confidence_score} />
      </TableCell>
      <TableCell className="text-muted-foreground">{row.match_method ?? "—"}</TableCell>
      {children && <TableCell className="text-right">{children}</TableCell>}
    </TableRow>
  );
}

export function ReconciliationPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [autoMatched, setAutoMatched] = useState<Reconciliation[]>([]);
  const [suggested, setSuggested] = useState<Reconciliation[]>([]);
  const [unmatched, setUnmatched] = useState<Reconciliation[]>([]);
  const [history, setHistory] = useState<Reconciliation[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [credits, setCredits] = useState<CreditLogRow[]>([]);
  const [creditActionError, setCreditActionError] = useState<string | null>(null);
  const [creditSearch, setCreditSearch] = useState("");

  const filteredCredits = useMemo(() => {
    const term = creditSearch.trim().toLowerCase();
    if (!term) return credits;
    return credits.filter((c) =>
      [c.customer_name, c.driver_name, c.trip_date].some((v) => v.toLowerCase().includes(term))
    );
  }, [credits, creditSearch]);

  const [cheques, setCheques] = useState<ChequeLogRow[]>([]);
  const [chequeActionError, setChequeActionError] = useState<string | null>(null);
  const [chequeSearch, setChequeSearch] = useState("");
  const [openTrips, setOpenTrips] = useState<OpenTrip[]>([]);
  const [drivers, setDrivers] = useState<EmployeeRef[]>([]);
  const [newChequeTrip, setNewChequeTrip] = useState("");
  const [newChequeCustomer, setNewChequeCustomer] = useState("");
  const [newChequeAmount, setNewChequeAmount] = useState("");
  const [newChequeGivenDate, setNewChequeGivenDate] = useState("");
  const [newChequeDepositDate, setNewChequeDepositDate] = useState("");

  const filteredCheques = useMemo(() => {
    const term = chequeSearch.trim().toLowerCase();
    if (!term) return cheques;
    return cheques.filter((c) =>
      [c.customer_name, c.driver_name, c.trip_date].some((v) => v.toLowerCase().includes(term))
    );
  }, [cheques, chequeSearch]);

  const [manualCustomer, setManualCustomer] = useState<Record<number, string>>({});
  const [manualPending, setManualPending] = useState<Record<number, string>>({});
  const [pendingOptions, setPendingOptions] = useState<Record<number, PendingPayment[]>>({});

  async function refresh() {
    const [autoData, suggestedData, unmatchedData, approvedData, rejectedData] = await Promise.all([
      api.get<Reconciliation[]>("/reconciliations", { params: { status: "auto_matched" } }).then((r) => r.data),
      api.get<Reconciliation[]>("/reconciliations", { params: { status: "suggested" } }).then((r) => r.data),
      api.get<Reconciliation[]>("/reconciliations", { params: { status: "unmatched" } }).then((r) => r.data),
      api.get<Reconciliation[]>("/reconciliations", { params: { status: "approved" } }).then((r) => r.data),
      api.get<Reconciliation[]>("/reconciliations", { params: { status: "rejected" } }).then((r) => r.data),
    ]);
    setAutoMatched(autoData);
    setSuggested(suggestedData);
    setUnmatched(unmatchedData);
    setHistory([...approvedData, ...rejectedData].sort((a, b) => b.id - a.id));
  }

  async function refreshCredits() {
    const data = await api.get<CreditLogRow[]>("/reports/trip-credits").then((r) => r.data);
    setCredits(data);
  }

  async function refreshCheques() {
    const [chequeData, tripsData] = await Promise.all([
      api.get<ChequeLogRow[]>("/reports/trip-cheques").then((r) => r.data),
      listResource<OpenTrip>("/trips"),
    ]);
    setCheques(chequeData);
    setOpenTrips(tripsData.filter((t) => t.status !== "closed"));
  }

  useEffect(() => {
    refresh();
    refreshCredits();
    refreshCheques();
    listResource<Customer>("/customers").then(setCustomers);
    listResource<EmployeeRef>("/employees").then(setDrivers);
  }, []);

  async function handleToggleCreditPaid(row: CreditLogRow, paid: boolean) {
    setCreditActionError(null);
    try {
      await api.patch(`/trips/${row.trip_id}/credit-entries/${row.id}`, { paid });
      await refreshCredits();
    } catch {
      setCreditActionError("Could not update credit status — the trip may already be closed.");
    }
  }

  async function handleAddCheque(e: React.FormEvent) {
    e.preventDefault();
    if (!newChequeTrip || !newChequeCustomer || !newChequeAmount || !newChequeGivenDate || !newChequeDepositDate) return;
    setChequeActionError(null);
    try {
      await api.post(`/trips/${newChequeTrip}/cheque-entries`, {
        customer_id: Number(newChequeCustomer),
        amount: Number(newChequeAmount),
        cheque_given_date: newChequeGivenDate,
        cheque_deposit_date: newChequeDepositDate,
      });
      setNewChequeTrip("");
      setNewChequeCustomer("");
      setNewChequeAmount("");
      setNewChequeGivenDate("");
      setNewChequeDepositDate("");
      await refreshCheques();
    } catch {
      setChequeActionError("Could not add cheque — check the values and try again.");
    }
  }

  async function handleToggleChequePaid(row: ChequeLogRow, paid: boolean) {
    setChequeActionError(null);
    try {
      await api.patch(`/trips/${row.trip_id}/cheque-entries/${row.id}`, { paid });
      await refreshCheques();
    } catch {
      setChequeActionError("Could not update cheque status — the trip may already be closed.");
    }
  }

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/bank-statements/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult(
        `Imported ${data.transactions_imported} transactions — ${data.auto_matched} auto-matched, ${data.suggested} suggested, ${data.unmatched} unmatched, ${data.ignored} ignored (outgoing).`
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refresh();
    } catch {
      setUploadError("Could not import statement. Check the CSV format and try again.");
    } finally {
      setUploading(false);
    }
  }

  async function handleApprove(id: number) {
    await api.post(`/reconciliations/${id}/approve`);
    await refresh();
  }

  async function handleReject(id: number) {
    await api.post(`/reconciliations/${id}/reject`);
    await refresh();
  }

  async function loadPendingOptionsFor(row: Reconciliation, customerId: string) {
    const { data } = await api.get<PendingPayment[]>(`/customers/${customerId}/pending-online-payments`);
    setPendingOptions((prev) => ({ ...prev, [row.id]: data }));
  }

  async function handleManualMatch(row: Reconciliation) {
    const customerId = manualCustomer[row.id];
    const pendingId = manualPending[row.id];
    if (!customerId || !pendingId) return;
    await api.post(`/reconciliations/${row.id}/manual-match`, {
      customer_id: Number(customerId),
      pending_payment_id: Number(pendingId),
    });
    await refresh();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Import Bank Statement (CSV)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            Columns required: transaction_date (YYYY-MM-DD), amount, direction (credit/debit), plus optional
            account_holder_name, reference_number, narration. Outgoing (debit) rows are ignored automatically.
          </p>
          <div className="flex items-center gap-2">
            <input ref={fileInputRef} type="file" accept=".csv" className="text-sm" />
            <Button onClick={handleUpload} disabled={uploading}>
              {uploading ? "Importing..." : "Import"}
            </Button>
          </div>
          {uploadResult && <p className="text-sm text-emerald-700 dark:text-emerald-400">{uploadResult}</p>}
          {uploadError && <p className="text-sm text-destructive">{uploadError}</p>}
        </CardContent>
      </Card>

      <Tabs defaultValue="credits">
        <TabsList>
          <TabsTrigger value="credits">Credits</TabsTrigger>
          <TabsTrigger value="cheques">Cheques</TabsTrigger>
          <TabsTrigger value="auto">Automatically Matched ({autoMatched.length})</TabsTrigger>
          <TabsTrigger value="suggested">Suggested Matches ({suggested.length})</TabsTrigger>
          <TabsTrigger value="unmatched">Unmatched ({unmatched.length})</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="auto">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Bank Name</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Shop</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Method</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {autoMatched.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        Nothing here yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {autoMatched.map((row) => (
                    <TransactionRow key={row.id} row={row} />
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="suggested">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Bank Name</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Suggested Shop</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suggested.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        Nothing here yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {suggested.map((row) => (
                    <TransactionRow key={row.id} row={row}>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => handleApprove(row.id)}>
                          Approve
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleReject(row.id)}>
                          Reject
                        </Button>
                      </div>
                    </TransactionRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="unmatched">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Bank Name</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Best Guess</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Manual Match</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {unmatched.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        Nothing here yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {unmatched.map((row) => (
                    <TransactionRow key={row.id} row={row}>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => handleManualMatch(row)}>
                          Match
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleReject(row.id)}>
                          Reject
                        </Button>
                      </div>
                    </TransactionRow>
                  ))}
                </TableBody>
              </Table>
              {unmatched.length > 0 && (
                <div className="mt-4 flex flex-col gap-3 border-t pt-4">
                  <p className="text-sm font-medium">Pick a shop + outstanding online payment for each unmatched row:</p>
                  {unmatched.map((row) => (
                    <div key={row.id} className="flex items-center gap-2 text-sm">
                      <span className="w-40 truncate text-muted-foreground">
                        {row.account_holder_name} ({row.amount})
                      </span>
                      <Select
                        value={manualCustomer[row.id] ?? ""}
                        onValueChange={(v) => {
                          setManualCustomer((prev) => ({ ...prev, [row.id]: v }));
                          loadPendingOptionsFor(row, v);
                        }}
                      >
                        <SelectTrigger className="w-48">
                          <SelectValue placeholder="Shop" />
                        </SelectTrigger>
                        <SelectContent>
                          {customers.map((c) => (
                            <SelectItem key={c.id} value={String(c.id)}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select
                        value={manualPending[row.id] ?? ""}
                        onValueChange={(v) => setManualPending((prev) => ({ ...prev, [row.id]: v }))}
                      >
                        <SelectTrigger className="w-56">
                          <SelectValue placeholder="Outstanding payment" />
                        </SelectTrigger>
                        <SelectContent>
                          {(pendingOptions[row.id] ?? []).map((p) => (
                            <SelectItem key={p.id} value={String(p.id)}>
                              #{p.id} — {p.amount}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Bank Name</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Shop</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        Nothing here yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {history.map((row) => (
                    <TransactionRow key={row.id} row={row}>
                      <Badge
                        className={
                          row.status === "approved"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : undefined
                        }
                        variant={row.status === "rejected" ? "destructive" : undefined}
                      >
                        {row.status}
                      </Badge>
                    </TransactionRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="credits">
          <div className="flex flex-col gap-4">
            {creditActionError && <p className="text-sm text-destructive">{creditActionError}</p>}

            <Input
              placeholder="Search by shop, driver, or trip date..."
              value={creditSearch}
              onChange={(e) => setCreditSearch(e.target.value)}
              className="max-w-sm"
            />

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Yet to be Paid</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Shop</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Trip Date</TableHead>
                      <TableHead>Driver</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredCredits.filter((c) => c.status !== "cleared").length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          {credits.filter((c) => c.status !== "cleared").length === 0
                            ? "Nothing outstanding."
                            : "No matches in your search."}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredCredits
                      .filter((c) => c.status !== "cleared")
                      .map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>{row.customer_name}</TableCell>
                          <TableCell className="text-right">{row.amount}</TableCell>
                          <TableCell>{row.trip_date}</TableCell>
                          <TableCell>{row.driver_name}</TableCell>
                          <TableCell className="text-right">
                            <Button size="sm" onClick={() => handleToggleCreditPaid(row, true)}>
                              Mark Paid
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Paid</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Shop</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Trip Date</TableHead>
                      <TableHead>Driver</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredCredits.filter((c) => c.status === "cleared").length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          {credits.filter((c) => c.status === "cleared").length === 0
                            ? "Nothing paid yet."
                            : "No matches in your search."}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredCredits
                      .filter((c) => c.status === "cleared")
                      .map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>{row.customer_name}</TableCell>
                          <TableCell className="text-right">{row.amount}</TableCell>
                          <TableCell>{row.trip_date}</TableCell>
                          <TableCell>{row.driver_name}</TableCell>
                          <TableCell className="text-right">
                            <Button size="sm" variant="outline" onClick={() => handleToggleCreditPaid(row, false)}>
                              Mark Pending
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cheques">
          <div className="flex flex-col gap-4">
            {chequeActionError && <p className="text-sm text-destructive">{chequeActionError}</p>}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Add Cheque</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAddCheque} className="flex flex-wrap items-end gap-2">
                  <div className="flex w-56 flex-col gap-1">
                    <label className="text-xs text-muted-foreground">Trip</label>
                    <Select value={newChequeTrip} onValueChange={setNewChequeTrip}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select trip" />
                      </SelectTrigger>
                      <SelectContent>
                        {openTrips.map((t) => (
                          <SelectItem key={t.id} value={String(t.id)}>
                            Trip #{t.id} — {t.trip_date} — {drivers.find((d) => d.id === t.driver_id)?.name ?? "?"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex min-w-48 flex-1 flex-col gap-1">
                    <label className="text-xs text-muted-foreground">Given By (Shop)</label>
                    <Select value={newChequeCustomer} onValueChange={setNewChequeCustomer}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Customer / shop" />
                      </SelectTrigger>
                      <SelectContent>
                        {customers.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex w-32 flex-col gap-1">
                    <label className="text-xs text-muted-foreground">Amount</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={newChequeAmount}
                      onChange={(e) => setNewChequeAmount(e.target.value)}
                    />
                  </div>
                  <div className="flex w-40 flex-col gap-1">
                    <label className="text-xs text-muted-foreground">Date Given</label>
                    <Input type="date" value={newChequeGivenDate} onChange={(e) => setNewChequeGivenDate(e.target.value)} />
                  </div>
                  <div className="flex w-40 flex-col gap-1">
                    <label className="text-xs text-muted-foreground">Bank Deposit Date</label>
                    <Input
                      type="date"
                      value={newChequeDepositDate}
                      onChange={(e) => setNewChequeDepositDate(e.target.value)}
                    />
                  </div>
                  <Button type="submit">Add Cheque</Button>
                </form>
              </CardContent>
            </Card>

            <Input
              placeholder="Search by shop, driver, or trip date..."
              value={chequeSearch}
              onChange={(e) => setChequeSearch(e.target.value)}
              className="max-w-sm"
            />

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Cheques</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Given By</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Driver</TableHead>
                      <TableHead>Date Given</TableHead>
                      <TableHead>Bank Deposit Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredCheques.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground">
                          {cheques.length === 0 ? "No cheques recorded yet." : "No cheques match your search."}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredCheques.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.customer_name}</TableCell>
                        <TableCell className="text-right">{row.amount}</TableCell>
                        <TableCell>{row.driver_name}</TableCell>
                        <TableCell>{row.cheque_given_date}</TableCell>
                        <TableCell>{row.cheque_deposit_date}</TableCell>
                        <TableCell>
                          <Badge
                            className={
                              row.status === "cleared"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                            }
                          >
                            {row.status === "cleared" ? "Paid" : "Pending"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {row.status === "cleared" ? (
                            <Button size="sm" variant="outline" onClick={() => handleToggleChequePaid(row, false)}>
                              Mark Pending
                            </Button>
                          ) : (
                            <Button size="sm" onClick={() => handleToggleChequePaid(row, true)}>
                              Mark Paid
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
