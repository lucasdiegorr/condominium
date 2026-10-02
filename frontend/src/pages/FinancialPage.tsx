import { useEffect, useMemo, useState } from "react";
import { scopedApi, type BalanceSheet, type CategoryView, type InvoiceView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

type Tab = "entries" | "chart" | "invoices" | "sheet";

function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function FinancialPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.FINANCIAL_MANAGE);
  const canRead = hasPermission(perm.FINANCIAL_READ);
  const canChart = hasPermission(perm.CHART_ACCOUNTS_MANAGE);
  const canPayments = hasPermission(perm.INVOICES_MANAGE_PAYMENTS);
  const ownUnit = hasPermission(perm.FINANCIAL_READ_OWN_UNIT);

  const [tab, setTab] = useState<Tab>(canRead ? "entries" : "invoices");

  const tabs: { key: Tab; label: string; show: boolean }[] = [
    { key: "entries", label: t("financial.tab.entries"), show: canRead },
    { key: "chart", label: t("financial.tab.chart"), show: canRead },
    { key: "invoices", label: t("financial.tab.invoices"), show: canRead || ownUnit },
    { key: "sheet", label: t("financial.tab.sheet"), show: canRead || ownUnit },
  ];

  return (
    <div>
      <PageHeader title={t("financial.title")} subtitle={t("financial.subtitle")} />
      {ownUnit && !canRead ? <p className="hint">{t("financial.sheet.ownOnly")}</p> : null}
      <nav className="tabs">
        {tabs
          .filter((item) => item.show)
          .map((item) => (
            <button
              key={item.key}
              type="button"
              className={tab === item.key ? "is-active" : ""}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
      </nav>
      {tab === "entries" && canRead ? <EntriesTab canManage={canManage} /> : null}
      {tab === "chart" && canRead ? <ChartTab canChart={canChart} /> : null}
      {tab === "invoices" ? <InvoicesTab canGenerate={canManage} canPayments={canPayments} /> : null}
      {tab === "sheet" ? <SheetTab /> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Entries
// ---------------------------------------------------------------------------

function EntriesTab({ canManage }: { canManage: boolean }) {
  const entries = useScopedData(() => scopedApi.listEntries());
  const categories = useScopedData<CategoryView[]>(() => scopedApi.listCategories());

  const [date, setDate] = useState("");
  const [amount, setAmount] = useState("");
  const [kind, setKind] = useState("expense");
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const kindCategories = (categories.data ?? []).filter((cat) => cat.kind === kind);

  useEffect(() => {
    if (!kindCategories.some((cat) => String(cat.id) === categoryId)) setCategoryId("");
  }, [kind, categories.data]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit() {
    if (!categoryId) {
      setError(t("common.requiredField"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createEntry({
        date,
        amount,
        kind,
        category_id: Number(categoryId),
        description: description || null,
      });
      setDate("");
      setAmount("");
      setDescription("");
      setCategoryId("");
      entries.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      {canManage ? (
        <div className="card">
          <h3>{t("financial.addEntry")}</h3>
          <InlineForm onSubmit={() => void submit()} busy={busy} submitLabel={t("common.save")}>
            <Field label={`${t("financial.entry.date")} *`}>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </Field>
            <Field label={`${t("financial.entry.amount")} *`}>
              <input
                inputMode="decimal"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </Field>
            <Field label={t("financial.entry.kind")}>
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="expense">{t("financial.entry.kind.expense")}</option>
                <option value="income">{t("financial.entry.kind.income")}</option>
              </select>
            </Field>
            <Field label={t("financial.entry.category")}>
              <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">{t("common.none")}</option>
                {kindCategories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("financial.entry.description")}>
              <input value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
          </InlineForm>
        </div>
      ) : null}

      {entries.loading ? (
        <Loading />
      ) : entries.error ? (
        <ErrorNote>{entries.error}</ErrorNote>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("financial.entry.date")}</th>
              <th>{t("financial.entry.kind")}</th>
              <th>{t("financial.entry.category")}</th>
              <th>{t("financial.entry.amount")}</th>
              <th>{t("financial.entry.description")}</th>
              {canManage ? <th>{t("common.actions")}</th> : null}
            </tr>
          </thead>
          <tbody>
            {(entries.data ?? []).map((entry) => (
              <tr key={entry.id}>
                <td>{entry.date}</td>
                <td>
                  <span className={`badge ${entry.kind === "income" ? "ok" : ""}`}>
                    {t(`financial.entry.kind.${entry.kind}`)}
                  </span>
                </td>
                <td>{entry.category_name}</td>
                <td className="num">{entry.amount}</td>
                <td>{entry.description ?? t("common.none")}</td>
                {canManage ? (
                  <td>
                    <button
                      type="button"
                      onClick={() => {
                        if (!window.confirm(t("common.confirmDelete"))) return;
                        void scopedApi.deleteEntry(entry.id).then(entries.reload).catch((err: unknown) => setError(errorText(err)));
                      }}
                    >
                      {t("financial.deleteEntry")}
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Chart of accounts
// ---------------------------------------------------------------------------

function ChartTab({ canChart }: { canChart: boolean }) {
  const categories = useScopedData(() => scopedApi.listCategories());
  const [name, setName] = useState("");
  const [kind, setKind] = useState("expense");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createCategory({ name, kind });
      setName("");
      categories.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      {canChart ? (
        <div className="card">
          <h3>{t("financial.chart.add")}</h3>
          <InlineForm onSubmit={() => void submit()} busy={busy} submitLabel={t("common.save")}>
            <Field label={`${t("financial.chart.name")} *`}>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label={t("financial.chart.kind")}>
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="expense">{t("financial.entry.kind.expense")}</option>
                <option value="income">{t("financial.entry.kind.income")}</option>
              </select>
            </Field>
          </InlineForm>
        </div>
      ) : null}

      {categories.loading ? (
        <Loading />
      ) : categories.error ? (
        <ErrorNote>{categories.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(categories.data ?? []).map((cat) => (
            <li key={cat.id} className="card">
              <div className="row-head">
                <strong>{cat.name}</strong>
                <span className={`badge ${cat.kind === "income" ? "ok" : ""}`}>
                  {t(`financial.entry.kind.${cat.kind}`)}
                </span>
                {canChart ? (
                  <button type="button" onClick={() => setEditingId(editingId === cat.id ? null : cat.id)}>
                    {t("common.edit")}
                  </button>
                ) : null}
              </div>
              {editingId === cat.id && canChart ? (
                <CategoryEditForm cat={cat} onDone={categories.reload} />
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </section>
  );
}

function CategoryEditForm({ cat, onDone }: { cat: CategoryView; onDone: () => void }) {
  const [name, setName] = useState(cat.name);
  const [kind, setKind] = useState(cat.kind);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.updateCategory(cat.id, { name, kind });
      onDone();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <InlineForm onSubmit={() => void save()} busy={busy} submitLabel={t("common.save")}>
      <Field label={t("financial.chart.name")}>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      <Field label={t("financial.chart.kind")}>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="expense">{t("financial.entry.kind.expense")}</option>
          <option value="income">{t("financial.entry.kind.income")}</option>
        </select>
      </Field>
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </InlineForm>
  );
}

// ---------------------------------------------------------------------------
// Invoices
// ---------------------------------------------------------------------------

function InvoicesTab({ canGenerate, canPayments }: { canGenerate: boolean; canPayments: boolean }) {
  const invoices = useScopedData(() => scopedApi.listInvoices());
  const [period, setPeriod] = useState("");
  const [filter, setFilter] = useState("");
  const [payload, setPayload] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const periods = useMemo(() => {
    const set = new Set<string>();
    (invoices.data ?? []).forEach((inv) => set.add(inv.period));
    return [...set].sort().reverse();
  }, [invoices.data]);

  async function generate() {
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) {
      setError(t("financial.invoice.periodFormat"));
      return;
    }
    setGenerating(true);
    setError(null);
    setSuccess(false);
    try {
      const generated = await scopedApi.generateInvoices(period);
      setPayload(t("financial.invoice.generated", { count: generated.length, period }));
      setFilter(period);
      setSuccess(true);
      invoices.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setGenerating(false);
    }
  }

  const shown = (invoices.data ?? []).filter((inv) => !filter || inv.period === filter);

  return (
    <section>
      {canGenerate ? (
        <div className="card">
          <h3>{t("financial.invoice.generate")}</h3>
          <p className="hint">{t("financial.invoice.generateHint")}</p>
          <InlineForm onSubmit={() => void generate()} busy={generating} submitLabel={t("financial.invoice.generate")}>
            <Field label={`${t("financial.invoice.period")} *`}>
              <input
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                placeholder="2026-10"
                pattern="\d{4}-(0[1-9]|1[0-2])"
                required
              />
            </Field>
          </InlineForm>
          {success && payload ? <p className="ok-note">{payload}</p> : null}
        </div>
      ) : null}

      {periods.length > 0 ? (
        <Field label={t("financial.invoice.period")}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">{t("common.none")}</option>
            {periods.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
      ) : null}

      {invoices.loading ? (
        <Loading />
      ) : invoices.error ? (
        <ErrorNote>{invoices.error}</ErrorNote>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("financial.invoice.period")}</th>
              <th>{t("vehicles.unit")}</th>
              <th>{t("financial.invoice.dueDate")}</th>
              <th>{t("financial.invoice.amount")}</th>
              <th>{t("financial.invoice.paid")}</th>
              <th>{t("financial.invoice.status")}</th>
              {canPayments ? <th>{t("common.actions")}</th> : null}
            </tr>
          </thead>
          <tbody>
            {shown.map((invoice) => (
              <InvoiceRow key={invoice.id} invoice={invoice} canPayments={canPayments} onPay={invoices.reload} />
            ))}
          </tbody>
        </table>
      )}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </section>
  );
}

function InvoiceRow({
  invoice,
  canPayments,
  onPay,
}: {
  invoice: InvoiceView;
  canPayments: boolean;
  onPay: () => void;
}) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pay() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.recordPayment(invoice.id, { amount });
      setAmount("");
      onPay();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const statusLabel = t(`financial.invoice.status.${invoice.status}`) ?? invoice.status;

  return (
    <tr>
      <td>{invoice.period}</td>
      <td>{invoice.unit_code}</td>
      <td>{invoice.due_date}</td>
      <td className="num">{invoice.amount}</td>
      <td className="num">{invoice.paid}</td>
      <td>
        <span className={`badge ${invoice.status === "paid" ? "ok" : invoice.status === "overdue" ? "warn" : ""}`}>
          {statusLabel}
        </span>
      </td>
      {canPayments ? (
        <td>
          <InlineForm onSubmit={() => void pay()} busy={busy} submitLabel={t("financial.invoice.recordPayment")}>
            <input
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={t("financial.invoice.paymentAmount")}
              required
            />
          </InlineForm>
          {error ? <ErrorNote>{error}</ErrorNote> : null}
        </td>
      ) : null}
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Balance sheet
// ---------------------------------------------------------------------------

function SheetTab() {
  const [period, setPeriod] = useState(currentPeriod());
  const sheet = useScopedData<BalanceSheet>(() => scopedApi.balanceSheet(period), [period]);

  return (
    <section>
      <InlineForm
        onSubmit={() => sheet.reload()}
        busy={sheet.loading}
        submitLabel={t("common.save")}
      >
        <Field label={`${t("financial.invoice.period")} *`}>
          <input
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            placeholder="2026-10"
            pattern="\d{4}-(0[1-9]|1[0-2])"
            required
          />
        </Field>
      </InlineForm>
      {sheet.loading ? (
        <Loading />
      ) : sheet.error ? (
        <ErrorNote>{sheet.error}</ErrorNote>
      ) : sheet.data ? (
        <div className="sheet-grid">
          <CategoryTable title={t("financial.sheet.expensesByCategory")} rows={sheet.data.expenses_by_category} />
          <CategoryTable title={t("financial.sheet.incomesByCategory")} rows={sheet.data.incomes_by_category} />
          <div className="card result-card">
            <strong>{t("financial.sheet.result")}</strong>
            <span className="num">{sheet.data.result}</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("vehicles.unit")}</th>
                <th>{t("financial.sheet.billed")}</th>
                <th>{t("financial.sheet.paid")}</th>
                <th>{t("financial.sheet.pending")}</th>
                <th>{t("financial.sheet.delinquent")}</th>
              </tr>
            </thead>
            <tbody>
              {sheet.data.per_unit.map((unit) => (
                <tr key={unit.unit_id}>
                  <td>{unit.unit_code}</td>
                  <td className="num">{unit.billed}</td>
                  <td className="num">{unit.paid}</td>
                  <td className="num">{unit.pending}</td>
                  <td className="num">{unit.delinquent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function CategoryTable({ title, rows }: { title: string; rows: { category: string; amount: string }[] }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="muted">{t("common.none")}</p>
      ) : (
        <table className="data-table">
          <tbody>
            {rows.map((row) => (
              <tr key={row.category}>
                <td>{row.category}</td>
                <td className="num">{row.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
