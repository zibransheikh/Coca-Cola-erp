# Distributor Management System (DMS) + AI Platform
# Complete Project Requirements & Build Plan

**Version:** 2.0
**Document Type:** User Requirements & Technical Planning Document

---

# Table of Contents

1. Vision
2. Core Business Workflow
3. Business Modules
4. Functional Requirements
5. Payment Reconciliation System
6. System Architecture
7. Engineering Principles
8. AI Strategy
9. Database Design
10. Application Workflow
11. Screen-by-Screen Requirements
12. Reports
13. Security
14. Build Roadmap
15. Future Enhancements

---

# 1. Vision

The Distributor Management System (DMS) is an ERP platform designed specifically for FMCG distribution agencies such as Coca-Cola distributors, dairy distributors, beverage distributors and similar businesses.

The objective is to digitize every operational activity of the business while minimizing manual work, reducing fraud, improving stock visibility and simplifying accounting.

Unlike generic ERPs, this system is centered around the **Van Sales / Direct Store Delivery (DSD)** workflow.

The platform manages:

- Warehouse inventory
- Vehicle load-out
- Daily sales
- Customer credits
- Collections
- Online payment reconciliation
- Expenses
- Labour
- Reports
- AI-driven analytics

The system belongs entirely to the distributor and does not replace Coca-Cola's internal systems.

---

# 2. Core Business Workflow

The entire ERP revolves around one daily operational loop.

```
Warehouse

↓

Load Vehicle

↓

Vehicle Leaves

↓

Visit Shops

↓

Sales

↓

Cash Collection

↓

Online Collection

↓

Credit Given

↓

Vehicle Returns

↓

Stock Count

↓

Cash Submission

↓

Bank Reconciliation

↓

Manager Approval

↓

Day Closed
```

Everything inside the ERP supports this workflow.

---

# 3. Daily Reconciliation Rule

The most important rule inside the ERP is

```
Loaded Stock

=

Sold

+

Returned

+

Damaged

+

Missing
```

Where

Sold is **never manually entered**.

Instead it is calculated from invoices.

Likewise,

```
Sales Value

=

Cash Collected

+

Online Collections

+

Credit Given
```

If any mismatch exists

The day cannot be closed until approved by an authorized manager.

---

# 4. Business Modules

## 4.1 Inventory & Warehouse

Responsible for warehouse inventory.

Features

- Stock Ledger
- Batch Management
- Expiry Tracking
- FEFO Picking
- Stock Adjustment
- Damaged Stock
- Near Expiry Alerts
- Purchase Entry
- Stock Transfers

---

## 4.2 Empties & Returnables

Tracks

- Empty Crates
- Empty Bottles
- Deposit Amount
- Full for Empty Exchange
- Outstanding Returnables

---

## 4.3 Vehicles & Route Management

Responsible for daily vehicle operations.

Features

- Vehicle Registration
- Driver Assignment
- Route Assignment
- Daily Load-Out
- Vehicle Stock
- Vehicle History
- Vehicle Expenses
- Fuel
- Maintenance

---

## 4.4 Van Sales

Handles

Morning Load

↓

Sales

↓

Returns

↓

Damages

↓

Day Close

Every invoice generated automatically updates

- Inventory
- Customer Ledger
- Accounting
- Reports

---

## 4.5 Customers

Stores

- Shop Details
- Owner Details
- Phone Numbers
- Address
- GST
- Credit Limit
- Outstanding Balance
- Purchase History
- Route Assignment

---

## 4.6 Credit Management

Features

- Credit Sales
- Credit Limits
- Outstanding Amount
- Collections
- Aging Reports
- Overdue Alerts

---

# 5. Collections & Payment Reconciliation (NEW)

This module eliminates manual reconciliation between bank statements and customer credits.

---

## Problem Statement

Current Workflow

Driver visits shop.

Customer pays online.

Driver records

```
ABC Stores

Paid Online

₹4,500
```

At the end of the day,

Owner downloads bank statement.

Bank statement shows

```
MOHAMMED SHAFI

₹4500
```

ERP stores

```
ABC Stores
```

Only the owner knows

```
MOHAMMED SHAFI

=

ABC Stores
```

The owner manually clears the payment.

This becomes extremely time-consuming as the business grows.

---

# Objectives

