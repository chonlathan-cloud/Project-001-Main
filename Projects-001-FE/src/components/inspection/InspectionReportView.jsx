import { useState } from 'react';
import {
  BarChart3,
  BriefcaseBusiness,
  CalendarDays,
  FileText,
  Printer,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';
import InspectionFilePreview from './InspectionFilePreview';
import {
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_SEVERITY_OPTIONS,
  INSPECTION_STATUS_LABELS,
  INSPECTION_STATUS_OPTIONS,
  formatInspectionDate,
  formatInspectionDateTime,
  formatReadinessScore,
  getSeverityTone,
  getStatusTone,
  isInspectionDefectOverdue,
} from './inspectionUtils';

const REPORT_TYPES = [
  { value: 'CLIENT', label: 'Client', icon: UsersRound },
  { value: 'CONTRACTOR', label: 'Contractor', icon: BriefcaseBusiness },
  { value: 'MANAGEMENT', label: 'Management', icon: BarChart3 },
];

const EMPTY_FILTERS = {
  reportType: 'CLIENT',
  zoneId: '',
  contractorId: '',
  severity: '',
  status: '',
  includeResolved: false,
  includePhotos: true,
};

function getZoneName(zones, zoneId) {
  return zones.find((zone) => zone.id === zoneId)?.name || '-';
}

function getContractorName(defect) {
  return defect.assigned_subcontractor_name || 'Unassigned';
}

function countBy(items, getKey) {
  const counts = {};
  items.forEach((item) => {
    const key = getKey(item) || 'Unassigned';
    counts[key] = Number(counts[key] || 0) + 1;
  });
  return counts;
}

function sortedEntries(map) {
  return Object.entries(map).sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0));
}

function applyReportFilters(defects, filters) {
  return defects.filter((defect) => {
    if (filters.zoneId && defect.zone_id !== filters.zoneId) return false;
    if (filters.contractorId && defect.assigned_subcontractor_id !== filters.contractorId) return false;
    if (filters.severity && defect.severity !== filters.severity) return false;
    if (filters.status && defect.status !== filters.status) return false;
    if (!filters.includeResolved && defect.status === 'RESOLVED') return false;
    return true;
  });
}

