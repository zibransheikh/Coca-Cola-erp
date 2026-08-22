import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Employee {
  id: number;
  name: string;
}
interface PayrollRow {
  employee_id: number;
  employee_name: string;
  monthly_salary: string;
  leave_days: number;
  half_days: number;
  absent_days: number;
  advances_total: string;
  net_payable: string;
  paid: boolean;
  paid_at: string | null;
  salary_payment_id: number | null;
}
interface SalaryPayment {
  id: number;
  employee_id: number;
  period_start: string;
  period_end: string;
  gross_amount: string;
  advances_deducted: string;
  net_amount: string;
  paid_at: string | null;
}

function monthBounds(offsetMonths = 0) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() + offsetMonths, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + offsetMonths + 1, 0);
  // Not toISOString() — that normalizes to UTC first, which shifts the date
  // backward a day in any timezone behind UTC. Format from local fields instead.
  const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { start: fmt(start), end: fmt(end) };
}

export function PayrollPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [periodStart, setPeriodStart] = useState(monthBounds().start);
  const [periodEnd, setPeriodEnd] = useState(monthBounds().end);
  const [rows, setRows] = useState<PayrollRow[]>([]);
  const [payments, setPayments] = useState<SalaryPayment[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [payingId, setPayingId] = useState<number | null>(null);

  const [leaveForm, setLeaveForm] = useState({ employee_id: "", start_date: "", end_date: "", status: "leave" });
  const [leaveError, setLeaveError] = useState<string | null>(null);
  const [leaveSaving, setLeaveSaving] = useState(false);

  const [advanceForm, setAdvanceForm] = useState({ employee_id: "", amount: "", advance_date: "", reason: "" });
  const [advanceError, setAdvanceError] = useState<string | null>(null);
  const [advanceSaving, setAdvanceSaving] = useState(false);

  async function refreshSummary() {
    const { data } = await api.get<PayrollRow[]>("/payroll/summary", {
      params: { period_start: periodStart, period_end: periodEnd },
    });
    setRows(data);
  }

  async function refreshPayments() {
    const data = await listResource<SalaryPayment>("/payroll/payments");
    setPayments(data);
  }

  useEffect(() => {
    listResource<Employee>("/employees").then(setEmployees);
    refreshPayments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refreshSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodStart, periodEnd]);

  async function handlePay(employeeId: number) {
    setActionError(null);
    setPayingId(employeeId);
    try {
      await api.post("/payroll/pay", {
        employee_id: employeeId,
        period_start: periodStart,
        period_end: periodEnd,
      });
      await Promise.all([refreshSummary(), refreshPayments()]);
    } catch {
      setActionError("Could not record payment — it may already be paid for this period.");
    } finally {
      setPayingId(null);
    }
  }

  async function handleMarkLeave(e: React.FormEvent) {
    e.preventDefault();
    if (!leaveForm.employee_id || !leaveForm.start_date || !leaveForm.end_date) return;
    setLeaveError(null);
    setLeaveSaving(true);
    try {
      await api.post("/payroll/attendance", {
        employee_id: Number(leaveForm.employee_id),
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        status: leaveForm.status,
      });
      setLeaveForm({ employee_id: "", start_date: "", end_date: "", status: "leave" });
      await refreshSummary();
    } catch {
      setLeaveError("Could not mark attendance — check the dates and try again.");
    } finally {
      setLeaveSaving(false);
    }
  }

  async function handleAddAdvance(e: React.FormEvent) {
    e.preventDefault();
    if (!advanceForm.employee_id || !advanceForm.amount || !advanceForm.advance_date) return;
    setAdvanceError(null);
    setAdvanceSaving(true);
    try {
      await api.post("/payroll/advances", {
        employee_id: Number(advanceForm.employee_id),
        amount: Number(advanceForm.amount),
        advance_date: advanceForm.advance_date,
        reason: advanceForm.reason || null,
      });
      setAdvanceForm({ employee_id: "", amount: "", advance_date: "", reason: "" });
      await refreshSummary();
    } catch {
      setAdvanceError("Could not record advance — check the values and try again.");
    } finally {
      setAdvanceSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Payroll</h2>
      </div>

      {actionError && <p className="text-sm text-destructive">{actionError}</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Period</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-1">
            <Label className="text-xs text-muted-foreground">From</Label>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-xs text-muted-foreground">To</Label>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </div>
          <Button
            variant="outline"
            onClick={() => {
              const { start, end } = monthBounds();
              setPeriodStart(start);
              setPeriodEnd(end);
            }}
          >
            This Month
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payroll Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead className="text-right">Monthly Salary</TableHead>
                <TableHead className="text-right">Leave Days</TableHead>
                <TableHead className="text-right">Half Days</TableHead>
                <TableHead className="text-right">Absent Days</TableHead>
                <TableHead className="text-right">Advances</TableHead>
                <TableHead className="text-right">Net Payable</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground">
                    No active employees.
                  </TableCell>
                </TableRow>
              )}
              {rows.map((row) => (
                <TableRow key={row.employee_id}>
                  <TableCell>{row.employee_name}</TableCell>
                  <TableCell className="text-right">{row.monthly_salary}</TableCell>
                  <TableCell className="text-right">{row.leave_days}</TableCell>
                  <TableCell className="text-right">{row.half_days}</TableCell>
                  <TableCell className="text-right">{row.absent_days}</TableCell>
                  <TableCell className="text-right">{row.advances_total}</TableCell>
                  <TableCell
                    className={`text-right font-medium ${Number(row.net_payable) < 0 ? "text-destructive" : ""}`}
                  >
                    {row.net_payable}
                  </TableCell>
                  <TableCell>
                    {row.paid ? (
                      <span className="text-sm text-muted-foreground">
                        Paid on {row.paid_at ? row.paid_at.slice(0, 10) : "—"}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">Not paid</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {!row.paid && (
                      <Button size="sm" onClick={() => handlePay(row.employee_id)} disabled={payingId === row.employee_id}>
                        {payingId === row.employee_id ? "Paying..." : "Pay"}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mark Attendance / Leave</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleMarkLeave} className="flex flex-wrap items-end gap-2">
            <div className="flex min-w-40 flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Employee</Label>
              <Select
                value={leaveForm.employee_id}
                onValueChange={(v) => setLeaveForm((f) => ({ ...f, employee_id: v }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">From</Label>
              <Input
                type="date"
                value={leaveForm.start_date}
                onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">To</Label>
              <Input
                type="date"
                value={leaveForm.end_date}
                onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))}
              />
            </div>
            <div className="flex w-36 flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Status</Label>
              <Select value={leaveForm.status} onValueChange={(v) => setLeaveForm((f) => ({ ...f, status: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leave">Leave</SelectItem>
                  <SelectItem value="absent">Absent</SelectItem>
                  <SelectItem value="half_day">Half Day</SelectItem>
                  <SelectItem value="present">Present</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={leaveSaving}>
              {leaveSaving ? "Saving..." : "Mark"}
            </Button>
          </form>
          {leaveError && <p className="mt-2 text-sm text-destructive">{leaveError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Salary Advance</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAddAdvance} className="flex flex-wrap items-end gap-2">
            <div className="flex min-w-40 flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Employee</Label>
              <Select
                value={advanceForm.employee_id}
                onValueChange={(v) => setAdvanceForm((f) => ({ ...f, employee_id: v }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex w-32 flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Amount</Label>
              <Input
                type="number"
                step="0.01"
                value={advanceForm.amount}
                onChange={(e) => setAdvanceForm((f) => ({ ...f, amount: e.target.value }))}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Date</Label>
              <Input
                type="date"
                value={advanceForm.advance_date}
                onChange={(e) => setAdvanceForm((f) => ({ ...f, advance_date: e.target.value }))}
              />
            </div>
            <div className="flex min-w-40 flex-1 flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Reason</Label>
              <Input
                value={advanceForm.reason}
                onChange={(e) => setAdvanceForm((f) => ({ ...f, reason: e.target.value }))}
              />
            </div>
            <Button type="submit" disabled={advanceSaving}>
              {advanceSaving ? "Saving..." : "Add Advance"}
            </Button>
          </form>
          {advanceError && <p className="mt-2 text-sm text-destructive">{advanceError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payment History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Period</TableHead>
                <TableHead className="text-right">Gross</TableHead>
                <TableHead className="text-right">Advances Deducted</TableHead>
                <TableHead className="text-right">Net Paid</TableHead>
                <TableHead>Date Paid</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payments.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No payments recorded yet.
                  </TableCell>
                </TableRow>
              )}
              {payments.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{employees.find((e) => e.id === p.employee_id)?.name ?? "—"}</TableCell>
                  <TableCell>
                    {p.period_start} – {p.period_end}
                  </TableCell>
                  <TableCell className="text-right">{p.gross_amount}</TableCell>
                  <TableCell className="text-right">{p.advances_deducted}</TableCell>
                  <TableCell className="text-right font-medium">{p.net_amount}</TableCell>
                  <TableCell>{p.paid_at ? p.paid_at.slice(0, 10) : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
