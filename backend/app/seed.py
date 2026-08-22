"""Seed default roles, permissions, chart of accounts, a default product
catalog, and an initial owner user.

Usage:
    .venv/bin/python -m app.seed --owner-email you@example.com --owner-password changeme
"""

import argparse
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import AccountType, ChartOfAccount, Permission, Role, User
from app.models.masters import Product
from app.services import accounting as acct

PERMISSIONS = [
    ("can_close_day", "Close the daily van-sales trip after reconciliation"),
    ("can_approve_credit", "Approve a customer credit sale beyond limit"),
    ("can_reconcile_payment", "Approve/reject a suggested bank reconciliation match"),
    ("can_approve_expense", "Approve a submitted expense"),
    ("can_manage_products", "Create/edit product master data"),
    ("can_manage_users", "Create/edit users and role assignments"),
    ("can_manage_masters", "Create/edit warehouses, routes, vehicles, and customers"),
    ("can_manage_inventory", "Record purchases and stock adjustments"),
    ("can_view_reports", "View reports and dashboards"),
    ("can_manage_accounting", "Manage the chart of accounts and post manual journal entries"),
    ("can_manage_payroll", "Mark attendance, record salary advances, and pay salaries"),
]

ROLES = {
    "owner": [code for code, _ in PERMISSIONS],  # full access
    "manager": [
        "can_close_day",
        "can_approve_credit",
        "can_reconcile_payment",
        "can_approve_expense",
        "can_manage_masters",
        "can_manage_inventory",
        "can_view_reports",
        "can_manage_payroll",
    ],
    "accountant": ["can_reconcile_payment", "can_view_reports", "can_manage_accounting", "can_manage_payroll"],
    "driver": [],
}

# (code, name, type, parent_code)
CHART_OF_ACCOUNTS = [
    (acct.CASH, "Cash", AccountType.asset, None),
    (acct.BANK, "Bank", AccountType.asset, None),
    (acct.ACCOUNTS_RECEIVABLE, "Accounts Receivable", AccountType.asset, None),
    (acct.INVENTORY, "Inventory", AccountType.asset, None),
    (acct.ACCOUNTS_PAYABLE, "Accounts Payable", AccountType.liability, None),
    (acct.GST_OUTPUT_TAX_PAYABLE, "GST Output Tax Payable", AccountType.liability, None),
    (acct.OWNERS_EQUITY, "Owner's Equity", AccountType.equity, None),
    (acct.SALES_REVENUE, "Sales Revenue", AccountType.income, None),
    (acct.OPERATING_EXPENSES, "Operating Expenses", AccountType.expense, None),
]

