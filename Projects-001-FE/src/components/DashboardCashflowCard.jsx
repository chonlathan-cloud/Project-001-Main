import React from 'react';
import { Scale, TrendingDown, TrendingUp } from 'lucide-react';

const statusStyles = {
  balanced: {
    label: 'Balanced',
    message: 'Cashflow is balanced',
    color: '#4f6f64',
    background: 'rgba(79, 111, 100, 0.12)',
    Icon: Scale,
  },
  surplus: {
    label: 'Surplus',
    message: 'Income is ahead of expense',
    color: '#166534',
    background: '#f3fbf7',
    Icon: TrendingUp,
  },
  deficit: {
    label: 'Deficit',
    message: 'Expense is ahead of income',
    color: '#9f1239',
    background: '#fef2f2',
    Icon: TrendingDown,
  },
};

function getBalanceStatus(balance, totalIncome, totalExpense) {
  const tolerance = Math.max(Math.abs(totalIncome), Math.abs(totalExpense), 1) * 0.03;

  if (Math.abs(balance) <= tolerance) {
    return 'balanced';
  }

  return balance > 0 ? 'surplus' : 'deficit';
}

function DashboardCashflowCard({
  balance = 0,
  totalIncome = 0,
  totalExpense = 0,
  cashflow = [],
  latestMonth = '',
  formatCurrency,
}) {
  const numericBalance = Number(balance || 0);
  const numericIncome = Number(totalIncome || 0);
  const numericExpense = Number(totalExpense || 0);
  const totalFlow = numericIncome + numericExpense;
  const incomeRatio = totalFlow > 0 ? Math.max(4, Math.min(96, (numericIncome / totalFlow) * 100)) : 50;
  const status = getBalanceStatus(numericBalance, numericIncome, numericExpense);
  const statusStyle = statusStyles[status];
  const StatusIcon = statusStyle.Icon;
  const toCurrency = formatCurrency || ((value) => String(value || 0));
  const trendItems = Array.isArray(cashflow) ? cashflow.slice(-7) : [];
  const maxTrendValue = Math.max(
    ...trendItems.map((item) => Math.abs(Number(item?.balance || 0))),
    1
  );

  return (
    <article
      className="dashboard-kpi-card dashboard-cashflow-card dashboard-cashflow-card-featured"
      style={{
        background: '#ffffff',
        border: '1px solid #e7e0d4',
        '--cashflow-color': statusStyle.color,
        '--cashflow-bg': statusStyle.background,
      }}
    >
      <div className="dashboard-cashflow-head">
        <div className="dashboard-cashflow-icon">
          <StatusIcon size={19} />
        </div>

        <span className="dashboard-cashflow-status">{statusStyle.label}</span>
      </div>

      <div className="dashboard-cashflow-grid">
        <div className="dashboard-cashflow-summary">
          <div className="dashboard-kpi-label">Cashflow Balance</div>
          <div className="dashboard-cashflow-value">{toCurrency(numericBalance)}</div>
          <p>
            {statusStyle.message}
            {latestMonth ? ` through ${latestMonth}` : ''}.
          </p>
        </div>

        {trendItems.length ? (
          <div className="dashboard-cashflow-trend" aria-label="Recent cashflow balance trend">
            {trendItems.map((item, index) => {
              const itemBalance = Number(item?.balance || 0);
              const height = Math.max(18, Math.min(72, (Math.abs(itemBalance) / maxTrendValue) * 72));

              return (
                <span
                  key={`${item?.month || 'month'}-${index}`}
                  className={itemBalance >= 0 ? 'is-positive' : 'is-negative'}
                  style={{ height: `${height}px` }}
                  title={`${item?.month || '-'}: ${toCurrency(itemBalance)}`}
                />
              );
            })}
          </div>
        ) : null}
      </div>

      <div className="dashboard-cashflow-flow">
        <div className="dashboard-cashflow-split" aria-label="Income and expense balance">
          <div style={{ width: `${incomeRatio}%` }} />
          <div />
        </div>

        <div className="dashboard-cashflow-amounts">
          <div>
            <span>Income</span>
            <strong>{toCurrency(numericIncome)}</strong>
          </div>
          <div>
            <span>Expense</span>
            <strong>{toCurrency(numericExpense)}</strong>
          </div>
        </div>
      </div>
    </article>
  );
}

export default DashboardCashflowCard;
