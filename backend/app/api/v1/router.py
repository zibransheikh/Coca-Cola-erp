from fastapi import APIRouter

from app.api.v1.accounting import chart_of_accounts_router, router as accounting_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.expenses import expense_categories_router, router as expenses_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.masters import (
    customers_router,
    employees_router,
    product_batches_router,
    products_router,
    routes_router,
    vehicles_router,
    warehouses_router,
)
from app.api.v1.payroll import router as payroll_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.reports import router as reports_router
from app.api.v1.trips import invoices_router, router as trips_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(warehouses_router)
api_router.include_router(products_router)
api_router.include_router(product_batches_router)
api_router.include_router(routes_router)
api_router.include_router(customers_router)
api_router.include_router(employees_router)
api_router.include_router(vehicles_router)
api_router.include_router(inventory_router)
api_router.include_router(trips_router)
api_router.include_router(invoices_router)
api_router.include_router(expense_categories_router)
api_router.include_router(expenses_router)
api_router.include_router(reports_router)
api_router.include_router(reconciliation_router)
api_router.include_router(dashboard_router)
api_router.include_router(chart_of_accounts_router)
api_router.include_router(accounting_router)
api_router.include_router(payroll_router)
