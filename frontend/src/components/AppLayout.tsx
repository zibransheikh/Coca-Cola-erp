import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/trips", label: "Trips" },
  { to: "/inventory", label: "Inventory" },
  { to: "/expenses", label: "Expenses" },
  { to: "/reconciliation", label: "Reconciliation" },
  { to: "/accounting", label: "Accounting" },
  { to: "/reports", label: "Reports" },
  { to: "/products", label: "Products" },
  { to: "/customers", label: "Customers" },
  { to: "/vehicles", label: "Vehicles" },
  { to: "/routes", label: "Routes" },
  { to: "/warehouses", label: "Warehouses" },
  { to: "/employees", label: "Employees" },
  { to: "/payroll", label: "Payroll" },
  { to: "/expense-categories", label: "Expense Categories" },
  { to: "/chart-of-accounts", label: "Chart of Accounts" },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-svh bg-muted/40">
      <aside className="fixed inset-y-0 left-0 w-56 shrink-0 overflow-y-auto border-r bg-background">
        <div className="border-b px-4 py-4">
          <span className="font-semibold text-primary">DMS</span>
        </div>
        <nav className="flex flex-col gap-1 p-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col pl-56">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-6 py-4">
          <div />
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">{user?.full_name}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
