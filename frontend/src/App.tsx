import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ProductsPage } from "@/pages/ProductsPage";
import { CustomersPage } from "@/pages/CustomersPage";
import { VehiclesPage } from "@/pages/VehiclesPage";
import { RoutesPage } from "@/pages/RoutesPage";
import { WarehousesPage } from "@/pages/WarehousesPage";
import { EmployeesPage } from "@/pages/EmployeesPage";
import { InventoryPage } from "@/pages/InventoryPage";
import { TripsPage } from "@/pages/TripsPage";
import { TripDetailPage } from "@/pages/TripDetailPage";
import { ExpensesPage } from "@/pages/ExpensesPage";
import { ExpenseCategoriesPage } from "@/pages/ExpenseCategoriesPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { ReconciliationPage } from "@/pages/ReconciliationPage";
import { AccountingPage } from "@/pages/AccountingPage";
import { ChartOfAccountsPage } from "@/pages/ChartOfAccountsPage";
import { PayrollPage } from "@/pages/PayrollPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/trips" element={<TripsPage />} />
            <Route path="/trips/:tripId" element={<TripDetailPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/expenses" element={<ExpensesPage />} />
            <Route path="/expense-categories" element={<ExpenseCategoriesPage />} />
            <Route path="/reconciliation" element={<ReconciliationPage />} />
            <Route path="/accounting" element={<AccountingPage />} />
            <Route path="/chart-of-accounts" element={<ChartOfAccountsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/customers" element={<CustomersPage />} />
            <Route path="/vehicles" element={<VehiclesPage />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/warehouses" element={<WarehousesPage />} />
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/payroll" element={<PayrollPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
