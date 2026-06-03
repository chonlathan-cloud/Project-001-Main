import React, { useEffect, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getDashboardData } from './api';
import Loading from './components/Loading';
import DashboardCashflowCard from './components/DashboardCashflowCard';
import DashboardHeroSummary from './components/DashboardHeroSummary';
import DashboardKpiCard from './components/DashboardKpiCard';
import DashboardPanel from './components/DashboardPanel';

const currencyFormatter = new Intl.NumberFormat('th-TH', {
  style: 'currency',
  currency: 'THB',
  maximumFractionDigits: 0,
});

const numberFormatter = new Intl.NumberFormat('th-TH');

const percentFormatter = new Intl.NumberFormat('th-TH', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const toneStyles = {
  neutral: {
    background: '#ffffff',
    border: '#e7e0d4',
    text: '#2f2e2c',
    subtle: 'rgba(47, 46, 44, 0.6)',
    accent: '#c2a878',
    soft: 'rgba(194, 168, 120, 0.14)',
  },
  positive: {
    background: '#ffffff',
    border: '#e7e0d4',
    text: '#166534',
    subtle: 'rgba(47, 46, 44, 0.6)',
    accent: '#4f6f64',
    soft: 'rgba(79, 111, 100, 0.12)',
  },
  warning: {
    background: '#ffffff',
    border: '#e7e0d4',
    text: '#9a6700',
    subtle: 'rgba(47, 46, 44, 0.6)',
    accent: '#c2a878',
    soft: 'rgba(194, 168, 120, 0.16)',
  },
  danger: {
    background: '#ffffff',
    border: '#e7e0d4',
    text: '#9f1239',
    subtle: 'rgba(47, 46, 44, 0.6)',
    accent: '#de5b52',
    soft: 'rgba(222, 91, 82, 0.12)',
  },
};

const chartTooltipStyle = {
  borderRadius: '14px',
  border: '1px solid #e5e7eb',
  boxShadow: '0 18px 40px rgba(15, 23, 42, 0.08)',
};

function formatMetric(value, kind) {
  if (kind === 'currency') {
    return currencyFormatter.format(Number(value || 0));
  }

  if (kind === 'percent') {
    return `${percentFormatter.format(Number(value || 0))}%`;
  }

  return numberFormatter.format(Number(value || 0));
}

function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return parsed.toLocaleString('th-TH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getMaxCashflowItem(items, key) {
  if (!items.length) return null;
  return items.reduce((winner, item) => (
    Number(item?.[key] || 0) > Number(winner?.[key] || 0) ? item : winner
  ), items[0]);
}

function getCashflowInsightTone(value) {
  const amount = Number(value || 0);
  if (amount < 0) return 'danger';
  if (amount > 0) return 'positive';
  return 'neutral';
}

function BudgetRow({ item }) {
  const tone = toneStyles[item.tone] || toneStyles.neutral;

  return (
    <div
      className="dashboard-budget-row"
      style={{
        '--row-accent': tone.accent,
        '--row-bg': tone.soft,
        '--row-text': tone.text,
      }}
    >
      <div className="dashboard-budget-row-head">
        <span>{item.label}</span>
        <strong>{formatMetric(item.value, 'currency')}</strong>
      </div>

      <div className="dashboard-budget-track">
        <div
          style={{
            width: `${Math.max(0, Math.min(Number(item.ratio || 0), 100))}%`,
          }}
        />
      </div>

      <div className="dashboard-budget-note">
        {percentFormatter.format(Number(item.ratio || 0))}% ของงบรวม
      </div>
    </div>
  );
}

function AttentionItem({ item }) {
  const tone = toneStyles[item.tone] || toneStyles.neutral;

  return (
    <div
      className="dashboard-attention-row"
      style={{
        '--row-accent': tone.accent,
        '--row-bg': tone.soft,
        '--row-text': tone.text,
      }}
    >
      <div className="dashboard-attention-row-head">
        <span>{item.label}</span>
        <strong>{formatMetric(item.value, item.kind)}</strong>
      </div>
      <p>{item.description}</p>
    </div>
  );
}

function RiskProjectRow({ item, index, maxAmount }) {
  const overdueAmount = Number(item?.overdueAmount || 0);
  const pendingAmount = Number(item?.pendingRequestAmount || 0);
  const totalAmount = Number(item?.totalRiskAmount || overdueAmount + pendingAmount);
  const totalWidth = maxAmount > 0 ? Math.max(5, Math.min(100, (totalAmount / maxAmount) * 100)) : 0;
  const overdueWidth = totalAmount > 0 ? (overdueAmount / totalAmount) * 100 : 0;
  const pendingWidth = totalAmount > 0 ? (pendingAmount / totalAmount) * 100 : 0;
  const severity = overdueAmount > 0 ? 'critical' : 'watch';

  return (
    <article className={`dashboard-risk-row dashboard-risk-row-${severity}`}>
      <div className="dashboard-risk-rank">{index + 1}</div>

      <div className="dashboard-risk-body">
        <div className="dashboard-risk-row-head">
          <div className="dashboard-risk-project">
            <strong title={item.name}>{item.name || 'Unknown project'}</strong>
            <span>
              {formatMetric(item.overdueCount, 'number')} overdue · {formatMetric(item.pendingRequestCount, 'number')} pending
            </span>
          </div>

          <div className="dashboard-risk-total">
            <strong>{formatMetric(totalAmount, 'currency')}</strong>
            <span>{severity === 'critical' ? 'Critical exposure' : 'Admin queue'}</span>
          </div>
        </div>

        <div className="dashboard-risk-track" aria-label={`${item.name} risk amount`}>
          <div className="dashboard-risk-track-fill" style={{ width: `${totalWidth}%` }}>
            {overdueAmount > 0 ? (
              <span className="overdue" style={{ width: `${overdueWidth}%` }} />
            ) : null}
            {pendingAmount > 0 ? (
              <span className="pending" style={{ width: `${pendingWidth}%` }} />
            ) : null}
          </div>
        </div>

        <div className="dashboard-risk-breakdown">
          <span>
            <i className="overdue" />
            Overdue {formatMetric(overdueAmount, 'currency')}
          </span>
          <span>
            <i className="pending" />
            Pending {formatMetric(pendingAmount, 'currency')}
          </span>
        </div>
      </div>
    </article>
  );
}

function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const result = await getDashboardData();
        setData(result);
      } catch (loadError) {
        setError(loadError.message || 'Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {error}
      </div>
    );
  }

  const latestMonth = data?.cashflow?.[data.cashflow.length - 1] || null;
  const cashflowRows = Array.isArray(data?.cashflow) ? data.cashflow : [];
  const strongestIncomeMonth = getMaxCashflowItem(cashflowRows, 'income');
  const highestExpenseMonth = getMaxCashflowItem(cashflowRows, 'expense');
  const positiveCashflowMonths = cashflowRows.filter((item) => Number(item?.balance || 0) > 0).length;
  const maxCashflowAmount = Math.max(
    ...cashflowRows.flatMap((item) => [
      Math.abs(Number(item?.income || 0)),
      Math.abs(Number(item?.expense || 0)),
      Math.abs(Number(item?.balance || 0)),
    ]),
    1
  );
  const cashflowInsights = [
    {
      key: 'income-peak',
      label: 'Strongest income',
      value: strongestIncomeMonth?.month || '-',
      detail: formatMetric(strongestIncomeMonth?.income || 0, 'currency'),
      tone: 'positive',
    },
    {
      key: 'expense-peak',
      label: 'Highest expense',
      value: highestExpenseMonth?.month || '-',
      detail: formatMetric(highestExpenseMonth?.expense || 0, 'currency'),
      tone: 'warning',
    },
    {
      key: 'positive-months',
      label: 'Positive months',
      value: `${positiveCashflowMonths}/${cashflowRows.length || 0}`,
      detail: `Net ${formatMetric(data?.kpis?.netCashflow, 'currency')}`,
      tone: getCashflowInsightTone(data?.kpis?.netCashflow),
    },
  ];
  const riskyRows = Array.isArray(data?.riskyProjects) ? data.riskyProjects : [];
  const maxRiskAmount = Math.max(
    ...riskyRows.map((item) => Number(item?.totalRiskAmount || 0)),
    1
  );
  const riskOverdueTotal = riskyRows.reduce((sum, item) => sum + Number(item?.overdueAmount || 0), 0);
  const riskPendingTotal = riskyRows.reduce((sum, item) => sum + Number(item?.pendingRequestAmount || 0), 0);
  const topRiskProject = riskyRows[0] || null;
  const utilizationTone = (data?.kpis?.budgetUtilization || 0) > 85 ? toneStyles.warning : toneStyles.positive;
  const cashflowIsNegative = (data?.kpis?.netCashflow || 0) < 0;
  const balanceTolerance = Math.max(
    Math.abs(data?.kpis?.totalIncome || 0),
    Math.abs(data?.kpis?.totalExpense || 0),
    1
  ) * 0.03;
  const cashflowBalanceText = Math.abs(data?.kpis?.netCashflow || 0) <= balanceTolerance
    ? 'Balanced'
    : cashflowIsNegative
      ? 'Deficit'
      : 'Surplus';
  const visibleStatCards = (data?.statCards || []).filter(
    (card) => card?.key !== 'profit-margin' && card?.key !== 'profitMargin' && card?.label !== 'Profit Margin'
  );
  const dashboardStatCards = visibleStatCards.map((card) => {
    if (card.key === 'actual-cost') {
      return {
        ...card,
        badge: (data?.kpis?.budgetUtilization || 0) > 85 ? 'Watch' : 'Healthy',
        progress: data?.kpis?.budgetUtilization,
        progressLabel: 'Budget used',
      };
    }

    if (card.key === 'pending-approvals') {
      const pendingCount = Number(data?.kpis?.pendingApprovalCount || 0);
      return {
        ...card,
        badge: pendingCount > 0 ? 'Action' : 'Clear',
        progress: pendingCount > 0 ? Math.min((pendingCount / Math.max(pendingCount, 8)) * 100, 100) : 0,
        progressLabel: 'Approval load',
      };
    }

    if (card.key === 'total-budget') {
      return {
        ...card,
        badge: 'Portfolio',
      };
    }

    return card;
  });
  const portfolioSignals = [
    {
      title: 'Budget room',
      value: formatMetric(data?.kpis?.remainingBudget, 'currency'),
      detail: `จากงบรวม ${formatMetric(data?.kpis?.totalBudget, 'currency')}`,
      tone: (data?.kpis?.remainingBudget || 0) < 0 ? 'danger' : 'positive',
    },
    {
      title: 'Cashflow state',
      value: cashflowBalanceText,
      detail: `Balance ${formatMetric(data?.kpis?.netCashflow, 'currency')}`,
      tone: cashflowIsNegative ? 'danger' : 'positive',
    },
    {
      title: 'Blocked work',
      value: formatMetric(data?.kpis?.pendingApprovalCount, 'number'),
      detail: `ยอดค้างชำระ ${formatMetric(data?.kpis?.overdueAmount, 'currency')}`,
      tone: (data?.kpis?.pendingApprovalCount || 0) > 0 ? 'warning' : 'positive',
    },
  ];

  return (
    <div className="dashboard-page">
      <DashboardHeroSummary
        balance={data?.kpis?.netCashflow}
        budgetUtilization={data?.kpis?.budgetUtilization}
        cashflowLabel={cashflowBalanceText}
        latestMonth={latestMonth?.month}
        pendingApprovals={data?.kpis?.pendingApprovalCount}
        totalBudget={data?.kpis?.totalBudget}
        formatCurrency={(value) => formatMetric(value, 'currency')}
        formatPercent={(value) => formatMetric(value, 'percent')}
        formatNumber={(value) => formatMetric(value, 'number')}
      />

      <section className="dashboard-kpi-grid">
        <DashboardCashflowCard
          balance={data?.kpis?.netCashflow}
          totalIncome={data?.kpis?.totalIncome}
          totalExpense={data?.kpis?.totalExpense}
          cashflow={data?.cashflow}
          latestMonth={latestMonth?.month}
          formatCurrency={(value) => formatMetric(value, 'currency')}
        />
        {dashboardStatCards.map((card) => (
          <DashboardKpiCard key={card.key} card={card} formatMetric={formatMetric} />
        ))}
      </section>

      <section className="dashboard-main-grid dashboard-flow-grid">
        <div className="dashboard-primary-stack">
          <DashboardPanel
            title="Monthly Cashflow"
            description="เปรียบเทียบรายรับจาก installments กับรายจ่ายที่อนุมัติแล้วในแต่ละเดือน"
            action={<span className="dashboard-panel-pill">Income / Expense / Balance</span>}
            className="dashboard-chart-panel"
          >
          <div className="dashboard-chart-height">
            {data?.cashflow?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.cashflow} margin={{ top: 18, right: 20, left: 0, bottom: 6 }}>
                  <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="month"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    tickFormatter={(value) => `${Math.round(Number(value || 0) / 1000)}k`}
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      formatMetric(value, 'currency'),
                      name === 'income' ? 'Income' : name === 'expense' ? 'Expense' : 'Balance',
                    ]}
                    labelStyle={{ color: '#111827', fontWeight: 700 }}
                    contentStyle={chartTooltipStyle}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    iconType="circle"
                    wrapperStyle={{ fontSize: '12px', color: '#6b7280', paddingBottom: '12px' }}
                    formatter={(value) => (value === 'income' ? 'Income' : value === 'expense' ? 'Expense' : 'Balance')}
                  />
                  <Bar dataKey="income" name="income" fill="#4f6f64" radius={[8, 8, 0, 0]} barSize={24} />
                  <Bar dataKey="expense" name="expense" fill="#c2a878" radius={[8, 8, 0, 0]} barSize={18} />
                  <Line
                    type="monotone"
                    dataKey="balance"
                    name="balance"
                    stroke="#2f2e2c"
                    strokeWidth={3}
                    dot={{ r: 4, strokeWidth: 0, fill: '#2f2e2c' }}
                    activeDot={{ r: 6, strokeWidth: 2, stroke: '#ffffff', fill: '#2f2e2c' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="dashboard-empty-state">ยังไม่มีข้อมูล cashflow สำหรับแสดงผล</div>
            )}
          </div>

          {cashflowRows.length ? (
            <>
              <div className="dashboard-cashflow-insight-grid">
                {cashflowInsights.map((item) => (
                  <article key={item.key} className={`dashboard-cashflow-insight dashboard-cashflow-insight-${item.tone}`}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                    <p>{item.detail}</p>
                  </article>
                ))}
              </div>

              <div className="dashboard-cashflow-month-strip" aria-label="Monthly cashflow quick scan">
                {cashflowRows.map((item) => {
                  const balance = Number(item?.balance || 0);
                  const incomeWidth = Math.max(6, Math.min(100, (Math.abs(Number(item?.income || 0)) / maxCashflowAmount) * 100));
                  const expenseWidth = Math.max(6, Math.min(100, (Math.abs(Number(item?.expense || 0)) / maxCashflowAmount) * 100));

                  return (
                    <div key={item.month} className="dashboard-cashflow-month">
                      <div className="dashboard-cashflow-month-label">
                        <span>{item.month}</span>
                        <strong className={balance < 0 ? 'is-negative' : 'is-positive'}>
                          {formatMetric(balance, 'currency')}
                        </strong>
                      </div>
                      <div className="dashboard-cashflow-mini-bars">
                        <div className="income" style={{ width: `${incomeWidth}%` }} />
                        <div className="expense" style={{ width: `${expenseWidth}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : null}
          </DashboardPanel>

          <DashboardPanel
            title="Top Risky Projects"
            description="เรียงตามยอดค้างชำระรวมกับยอด input request ที่ยังรอ Pending Admin"
            action={<span className="dashboard-panel-pill">Top 5 by risk amount</span>}
            className="dashboard-chart-panel"
          >
            <div className="dashboard-risk-board">
              {riskyRows.length ? (
                <>
                  <div className="dashboard-risk-summary-grid">
                    <div className="dashboard-risk-summary-card">
                      <span>Highest exposure</span>
                      <strong>{topRiskProject?.name || '-'}</strong>
                      <p>{formatMetric(topRiskProject?.totalRiskAmount, 'currency')}</p>
                    </div>
                    <div className="dashboard-risk-summary-card danger">
                      <span>Total overdue</span>
                      <strong>{formatMetric(riskOverdueTotal, 'currency')}</strong>
                      <p>เงินค้างชำระที่ควรเร่งจัดการ</p>
                    </div>
                    <div className="dashboard-risk-summary-card warning">
                      <span>Pending admin</span>
                      <strong>{formatMetric(riskPendingTotal, 'currency')}</strong>
                      <p>ยอดที่รอการตรวจจาก admin</p>
                    </div>
                  </div>

                  <div className="dashboard-risk-legend">
                    <span><i className="overdue" /> Overdue</span>
                    <span><i className="pending" /> Pending Admin</span>
                  </div>

                  <div className="dashboard-risk-list">
                    {riskyRows.map((item, index) => (
                      <RiskProjectRow
                        key={item.projectId || item.name}
                        item={item}
                        index={index}
                        maxAmount={maxRiskAmount}
                      />
                    ))}
                  </div>
                </>
              ) : (
                <div className="dashboard-empty-state">
                  ยังไม่มีโปรเจกต์ที่มียอด overdue หรือ pending admin ให้จัดอันดับ
                </div>
              )}
            </div>
          </DashboardPanel>
        </div>

        <div className="dashboard-side-stack">
          <DashboardPanel
            title="Budget Health"
            description="สัดส่วนการใช้งบและจุดเสี่ยงที่ควรจับตาในภาพรวม"
          >
            <div
              className="dashboard-budget-status"
              style={{
                '--status-bg': utilizationTone.soft,
                '--status-color': utilizationTone.text,
                '--status-accent': utilizationTone.accent,
              }}
            >
              <div>
                <span>Spending status</span>
                <strong>{formatMetric(data?.kpis?.budgetUtilization, 'percent')}</strong>
              </div>

              <div className="dashboard-budget-status-label">
                {(data?.kpis?.budgetUtilization || 0) > 85 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                {(data?.kpis?.budgetUtilization || 0) > 85 ? 'ควรตรวจสอบงบใกล้เต็ม' : 'ยังอยู่ในกรอบใช้งบ'}
              </div>
            </div>

            <div className="dashboard-row-stack">
              {data?.budgetBreakdown?.map((item) => (
                <BudgetRow key={item.key} item={item} />
              ))}
            </div>
          </DashboardPanel>

          <DashboardPanel
            title="Attention Today"
            description="จุดที่ควรเปิดไปจัดการต่อทันทีจากข้อมูล summary ชุดนี้"
          >
            <div className="dashboard-row-stack">
              {data?.attentionItems?.map((item) => (
                <AttentionItem key={item.key} item={item} />
              ))}
            </div>
          </DashboardPanel>

          <DashboardPanel
            title="Recent Actions"
            description="เหตุการณ์ล่าสุดจากการอนุมัติ transaction และ input request"
          >
            <div className="dashboard-timeline">
              {data?.recentActions?.length ? (
                data.recentActions.map((item, index) => (
                  <div key={item.id} className="dashboard-timeline-item">
                    <div className="dashboard-timeline-marker" data-active={index === 0 ? 'true' : undefined} />

                    <div className="dashboard-timeline-content">
                      <time>{formatDateTime(item.time)}</time>
                      <p>{item.action || '-'}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="dashboard-empty-state">ยังไม่มีกิจกรรมล่าสุดให้แสดง</div>
              )}
            </div>
          </DashboardPanel>
        </div>
      </section>

      <section className="dashboard-signal-grid" aria-label="Portfolio signals">
        {portfolioSignals.map((item) => (
          <article key={item.title} className={`dashboard-signal-card dashboard-signal-${item.tone}`}>
            <span>{item.title}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

export default DashboardPage;
