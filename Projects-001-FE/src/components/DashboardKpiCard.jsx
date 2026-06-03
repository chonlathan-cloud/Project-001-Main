import React from 'react';
import { ClipboardCheck, Landmark, ReceiptText, TrendingUp, Wallet } from 'lucide-react';

const iconMap = {
  'total-budget': Landmark,
  'actual-cost': ReceiptText,
  'pending-approvals': ClipboardCheck,
};

function DashboardKpiCard({ card, formatMetric }) {
  const Icon = iconMap[card.key] || (card.kind === 'percent' ? TrendingUp : Wallet);
  const progress = Number(card.progress || 0);
  const normalizedProgress = Math.max(0, Math.min(progress, 100));
  const toneClass = `dashboard-kpi-card-${card.tone || 'neutral'}`;

  return (
    <article
      className={`dashboard-kpi-card ${toneClass}`}
      style={{
        background: '#ffffff',
        border: '1px solid #e7e0d4',
      }}
    >
      <div className="dashboard-kpi-top">
        <div className="dashboard-kpi-icon">
          <Icon size={18} />
        </div>
        {card.badge ? <span className="dashboard-kpi-badge">{card.badge}</span> : null}
      </div>

      <div className="dashboard-kpi-body">
        <div>
          <div className="dashboard-kpi-label">{card.label}</div>
          <div className="dashboard-kpi-value">{formatMetric(card.value, card.kind)}</div>
        </div>
        <p>{card.description}</p>
      </div>

      {card.progressLabel ? (
        <div className="dashboard-kpi-progress">
          <div className="dashboard-kpi-progress-label">
            <span>{card.progressLabel}</span>
            <span>{Math.round(normalizedProgress)}%</span>
          </div>
          <div className="dashboard-kpi-progress-track">
            <div style={{ width: `${normalizedProgress}%` }} />
          </div>
        </div>
      ) : null}
    </article>
  );
}

export default DashboardKpiCard;