# Default product catalog: (sku, name, price per case). All sold by the
# case, so unit/gst_rate/deposit/reorder_level use the model's plain
# defaults (case / 0 / 0 / 0) rather than guessing values the source price
# list didn't specify. SKUs always end in ML/L so they can't collide with
# any earlier ad-hoc test SKUs (e.g. "COKE-300" from manual testing) that
# don't carry that suffix.
#
# NOTE: the source price list had two distinct "Soda" entries at 250ml
# (₹270 and ₹225) with nothing distinguishing them (packaging, variant,
# etc.) — both are kept, disambiguated as "Soda" and "Soda (2)", since
# there wasn't enough information to tell what actually differs between
# them. Worth confirming with the real price list if that matters.
PRODUCTS: list[tuple[str, str, int]] = [
    # 150 ML
    ("MM-APPLE-TETRA-150ML", "MM Apple Tetra 150ml", 333),
    ("MM-MANGO-150ML", "MM Mango 150ml", 333),
    ("MM-MIXED-FRUIT-150ML", "MM Mixed Fruit 150ml", 333),
    ("PEACAN-150ML", "Peacan 150ml", 264),
    # 200 ML
    ("COKE-200ML", "Coke 200ml", 200),
    ("LIMCA-200ML", "Limca 200ml", 200),
    ("FANTA-200ML", "Fanta 200ml", 200),
    ("SPRITE-200ML", "Sprite 200ml", 200),
    ("THUMSUP-200ML", "Thums Up 200ml", 200),
    ("MAAZA-200ML", "Maaza 200ml", 325),
    # 250 ML
    ("COKE-250ML", "Coke 250ml", 517),
    ("LIMCA-250ML", "Limca 250ml", 517),
    ("FANTA-250ML", "Fanta 250ml", 517),
    ("SPRITE-250ML", "Sprite 250ml", 517),
    ("THUMSUP-250ML", "Thums Up 250ml", 517),
    ("MAAZA-P-250ML", "Maaza (P) 250ml", 545),
    ("SODA-250ML", "Soda 250ml", 270),
    ("JEERA-250ML", "Jeera 250ml", 225),
    ("BLAST-250ML", "Blast 250ml", 545),
    ("TONIC-CAN-250ML", "Tonic Can 250ml", 1200),
    ("ZERO-SPRITE-250ML", "Zero Sprite 250ml", 225),
    ("SODA-2-250ML", "Soda (2) 250ml", 225),
    ("MONSTER-250ML", "Monster 250ml", 2250),
    ("MM-PULPY-ORANGE-250ML", "MM Pulpy Orange 250ml", 680),
    ("PREDATOR-PET-250ML", "Predator PET 250ml", 735),
    # 300 ML
    ("COKE-300ML", "Coke 300ml", 367),
    ("LIMCA-300ML", "Limca 300ml", 367),
    ("FANTA-300ML", "Fanta 300ml", 367),
    ("SPRITE-300ML", "Sprite 300ml", 367),
    ("THUMSUP-300ML", "Thums Up 300ml", 367),
    ("MAAZA-RGP-300ML", "Maaza RGP 300ml", 381),
    ("SODA-300ML", "Soda 300ml", 100),
    ("COKE-DIET-300ML", "Coke Diet 300ml", 880),
    # 400 ML
    ("COKE-ZERO-400ML", "Coke Zero 400ml", 432),
    # 500 ML
    ("WATER-500ML", "Water 500ml", 180),
    # 600 ML
    ("MAAZA-MANGO-600ML", "Maaza Mango 600ml", 786),
    # 750 ML
    ("COKE-750ML", "Coke 750ml", 790),
    ("LIMCA-750ML", "Limca 750ml", 790),
    ("FANTA-750ML", "Fanta 750ml", 790),
    ("SPRITE-750ML", "Sprite 750ml", 790),
    ("THUMSUP-750ML", "Thums Up 750ml", 790),
    ("SODA-750ML", "Soda 750ml", 347),
    # 1 LTR
    ("WATER-1L", "Water 1ltr", 195),
    ("MM-MANGO-1L", "MM Mango 1ltr", 830),
    ("MM-MIXED-FRUIT-1L", "MM Mixed Fruit 1ltr", 700),
    ("MM-ORANGE-1L", "MM Orange 1ltr", 700),
    ("TETRA-ORANGE-LITCHI-1L", "Tetra Orange/Litchi 1ltr", 525),
    # 1.25 LTR
    ("MAAZA-MANGO-1-25L", "Maaza Mango 1.25ltr", 956),
    ("SPRITE-1-25L", "Sprite 1.25ltr", 555),
    # 1.5 LTR
    ("SODA-1-5L", "Soda 1.5ltr", 270),
    ("SOFT-DRINK-1-5L", "Soft Drink 1.5ltr", 710),
    # 2 LTR
    ("COKE-2L", "Coke 2ltr", 852),
    ("LIMCA-2L", "Limca 2ltr", 852),
    ("FANTA-2L", "Fanta 2ltr", 852),
    ("SPRITE-2L", "Sprite 2ltr", 852),
    ("THUMSUP-2L", "Thums Up 2ltr", 852),
    ("SODA-2L", "Soda 2ltr", 288),
]


def seed(owner_email: str, owner_password: str, owner_name: str) -> None:
    db = SessionLocal()
    try:
        permission_by_code = {}
        for code, description in PERMISSIONS:
            perm = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
            if perm is None:
                perm = Permission(code=code, description=description)
                db.add(perm)
                db.flush()
            permission_by_code[code] = perm

        role_by_name = {}
        for role_name, perm_codes in ROLES.items():
            role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
            if role is None:
                role = Role(name=role_name)
                db.add(role)
                db.flush()
            role.permissions = [permission_by_code[code] for code in perm_codes]
            role_by_name[role_name] = role

        owner = db.execute(select(User).where(User.email == owner_email)).scalar_one_or_none()
        if owner is None:
            owner = User(
                email=owner_email,
                password_hash=hash_password(owner_password),
                full_name=owner_name,
            )
            db.add(owner)
            db.flush()
        owner.roles = [role_by_name["owner"]]

        accounts_by_code = {}
        for code, name, account_type, parent_code in CHART_OF_ACCOUNTS:
            account = db.execute(select(ChartOfAccount).where(ChartOfAccount.code == code)).scalar_one_or_none()
            if account is None:
                account = ChartOfAccount(
                    code=code,
                    name=name,
                    account_type=account_type,
                    parent_id=accounts_by_code[parent_code].id if parent_code else None,
                )
                db.add(account)
                db.flush()
            accounts_by_code[code] = account

        products_created = 0
        for sku, name, price_per_case in PRODUCTS:
            existing = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
            if existing is None:
                db.add(Product(sku=sku, name=name, unit="case", base_price=Decimal(price_per_case)))
                products_created += 1

        db.commit()
        print(
            f"Seeded {len(PERMISSIONS)} permissions, {len(ROLES)} roles, "
            f"{len(CHART_OF_ACCOUNTS)} chart-of-accounts entries, "
            f"{products_created} new products (of {len(PRODUCTS)} in the default catalog), "
            f"owner user '{owner_email}'."
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-email", required=True)
    parser.add_argument("--owner-password", required=True)
    parser.add_argument("--owner-name", default="Owner")
    args = parser.parse_args()
    seed(args.owner_email, args.owner_password, args.owner_name)