Automatically reconcile

Incoming Bank Transactions

↓

Pending Shop Credits

without requiring drivers to collect timestamps or bank account numbers.

---

## Driver Workflow

Driver only records

- Shop Name
- Amount
- Payment Mode

Payment Mode

- Cash
- Credit
- Online

For online payments

Status becomes

```
Awaiting Bank Verification
```

Nothing extra is required from the driver.

---

## Bank Statement Import

Supported formats

- PDF
- Excel
- CSV

System extracts

- Incoming Credits
- Account Holder Name
- Amount
- Transaction Reference
- Narration (if available)

Outgoing transactions

- Fuel
- Salary
- Vendor Payments
- Charges

are ignored.

---

# Intelligent Reconciliation Engine

The engine compares

Pending Online Payments

with

Incoming Bank Credits.

Matching uses

- Previously Verified Account Holder
- Amount
- Outstanding Balance
- Customer Payment History
- Fuzzy Name Matching
- Transaction Narration
- UPI ID (if available)
- Reference Number (if available)

---

# Confidence Levels

### Above 95%

Automatically Clear Payment

---

### 80–95%

Suggest Match

Owner approves.

---

### Below 80%

Remain Unmatched.

---

# Learning System

Example

Owner confirms

```
MOHAMMED SHAFI

↓

ABC Stores
```

System permanently stores

```
Verified Payment Identity

MOHAMMED SHAFI

↓

ABC Stores
```

Future payments become automatic.

---

# Multiple Payment Identities

One customer may use

- Personal Account
- Wife's Account
- Business Account
- Different UPI IDs

Therefore

One Shop

↓

Many Payment Identities

Example

ABC Stores

Verified Identities

- Mohammed Shafi
- Mohd Shafi
- SHAFI TRADERS
- shafi@okaxis
- shafi@ybl

---

# Reconciliation Dashboard

Sections

### Automatically Matched

Displays

- Shop
- Amount
- Transaction

---

### Suggested Matches

Shows

- Bank Name
- Suggested Shop
- Confidence
- Approve Button
- Reject Button

---

### Unmatched Transactions

Displays

Transactions requiring manual review.

---

# Audit Trail

Every reconciliation stores

- Who approved
- Date
- Previous Status
- New Status
- Confidence Score

Nothing can be silently changed.

---

# 6. Accounting

Features

- GST Invoice
- Credit Note
- Debit Note
- Journal Entries
- Customer Ledger
- Cash Ledger
- Bank Ledger
- General Ledger
- Trial Balance
- Profit & Loss
- Balance Sheet

Invoices are immutable.

No delete operation exists.

---

# 7. Expenses

Track

Vehicle

- Fuel
- Service
- Tyres
- Repairs

Business

- Rent
- Electricity
- Office
- Labour
- Miscellaneous

Approval Workflow included.

---

# 8. Labour & Payroll

Each worker has

- Joining Date
- Salary
- Advances
- Attendance
- Pending Salary
- Payment History
- Notes

---

# 9. Dashboard

Cards

- Today's Sales
- Cash Collection
- Online Collection
- Pending Credits
- Outstanding Collections
- Vehicles on Route
- Warehouse Stock
- Near Expiry Products
- Best Selling Products
- Low Stock
- Daily Expenses
- Profit Today

Graphs

- Daily Sales
- Weekly Sales
- Monthly Sales
- Collection Trends
- Credit Trends

---

# 10. Reports

Inventory

- Stock Report
- Expiry Report
- Vehicle Stock
- Damage Report

Sales

- Sales by Driver
- Sales by Route
- Sales by Product
- Sales by Shop

Collections

- Cash Collection
- Online Collection
- Pending Credits
- Aging Report
- Reconciliation Report

Finance

- P&L
- Balance Sheet
- Expense Report

Labour

- Salary Report
- Advances
- Pending Salary

Export

- Excel
- PDF

---

# 11. AI Strategy

The system introduces AI gradually.

---

## Phase 1

Deterministic Analytics

- SQL Reports
- KPIs
- Dashboards

---

## Phase 2

Intelligent Reconciliation

- Bank Statement Reading
- Customer Matching
- Learned Payment Mapping

---

## Phase 3

Business Assistant

Read-only AI Chatbot

Examples

"What were today's sales?"

