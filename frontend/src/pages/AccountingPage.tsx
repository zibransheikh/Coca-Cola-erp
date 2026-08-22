import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Account {
  id: number;
  code: string;
  name: string;
  account_type: string;
}
interface TrialBalanceRow {
  account_id: number;
  code: string;
  name: string;
  account_type: string;
  debit_total: string;
  credit_total: string;
}
interface TrialBalance {
  rows: TrialBalanceRow[];
  total_debit: string;
  total_credit: string;
  balanced: boolean;
}
interface PLLine {
  code: string;
  name: string;
  amount: string;
}
interface ProfitAndLoss {
  income: PLLine[];
  expenses: PLLine[];
  total_income: string;
  total_expenses: string;
  net_profit: string;
}
interface BalanceSheetLine {
  code: string;
  name: string;
  amount: string;
}
interface BalanceSheet {
  assets: BalanceSheetLine[];
  liabilities: BalanceSheetLine[];
  equity: BalanceSheetLine[];
  retained_earnings: string;
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  balanced: boolean;
}
interface GLRow {
  journal_entry_id: number;
  entry_date: string;
  reference_type: string | null;
  narration: string | null;
  debit: string;
  credit: string;
  running_balance: string;
}
interface JELine {
  account_id: number;
  account_code: string;
  account_name: string;
  debit: string;
  credit: string;
}
interface JournalEntry {
  id: number;
  entry_date: string;
  reference_type: string | null;
  narration: string | null;
  lines: JELine[];
}

function BalancedBadge({ balanced }: { balanced: boolean }) {
  return (
    <Badge
      className={
        balanced
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
          : undefined
      }
      variant={balanced ? undefined : "destructive"}
    >
      {balanced ? "Balanced" : "Out of balance"}
    </Badge>
  );
}

