import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface ExpenseCategory {
  id: number;
  name: string;
}
interface Vehicle {
  id: number;
  registration_number: string;
}
interface Expense {
  id: number;
  category_id: number;
  vehicle_id: number | null;
  amount: string;
  expense_date: string;
  description: string | null;
  status: string;
}

// Explicit semantic colors rather than the brand-red "default" badge variant
// — "approved" in brand red would read as a warning, not a good outcome.
const STATUS_CLASS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  approved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  rejected: "", // falls through to the destructive variant below
};

export function ExpensesPage() {
  const { hasPermission } = useAuth();
  const canApprove = hasPermission("can_approve_expense");
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [form, setForm] = useState({ category_id: "", vehicle_id: "", amount: "", expense_date: "", description: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    const data = await listResource<Expense>("/expenses");
    setExpenses(data);
  }

  useEffect(() => {
    refresh();
    listResource<ExpenseCategory>("/expense-categories").then(setCategories);
    listResource<Vehicle>("/vehicles").then(setVehicles);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/expenses", {
        category_id: Number(form.category_id),
        vehicle_id: form.vehicle_id ? Number(form.vehicle_id) : null,
        amount: Number(form.amount),
        expense_date: form.expense_date,
        description: form.description || null,
      });
      setForm({ category_id: "", vehicle_id: "", amount: "", expense_date: "", description: "" });
      await refresh();
    } catch {
      setError("Could not submit expense. Check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDecision(id: number, action: "approve" | "reject") {
    await api.post(`/expenses/${id}/${action}`);
    await refresh();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Submit Expense</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="flex gap-2">
              <Select value={form.category_id} onValueChange={(v) => setForm((f) => ({ ...f, category_id: v }))}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={form.vehicle_id} onValueChange={(v) => setForm((f) => ({ ...f, vehicle_id: v }))}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Vehicle (optional)" />
                </SelectTrigger>
                <SelectContent>
                  {vehicles.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      {v.registration_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <div className="flex flex-1 flex-col gap-2">
                <Label htmlFor="amount">Amount</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  required
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                />
              </div>
              <div className="flex flex-1 flex-col gap-2">
                <Label htmlFor="expense_date">Date</Label>
                <Input
                  id="expense_date"
                  type="date"
                  required
                  value={form.expense_date}
                  onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={submitting} className="self-start">
              {submitting ? "Submitting..." : "Submit Expense"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="overflow-x-auto rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Category</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Status</TableHead>
              {canApprove && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {expenses.length === 0 && (
              <TableRow>
                <TableCell colSpan={canApprove ? 7 : 6} className="text-center text-muted-foreground">
                  No expenses yet.
                </TableCell>
              </TableRow>
            )}
            {expenses.map((exp) => (
              <TableRow key={exp.id}>
                <TableCell>{categories.find((c) => c.id === exp.category_id)?.name ?? "—"}</TableCell>
                <TableCell>{vehicles.find((v) => v.id === exp.vehicle_id)?.registration_number ?? "—"}</TableCell>
                <TableCell>{exp.expense_date}</TableCell>
                <TableCell className="text-right">{exp.amount}</TableCell>
                <TableCell>{exp.description ?? "—"}</TableCell>
                <TableCell>
                  <Badge
                    variant={exp.status === "rejected" ? "destructive" : undefined}
                    className={exp.status === "rejected" ? undefined : STATUS_CLASS[exp.status]}
                  >
                    {exp.status}
                  </Badge>
                </TableCell>
                {canApprove && (
                  <TableCell className="text-right">
                    {exp.status === "pending" && (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => handleDecision(exp.id, "approve")}>
                          Approve
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleDecision(exp.id, "reject")}>
                          Reject
                        </Button>
                      </div>
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