"Which customers have overdue payments?"

"Which products are nearly out of stock?"

The chatbot never writes to the database.

---

## Phase 4

Forecasting

Demand Prediction

Sales Forecast

Inventory Forecast

Seasonality

---

## Phase 5

Advanced AI

- Credit Risk Prediction
- Route Optimization
- Customer Segmentation
- Smart Ordering
- Inventory Optimization
- Business Insights

---

# 12. Technology Stack

Backend

FastAPI

SQLAlchemy

PostgreSQL

Redis

Celery

Frontend

React

TypeScript

TailwindCSS

shadcn/ui

Authentication

JWT

RBAC

Refresh Tokens

Reports

Pandas

OpenPyXL

ReportLab

Deployment

Docker

Nginx

CI/CD

Alembic

Sentry

---

# 13. Engineering Principles

Inventory

Append-only Stock Ledger

Money

Decimal only

Never Float

Invoices

Immutable

Permissions

Action Based

Example

```
can_close_day

can_approve_credit

can_reconcile_payment
```

Audit Log

Every important action recorded.

---

# 14. Suggested Database Modules

Master Tables

- Customers
- Drivers
- Vehicles
- Products
- Routes
- Employees

Operational Tables

- Stock Ledger
- Vehicle Loads
- Sales Invoices
- Returns
- Damages
- Expenses

Finance

- Customer Ledger
- Credit Ledger
- Cash Ledger
- Bank Ledger

Collections

- Pending Online Payments
- Imported Bank Statements
- Bank Transactions
- Payment Reconciliation
- Payment Identity Mapping

AI

- AI Conversations
- Forecast Results
- Reconciliation Confidence
- Learning History

---

# 15. Application Workflow

## Dashboard

↓

Vehicles

↓

Sales

↓

Credits

↓

Expenses

↓

Reports

↓

AI Assistant

---

## Vehicle Workflow

Create Trip

↓

Load Stock

↓

Driver Leaves

↓

Sales

↓

Returns

↓

Cash Entry

↓

Online Collections

↓

Credit Entries

↓

Vehicle Returns

↓

Stock Count

↓

Manager Verification

↓

Day Closed

---

## Credit Workflow

Create Credit

↓

Outstanding

↓

Payment Received

↓

Cash

OR

Online

↓

If Cash

↓

Immediately Cleared

↓

If Online

↓

Awaiting Verification

↓

Upload Bank Statement

↓

Automatic Reconciliation

↓

Owner Review (if needed)

↓

Credit Cleared

---

# 16. Security

- JWT Authentication
- Role Based Access
- Audit Logging
- Immutable Financial Records
- Daily Backups
- Encrypted Passwords
- Secure APIs
- Rate Limiting
- Transaction Rollbacks

---

# 17. Build Roadmap

## Phase 0

Foundation

- Authentication
- Roles
- Database
- Audit
- Deployment

---

## Phase 1

Core ERP

- Inventory
- Vehicles
- Sales
- Customers
- Credits
- Expenses
- Reports

---

## Phase 2

Finance

- Accounting
- Collections
- Online Payment Tracking
- Bank Statement Import
- Intelligent Payment Reconciliation
- Payment Mapping
- Collection Dashboard

---

## Phase 3

Analytics

- Business Dashboards
- AI Reports
- Read-only Chatbot

---

## Phase 4

Machine Learning

- Forecasting
- Credit Risk
- Route Optimization
- Inventory Prediction

---

# 18. Future Enhancements

- Mobile App for Drivers
- Barcode Scanning
- QR Invoice Payment
- WhatsApp Invoice Sharing
- GPS Route Tracking
- Digital Signatures
- Customer Portal
- Supplier Portal
- Automatic Bank API Integration (instead of manual statement upload)
- OCR for Invoice Scanning
- Voice-based AI Assistant
- Predictive Business Alerts

---

# Final Vision

The final platform is not merely an inventory management system—it is a comprehensive Distributor ERP designed for FMCG operations. It combines warehouse management, van sales, accounting, customer credit management, intelligent bank reconciliation, operational reporting, and AI-driven decision support into a single integrated system. The architecture is modular and scalable, enabling future capabilities such as real-time bank integrations, predictive analytics, route optimization, and autonomous business insights without requiring major redesigns.