function ReportMetric({ label, value, subtext, tone = 'neutral' }) {
  return (
    <article className={`inspection-report-metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{subtext}</small>
    </article>
  );
}

function ReportDefectRows({ defects, zones, limit = 8 }) {
  const visibleDefects = defects.slice(0, limit);

  if (!visibleDefects.length) {
    return <div className="inspection-soft-empty">No defects in this section</div>;
  }

  return (
    <div className="inspection-report-list">
      {visibleDefects.map((defect) => (
        <article key={defect.id} className="inspection-report-defect">
          <div>
            <strong>{defect.display_no}</strong>
            <span>{defect.title}</span>
            <small>{getZoneName(zones, defect.zone_id)} / {getContractorName(defect)}</small>
          </div>
          <div className="inspection-badge-row">
            <span className={`inspection-badge tone-${getSeverityTone(defect.severity)}`}>
              {INSPECTION_SEVERITY_LABELS[defect.severity] || defect.severity}
            </span>
            <span className={`inspection-badge tone-${getStatusTone(defect.status)}`}>
              {INSPECTION_STATUS_LABELS[defect.status] || defect.status}
            </span>
          </div>
        </article>
      ))}
    </div>
  );
}

function ReportPhotoStrip({ defects }) {
  const fileIds = defects
    .flatMap((defect) => [
      ...(Array.isArray(defect.before_file_ids) ? defect.before_file_ids : []),
      ...(Array.isArray(defect.after_file_ids) ? defect.after_file_ids : []),
    ])
    .slice(0, 6);

  if (!fileIds.length) {
    return <div className="inspection-soft-empty">No photos selected by current filters</div>;
  }

  return (
    <div className="inspection-report-photo-strip">
      {fileIds.map((fileId) => (
        <InspectionFilePreview key={fileId} fileId={fileId} label="Report photo" compact />
      ))}
    </div>
  );
}

function ContractorActionList({ defects, zones }) {
  const groups = {};
  defects.forEach((defect) => {
    const contractor = getContractorName(defect);
    groups[contractor] = groups[contractor] || [];
    groups[contractor].push(defect);
  });

  if (!Object.keys(groups).length) {
    return <div className="inspection-soft-empty">No contractor action items</div>;
  }

  return (
    <div className="inspection-report-contractor-groups">
      {Object.entries(groups).map(([contractor, contractorDefects]) => (
        <section key={contractor} className="inspection-report-group">
          <div className="inspection-report-group-head">
            <h4>{contractor}</h4>
            <span>{contractorDefects.length} items</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Description</th>
                <th>Zone</th>
                <th>Due</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {contractorDefects.map((defect) => (
                <tr key={defect.id}>
                  <td>{defect.display_no}</td>
                  <td>{defect.title}</td>
                  <td>{getZoneName(zones, defect.zone_id)}</td>
                  <td>{formatInspectionDate(defect.due_date)}</td>
                  <td>{INSPECTION_STATUS_LABELS[defect.status] || defect.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function CountPanel({ title, counts }) {
  const entries = sortedEntries(counts);

  return (
    <section className="inspection-report-panel">
      <h4>{title}</h4>
      {entries.length ? (
        <div className="inspection-report-counts">
          {entries.map(([label, count]) => (
            <div key={label}>
              <span>{label}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div className="inspection-soft-empty">No counts</div>
      )}
    </section>
  );
}

function ReportLogList({ reportLogs = [], loading = false }) {
  if (loading) {
    return <div className="inspection-soft-empty">Loading report logs</div>;
  }

  if (!reportLogs.length) {
    return <div className="inspection-soft-empty">No report print logs yet</div>;
  }

  return (
    <div className="inspection-report-log-list">
      {reportLogs.slice(0, 8).map((log) => (
        <article key={log.id}>
          <div>
            <strong>{log.report_type}</strong>
            <span>{formatInspectionDateTime(log.printed_at)}</span>
          </div>
          <small>{log.printed_by || 'Unknown user'}</small>
        </article>
      ))}
    </div>
  );
}

export default function InspectionReportView({
  projectName,
  round,
  summary,
  defects = [],
  zones = [],
  subcontractors = [],
  reportLogs = [],
  loadingLogs = false,
  canPrint = false,
  printing = false,
  printError = '',
  onPrintReport,
  onRefreshLogs,
}) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const filteredDefects = applyReportFilters(defects, filters);
  const openDefects = filteredDefects.filter((defect) => defect.status !== 'RESOLVED');
  const criticalDefects = filteredDefects.filter((defect) => defect.severity === 'CRITICAL' && defect.status !== 'RESOLVED');
  const overdueDefects = filteredDefects.filter(isInspectionDefectOverdue);
  const readyDefects = filteredDefects.filter((defect) => defect.status === 'READY_FOR_REVIEW');
  const resolvedDefects = filteredDefects.filter((defect) => defect.status === 'RESOLVED');
  const statusCounts = countBy(filteredDefects, (defect) => INSPECTION_STATUS_LABELS[defect.status] || defect.status);
  const severityCounts = countBy(filteredDefects, (defect) => INSPECTION_SEVERITY_LABELS[defect.severity] || defect.severity);
  const contractorCounts = countBy(openDefects, getContractorName);
  const selectedReport = REPORT_TYPES.find((item) => item.value === filters.reportType) || REPORT_TYPES[0];
  const SelectedIcon = selectedReport.icon;

  const updateFilters = (updates) => {
    setFilters((current) => ({ ...current, ...updates }));
  };

  const printReport = async () => {
    if (!canPrint || printing) return;
    try {
      await onPrintReport({
        report_type: filters.reportType,
        filters: {
          zone_id: filters.zoneId || null,
          assigned_subcontractor_id: filters.contractorId || null,
          severity: filters.severity || null,
          status: filters.status || null,
          include_resolved: filters.includeResolved,
          include_photos: filters.includePhotos,
          visible_defect_count: filteredDefects.length,
        },
      });
      window.setTimeout(() => window.print(), 80);
    } catch {
      // Parent state renders the backend error.
    }
  };

  return (
    <section className="inspection-report-workspace">
      <div className="inspection-report-controls">
        <div>
          <span>Reports</span>
          <h3>{selectedReport.label} Report</h3>
        </div>
        <div className="inspection-report-actions">
          <button type="button" className="inspection-button secondary" onClick={onRefreshLogs} disabled={loadingLogs}>
            <RefreshCw size={16} />
            Logs
          </button>
          <button type="button" className="inspection-button primary" onClick={printReport} disabled={!canPrint || printing}>
            <Printer size={16} />
            Print / PDF
          </button>
        </div>
      </div>

      {printError ? <div className="inspection-alert danger">{printError}</div> : null}
      {!canPrint ? <div className="inspection-alert danger">Inspection staff access is required to print reports.</div> : null}

      <div className="inspection-report-filter-grid">
        <div className="inspection-report-type-tabs">
          {REPORT_TYPES.map((reportType) => {
            const Icon = reportType.icon;
            return (
              <button
                key={reportType.value}
                type="button"
                className={filters.reportType === reportType.value ? 'active' : ''}
                onClick={() => updateFilters({ reportType: reportType.value })}
              >
                <Icon size={16} />
                {reportType.label}
              </button>
            );
          })}
        </div>
        <select value={filters.zoneId} onChange={(event) => updateFilters({ zoneId: event.target.value })}>
          <option value="">All zones</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
        <select value={filters.contractorId} onChange={(event) => updateFilters({ contractorId: event.target.value })}>
          <option value="">All contractors</option>
          {subcontractors.map((subcontractor) => {
            const id = subcontractor.subcontractor_id || subcontractor.id;
            return (
              <option key={id} value={id}>
                {subcontractor.name || subcontractor.company_name || id}
              </option>
            );
          })}
        </select>
        <select value={filters.severity} onChange={(event) => updateFilters({ severity: event.target.value })}>
          <option value="">All severities</option>
          {INSPECTION_SEVERITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select value={filters.status} onChange={(event) => updateFilters({ status: event.target.value })}>
          <option value="">All statuses</option>
          {INSPECTION_STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <label className="inspection-filter-toggle">
          <input
            type="checkbox"
            checked={filters.includeResolved}
            onChange={(event) => updateFilters({ includeResolved: event.target.checked })}
          />
          Resolved
        </label>
        <label className="inspection-filter-toggle">
          <input
            type="checkbox"
            checked={filters.includePhotos}
            onChange={(event) => updateFilters({ includePhotos: event.target.checked })}
          />
          Photos
        </label>
      </div>

      <div className="inspection-report-layout">
        <article className="inspection-report-page inspection-print-scope">
          <header className="inspection-report-page-head">
            <div>
              <span>
                <SelectedIcon size={16} />
                {selectedReport.label} Report
              </span>
              <h2>{projectName || 'Inspection Project'}</h2>
              <p>{round?.name || 'Inspection Round'} / Printed {formatInspectionDate(new Date())}</p>
            </div>
            <div>
              <strong>{formatReadinessScore(summary?.readiness_score)}</strong>
              <small>readiness</small>
            </div>
          </header>

          <section className="inspection-report-metrics">
            <ReportMetric label="Visible defects" value={filteredDefects.length} subtext={`${openDefects.length} open`} />
            <ReportMetric label="Critical" value={criticalDefects.length} subtext="Open critical items" tone={criticalDefects.length ? 'danger' : 'positive'} />
            <ReportMetric label="Overdue" value={overdueDefects.length} subtext="Past due unresolved" tone={overdueDefects.length ? 'warning' : 'neutral'} />
            <ReportMetric label="Ready Review" value={readyDefects.length} subtext={`${resolvedDefects.length} resolved`} tone="neutral" />
          </section>

          {filters.reportType === 'CLIENT' ? (
            <>
              <section className="inspection-report-section">
                <div className="inspection-report-section-head">
                  <h3>Open Critical / Handover Blockers</h3>
                  <ShieldCheck size={18} />
                </div>
                <ReportDefectRows defects={[...criticalDefects, ...overdueDefects]} zones={zones} limit={10} />
              </section>
              {filters.includePhotos ? (
                <section className="inspection-report-section">
                  <h3>Selected Photos</h3>
                  <ReportPhotoStrip defects={[...criticalDefects, ...overdueDefects, ...openDefects]} />
                </section>
              ) : null}
            </>
          ) : null}

          {filters.reportType === 'CONTRACTOR' ? (
            <section className="inspection-report-section">
              <div className="inspection-report-section-head">
                <h3>Contractor Action List</h3>
                <BriefcaseBusiness size={18} />
              </div>
              <ContractorActionList defects={openDefects} zones={zones} />
            </section>
          ) : null}

          {filters.reportType === 'MANAGEMENT' ? (
            <>
              <div className="inspection-report-panel-grid">
                <CountPanel title="Status Breakdown" counts={statusCounts} />
                <CountPanel title="Severity Breakdown" counts={severityCounts} />
                <CountPanel title="Open By Contractor" counts={contractorCounts} />
              </div>
              <section className="inspection-report-section">
                <div className="inspection-report-section-head">
                  <h3>Risk Items</h3>
                  <BarChart3 size={18} />
                </div>
                <ReportDefectRows defects={[...overdueDefects, ...criticalDefects, ...readyDefects]} zones={zones} limit={12} />
              </section>
            </>
          ) : null}
        </article>

        <aside className="inspection-report-log-panel">
          <div className="inspection-detail-card-head">
            <h3>Print Logs</h3>
            <FileText size={18} />
          </div>
          <ReportLogList reportLogs={reportLogs} loading={loadingLogs} />
          <div className="inspection-report-log-note">
            <CalendarDays size={15} />
            Browser print is logged when the print action is requested.
          </div>
        </aside>
      </div>
    </section>
  );
}
