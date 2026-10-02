## Purpose

Controls the condominium's finances: chart of accounts, expense and income entries, allocation by ideal fraction, per-unit invoices, payment recording and balance sheet, without executing charges.

## ADDED Requirements

### Requirement: Chart of accounts per condominium

The system SHALL keep a category catalog configurable per condominium, classified as expense or income (for example: maintenance, security, cleaning, workers, extra fees).

#### Scenario: Expense category creation
- **WHEN** the síndico creates the category "maintenance" classified as expense
- **THEN** the category becomes available for entries of that condominium

### Requirement: Expense and income entries

The system SHALL register financial entries (date, amount, category, description) for expenses and incomes, always scoped to a condominium.

#### Scenario: Expense entry
- **WHEN** the síndico records a maintenance expense
- **THEN** the entry is recorded as an expense in the condominium

#### Scenario: Income entry
- **WHEN** the síndico records an income, such as an extra fee
- **THEN** the entry is recorded as income/credit in the condominium

### Requirement: Allocation by ideal fraction

The system SHALL allocate the condominium's expenses among units proportionally to each unit's ideal fraction.

#### Scenario: Proportional allocation
- **WHEN** an expense is recorded and the allocation is calculated
- **THEN** each unit receives a debit proportional to its ideal fraction

### Requirement: Invoice per unit

The system SHALL generate monthly invoices per unit reflecting the expenses allocation and the period's incomes/credits.

#### Scenario: Monthly invoice generation
- **WHEN** the period closes with allocated expenses and applied credits
- **THEN** each unit has an invoice with the period's due amount

### Requirement: Manual payment recording

The system SHALL manually record invoice payments, keeping per-unit status among paid, pending and overdue.

#### Scenario: Payment settlement
- **WHEN** the síndico or administrator records the payment of an invoice
- **THEN** the invoice status becomes paid

#### Scenario: Overdue invoice
- **WHEN** a pending invoice passes the due date without payment
- **THEN** its status becomes overdue

### Requirement: Balance sheet

The system SHALL present the period balance sheet consolidating expenses and incomes per category, the period result and a per-unit summary (billing and delinquency).

#### Scenario: Balance sheet consultation
- **WHEN** the síndico or administrator consults the balance sheet of a period
- **THEN** the system displays expenses, incomes, result and a per-unit summary

#### Scenario: Resident sees only their own unit
- **WHEN** a condômino or inquilino consults financial data
- **THEN** the system displays only the financial information of their own unit

### Requirement: No charge execution

The system SHALL only keep financial information and entries and SHALL NOT issue bank slips or PIX, nor integrate with payment channels in this version.

#### Scenario: No charge integration triggered
- **WHEN** an entry or invoice is created
- **THEN** no external charge integration is triggered
