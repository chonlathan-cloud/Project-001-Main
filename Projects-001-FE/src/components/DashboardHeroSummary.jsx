import React from 'react';
import { Activity, CalendarDays, TrendingDown, TrendingUp, WalletCards } from 'lucide-react';

function DashboardHeroSummary({
  balance = 0,
  budgetUtilization = 0,
  cashflowLabel = 'Balanced',
  latestMonth = '-',
  pendingApprovals = 0,
  totalBudget = 0,
  formatCurrency,
  formatPercent,
  formatNumber,
}) {
  const numericBalance = Number(balance || 0);
  const isNegative = numericBalance < 0;
  const BalanceIcon = isNegative ? TrendingDown : TrendingUp;
  const toCurrency = formatCurrency || ((value) => String(value || 0));
  const toPercent = formatPercent || ((value) => `${value || 0}%`);
  const toNumber = formatNumber || ((value) => String(value || 0));
  const budgetTone = Number(budgetUtilization || 0) > 85 ? 'warning' : 'positive';

  return (
    <section className="dashboard-hero" aria-label="Dashboard overview">
      <div className="dashboard-hero-copy">
        <div className="dashboard-eyebrow">
          <Activity size={14} />
          Live portfolio overview
        </div>

        <div>
          <h1>Dashboard</h1>
          <p>Project financial health, approvals, and cashflow status across the active portfolio.</p>
        </div>
      </div>

      <div className="dashboard-hero-stats" aria-label="Dashboard headline metrics">
        <div className="dashboard-hero-stat dashboard-hero-stat-primary">
          <div className="dashboard-hero-stat-icon">
            <BalanceIcon size={18} />
          </div>
          <div>
            <span>Cashflow Balance</span>
            <strong>{toCurrency(numericBalance)}</strong>
            <small>{cashflowLabel}</small>
          </div>
        </div>

        <div className="dashboard-hero-stat">
          <div className="dashboard-hero-stat-icon">
            <WalletCards size={18} />
          </div>
          <div>
            <span>Total Budget</span>
            <strong>{toCurrency(totalBudget)}</strong>
            <small className={`dashboard-tone-${budgetTone}`}>{toPercent(budgetUtilization)} used</small>
          </div>
        </div>

        <div className="dashboard-hero-stat">
          <div className="dashboard-hero-stat-icon">
            <CalendarDays size={18} />
          </div>
          <div>
            <span>Latest Period</span>
            <strong>{latestMonth || '-'}</strong>
            <small>{toNumber(pendingApprovals)} approvals pending</small>
          </div>
        </div>
      </div>
    </section>
  );
}

export default DashboardHeroSummary;
