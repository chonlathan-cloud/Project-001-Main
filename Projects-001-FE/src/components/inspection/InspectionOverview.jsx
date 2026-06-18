import {
  AlertTriangle,
  ClipboardCheck,
  Clock3,
  Gauge,
  ListChecks,
  ShieldCheck,
} from 'lucide-react';
import {
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_STATUS_LABELS,
  countFromMap,
  formatReadinessScore,
  getSeverityTone,
  getStatusTone,
} from './inspectionUtils';

function OverviewMetric({ icon: Icon, label, value, subtext, tone = 'neutral' }) {
  return (
    <article className={`inspection-metric-card tone-${tone}`}>
      <div className="inspection-metric-icon">{Icon ? <Icon size={18} /> : null}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <small>{subtext}</small>
    </article>
  );
}

function CountList({ title, items, emptyLabel }) {
  const visibleItems = items.filter((item) => Number(item.count || 0) > 0);

  return (
    <section className="inspection-count-panel">
      <div className="inspection-count-panel-head">
        <h3>{title}</h3>
        <span>{visibleItems.length}</span>
      </div>
      {visibleItems.length ? (
        <div className="inspection-count-list">
          {visibleItems.map((item) => (
            <div key={item.key} className={`inspection-count-row tone-${item.tone || 'neutral'}`}>
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div className="inspection-soft-empty">{emptyLabel}</div>
      )}
    </section>
  );
}

export default function InspectionOverview({ summary, loading = false }) {
  if (loading) {
    return (
      <section className="inspection-overview-grid">
        {[0, 1, 2, 3].map((item) => (
          <article key={item} className="inspection-metric-card is-loading" />
        ))}
      </section>
    );
  }

  const safeSummary = summary || {};
  const totalDefects = Number(safeSummary.total_defects || 0);
  const resolvedDefects = Number(safeSummary.resolved_defects || 0);
  const openDefects = Number(safeSummary.open_defects || 0);
  const readyForReview = Number(safeSummary.ready_for_review_defects || 0);
  const overdueCount = Number(safeSummary.overdue_count || 0);
  const severityCounts = safeSummary.severity_counts || {};
  const categoryCounts = safeSummary.category_counts || {};
  const contractorCounts = safeSummary.contractor_counts || {};
  const criticalCount = countFromMap(severityCounts, 'CRITICAL');

  const statusItems = Object.entries(INSPECTION_STATUS_LABELS).map(([key, label]) => ({
    key,
    label,
    count:
      key === 'OPEN'
        ? safeSummary.open_defects
        : key === 'IN_PROGRESS'
          ? safeSummary.in_progress_defects
          : key === 'READY_FOR_REVIEW'
            ? safeSummary.ready_for_review_defects
            : safeSummary.resolved_defects,
    tone: getStatusTone(key),
  }));
  const severityItems = Object.entries(INSPECTION_SEVERITY_LABELS).map(([key, label]) => ({
    key,
    label,
    count: countFromMap(severityCounts, key),
    tone: getSeverityTone(key),
  }));
  const categoryItems = Object.entries(categoryCounts).map(([key, count]) => ({
    key,
    label: key,
    count,
  }));
  const contractorItems = Object.entries(contractorCounts).map(([key, count]) => ({
    key,
    label: key,
    count,
  }));

  return (
    <div className="inspection-overview">
      <section className="inspection-overview-grid">
        <OverviewMetric
          icon={ListChecks}
          label="Total Defects"
          value={totalDefects}
          subtext={`${resolvedDefects} resolved`}
        />
        <OverviewMetric
          icon={AlertTriangle}
          label="Open"
          value={openDefects}
          subtext={`${criticalCount} critical`}
          tone={openDefects || criticalCount ? 'danger' : 'positive'}
        />
        <OverviewMetric
          icon={Clock3}
          label="Overdue"
          value={overdueCount}
          subtext={`${readyForReview} ready for review`}
          tone={overdueCount ? 'warning' : 'neutral'}
        />
        <OverviewMetric
          icon={Gauge}
          label="Readiness"
          value={formatReadinessScore(safeSummary.readiness_score)}
          subtext="Resolved over total"
          tone={Number(safeSummary.readiness_score || 0) >= 80 ? 'positive' : 'neutral'}
        />
      </section>

      {totalDefects ? (
        <section className="inspection-overview-panels">
          <CountList title="Status" items={statusItems} emptyLabel="No status counts" />
          <CountList title="Severity" items={severityItems} emptyLabel="No severity counts" />
          <CountList title="Categories" items={categoryItems} emptyLabel="No category counts" />
          <CountList title="Contractors" items={contractorItems} emptyLabel="No contractor counts" />
        </section>
      ) : (
        <section className="inspection-empty-band">
          <ClipboardCheck size={24} />
          <div>
            <h3>No defects in this round</h3>
            <p>This round has no captured inspection items.</p>
          </div>
          <ShieldCheck size={20} />
        </section>
      )}
    </div>
  );
}