export function AccountingPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [pl, setPl] = useState<ProfitAndLoss | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheet | null>(null);
  const [glAccountId, setGlAccountId] = useState("");
  const [glRows, setGlRows] = useState<GLRow[]>([]);
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);

  const [jeDate, setJeDate] = useState("");
  const [jeNarration, setJeNarration] = useState("");
  const [jeLines, setJeLines] = useState([{ account_id: "", debit: "", credit: "" }]);
  const [jeError, setJeError] = useState<string | null>(null);

  async function refreshReports() {
    api.get<TrialBalance>("/accounting/trial-balance").then((r) => setTrialBalance(r.data));
    api.get<ProfitAndLoss>("/accounting/profit-and-loss").then((r) => setPl(r.data));
    api.get<BalanceSheet>("/accounting/balance-sheet").then((r) => setBalanceSheet(r.data));
    api.get<JournalEntry[]>("/accounting/journal-entries").then((r) => setJournalEntries(r.data));
  }

  useEffect(() => {
    listResource<Account>("/chart-of-accounts").then(setAccounts);
    refreshReports();
  }, []);

  useEffect(() => {
    if (glAccountId) {
      api.get<GLRow[]>("/accounting/general-ledger", { params: { account_id: glAccountId } }).then((r) => setGlRows(r.data));
    }
  }, [glAccountId]);

  async function handleCreateJournalEntry(e: React.FormEvent) {
    e.preventDefault();
    setJeError(null);
    try {
      await api.post("/accounting/journal-entries", {
        entry_date: jeDate,
        narration: jeNarration,
        lines: jeLines
          .filter((l) => l.account_id && (l.debit || l.credit))
          .map((l) => ({
            account_id: Number(l.account_id),
            debit: l.debit ? Number(l.debit) : 0,
            credit: l.credit ? Number(l.credit) : 0,
          })),
      });
      setJeDate("");
      setJeNarration("");
      setJeLines([{ account_id: "", debit: "", credit: "" }]);
      await refreshReports();
    } catch {
      setJeError("Could not post — check the entry balances (total debit must equal total credit).");
    }
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Accounting</h2>
      <Tabs defaultValue="trial-balance">
        <TabsList>
          <TabsTrigger value="trial-balance">Trial Balance</TabsTrigger>
          <TabsTrigger value="pl">Profit &amp; Loss</TabsTrigger>
          <TabsTrigger value="balance-sheet">Balance Sheet</TabsTrigger>
          <TabsTrigger value="general-ledger">General Ledger</TabsTrigger>
          <TabsTrigger value="journal-entries">Journal Entries</TabsTrigger>
        </TabsList>

        <TabsContent value="trial-balance">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                Trial Balance {trialBalance && <BalancedBadge balanced={trialBalance.balanced} />}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trialBalance?.rows.map((row) => (
                    <TableRow key={row.account_id}>
                      <TableCell>{row.code}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell className="text-muted-foreground">{row.account_type}</TableCell>
                      <TableCell className="text-right">{row.debit_total}</TableCell>
                      <TableCell className="text-right">{row.credit_total}</TableCell>
                    </TableRow>
                  ))}
                  {trialBalance && (
                    <TableRow className="font-medium">
                      <TableCell colSpan={3}>Total</TableCell>
                      <TableCell className="text-right">{trialBalance.total_debit}</TableCell>
                      <TableCell className="text-right">{trialBalance.total_credit}</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Profit &amp; Loss</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div>
                <p className="mb-1 text-sm font-medium">Income</p>
                {pl?.income.map((line) => (
                  <div key={line.code} className="flex justify-between text-sm">
                    <span>{line.name}</span>
                    <span>{line.amount}</span>
                  </div>
                ))}
                <div className="flex justify-between border-t pt-1 text-sm font-medium">
                  <span>Total Income</span>
                  <span>{pl?.total_income}</span>
                </div>
              </div>
              <div>
                <p className="mb-1 text-sm font-medium">Expenses</p>
                {pl?.expenses.map((line) => (
                  <div key={line.code} className="flex justify-between text-sm">
                    <span>{line.name}</span>
                    <span>{line.amount}</span>
                  </div>
                ))}
                <div className="flex justify-between border-t pt-1 text-sm font-medium">
                  <span>Total Expenses</span>
                  <span>{pl?.total_expenses}</span>
                </div>
              </div>
              <div className="flex justify-between border-t pt-2 text-base font-semibold">
                <span>Net Profit</span>
                <span className={Number(pl?.net_profit) < 0 ? "text-destructive" : "text-emerald-700 dark:text-emerald-400"}>
                  {pl?.net_profit}
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="balance-sheet">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                Balance Sheet {balanceSheet && <BalancedBadge balanced={balanceSheet.balanced} />}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-sm font-medium">Assets</p>
                {balanceSheet?.assets.map((line) => (
                  <div key={line.code} className="flex justify-between text-sm">
                    <span>{line.name}</span>
                    <span>{line.amount}</span>
                  </div>
                ))}
                <div className="flex justify-between border-t pt-1 text-sm font-medium">
                  <span>Total Assets</span>
                  <span>{balanceSheet?.total_assets}</span>
                </div>
              </div>
              <div>
                <p className="mb-1 text-sm font-medium">Liabilities</p>
                {balanceSheet?.liabilities.map((line) => (
                  <div key={line.code} className="flex justify-between text-sm">
                    <span>{line.name}</span>
                    <span>{line.amount}</span>
                  </div>
                ))}
                <div className="flex justify-between border-t pt-1 text-sm font-medium">
                  <span>Total Liabilities</span>
                  <span>{balanceSheet?.total_liabilities}</span>
                </div>

                <p className="mt-4 mb-1 text-sm font-medium">Equity</p>
                {balanceSheet?.equity.map((line) => (
                  <div key={line.code} className="flex justify-between text-sm">
                    <span>{line.name}</span>
                    <span>{line.amount}</span>
                  </div>
                ))}
                <div className="flex justify-between text-sm">
                  <span>Retained Earnings (all-time net income)</span>
                  <span>{balanceSheet?.retained_earnings}</span>
                </div>
                <div className="flex justify-between border-t pt-1 text-sm font-medium">
                  <span>Total Equity + Retained Earnings</span>
                  <span>
                    {balanceSheet && (Number(balanceSheet.total_equity) + Number(balanceSheet.retained_earnings)).toFixed(2)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="general-ledger">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">General Ledger</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <Select value={glAccountId} onValueChange={setGlAccountId}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select an account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      {a.code} — {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {glAccountId && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Narration</TableHead>
                      <TableHead className="text-right">Debit</TableHead>
                      <TableHead className="text-right">Credit</TableHead>
                      <TableHead className="text-right">Running Balance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {glRows.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          No postings yet.
                        </TableCell>
                      </TableRow>
                    )}
                    {glRows.map((row) => (
                      <TableRow key={row.journal_entry_id}>
                        <TableCell>{row.entry_date}</TableCell>
                        <TableCell>{row.narration ?? "—"}</TableCell>
                        <TableCell className="text-right">{row.debit}</TableCell>
                        <TableCell className="text-right">{row.credit}</TableCell>
                        <TableCell className="text-right">{row.running_balance}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="journal-entries">
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Post Manual Journal Entry</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateJournalEntry} className="flex flex-col gap-3">
                  <div className="flex gap-2">
                    <div className="flex flex-1 flex-col gap-2">
                      <Label htmlFor="je-date">Date</Label>
                      <Input id="je-date" type="date" required value={jeDate} onChange={(e) => setJeDate(e.target.value)} />
                    </div>
                    <div className="flex flex-[2] flex-col gap-2">
                      <Label htmlFor="je-narration">Narration</Label>
                      <Input
                        id="je-narration"
                        required
                        value={jeNarration}
                        onChange={(e) => setJeNarration(e.target.value)}
                      />
                    </div>
                  </div>
                  {jeLines.map((line, i) => (
                    <div key={i} className="flex gap-2">
                      <Select
                        value={line.account_id}
                        onValueChange={(v) =>
                          setJeLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, account_id: v } : l)))
                        }
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Account" />
                        </SelectTrigger>
                        <SelectContent>
                          {accounts.map((a) => (
                            <SelectItem key={a.id} value={String(a.id)}>
                              {a.code} — {a.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="Debit"
                        className="w-32"
                        value={line.debit}
                        onChange={(e) =>
                          setJeLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, debit: e.target.value } : l)))
                        }
                      />
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="Credit"
                        className="w-32"
                        value={line.credit}
                        onChange={(e) =>
                          setJeLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, credit: e.target.value } : l)))
                        }
                      />
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="self-start"
                    onClick={() => setJeLines((prev) => [...prev, { account_id: "", debit: "", credit: "" }])}
                  >
                    Add Line
                  </Button>
                  {jeError && <p className="text-sm text-destructive">{jeError}</p>}
                  <Button type="submit" className="self-start">
                    Post Entry
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent Journal Entries</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {journalEntries.map((entry) => (
                  <div key={entry.id} className="rounded-lg border p-3 text-sm">
                    <div className="mb-1 flex justify-between font-medium">
                      <span>{entry.narration ?? entry.reference_type}</span>
                      <span className="text-muted-foreground">{entry.entry_date}</span>
                    </div>
                    {entry.lines.map((line, i) => (
                      <div key={i} className="flex justify-between text-muted-foreground">
                        <span>
                          {line.account_code} — {line.account_name}
                        </span>
                        <span>{Number(line.debit) > 0 ? `Dr ${line.debit}` : `Cr ${line.credit}`}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
