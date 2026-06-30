import { useMemo, useRef, useState } from 'react';
import {
  BarChart3,
  BriefcaseBusiness,
  CalendarDays,
  FileImage,
  FileText,
  ImageOff,
  Loader2,
  MapPin,
  Printer,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';
import useInspectionSignedUrl from './useInspectionSignedUrl';
import {
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_SEVERITY_OPTIONS,
  INSPECTION_STATUS_LABELS,
  INSPECTION_STATUS_OPTIONS,
  clampPlanCoordinate,
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

const REPORT_ASSET_TIMEOUT_MS = 8000;

function getZoneName(zones, zoneId) {
  return zones.find((zone) => zone.id === zoneId)?.name || '-';
}

function getZoneById(zones, zoneId) {
  return zones.find((zone) => zone.id === zoneId) || null;
}

function getContractorName(defect) {
  return defect.assigned_subcontractor_name || 'Unassigned';
}

function getReportId(round, reportType) {
  const source = round?.id || round?.name || 'inspection';
  return `${String(reportType || 'REPORT').slice(0, 3)}-${String(source).slice(-8).toUpperCase()}`;
}

function getDefectNarrative(defect) {
  return defect.description || defect.title || 'No description provided.';
}

function getDefectPhotoIds(defect) {
  return [
    ...(Array.isArray(defect.before_file_ids) ? defect.before_file_ids : []),
    ...(Array.isArray(defect.after_file_ids) ? defect.after_file_ids : []),
  ].filter(Boolean);
}

function buildDefectSequenceMap(defects) {
  const sequenceMap = {};
  defects.forEach((defect, index) => {
    if (defect?.id) {
      sequenceMap[defect.id] = index + 1;
    }
  });
  return sequenceMap;
}

function formatDefectSequence(value, fallback = 1) {
  const sequence = Number(value || fallback);
  return String(Number.isFinite(sequence) ? sequence : fallback).padStart(2, '0');
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

function waitForReportAssets(scope) {
  if (!scope) return Promise.resolve();

  const startedAt = Date.now();

  return new Promise((resolve) => {
    const check = () => {
      const loadingAssets = scope.querySelector('[data-report-asset-loading="true"]');
      const pendingImages = Array.from(scope.querySelectorAll('img')).filter((image) => !image.complete);
      const timedOut = Date.now() - startedAt > REPORT_ASSET_TIMEOUT_MS;

      if ((!loadingAssets && pendingImages.length === 0) || timedOut) {
        resolve();
        return;
      }

      window.setTimeout(check, 120);
    };

    check();
  });
}

function ReportImage({ fileId, label, className = '', badge = '' }) {
  const { signedUrl, contentType, filename, loading, error } = useInspectionSignedUrl(fileId);
  const [imageReady, setImageReady] = useState(false);
  const isImage = contentType ? contentType.startsWith('image/') : true;
  const assetLoading = Boolean(fileId && (loading || (signedUrl && isImage && !imageReady)));

  if (!fileId) {
    return (
      <div className={`inspection-report-photo-empty ${className}`}>
        <ImageOff size={18} />
        <span>No photo</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`inspection-report-photo-empty ${className}`} data-report-asset-loading="true">
        <Loader2 size={18} className="inspection-spin" />
        <span>Loading photo</span>
      </div>
    );
  }

  if (error || !signedUrl) {
    return (
      <div className={`inspection-report-photo-empty danger ${className}`}>
        <ImageOff size={18} />
        <span>{error || 'Photo unavailable'}</span>
      </div>
    );
  }

  if (!isImage) {
    return (
      <a className={`inspection-report-photo-empty ready ${className}`} href={signedUrl} target="_blank" rel="noreferrer">
        <FileImage size={18} />
        <span>{filename || label}</span>
      </a>
    );
  }

  return (
    <figure
      className={`inspection-report-photo ${className}`}
      data-report-asset-loading={assetLoading ? 'true' : undefined}
    >
      <img
        src={signedUrl}
        alt={filename || label}
        onLoad={() => setImageReady(true)}
        onError={() => setImageReady(true)}
      />
      {badge ? <figcaption>{badge}</figcaption> : null}
    </figure>
  );
}

function ReportPlanImage({ zone, defects, sequenceMap = {} }) {
  const { signedUrl, loading, error } = useInspectionSignedUrl(zone?.plan_file_id);
  const [imageReady, setImageReady] = useState(false);
  const assetLoading = Boolean(zone?.plan_file_id && (loading || (signedUrl && !imageReady)));
  const pinnedDefects = defects.filter((defect) => defect.plan_x != null && defect.plan_y != null);

  return (
    <div className="inspection-report-plan-frame" data-report-asset-loading={assetLoading ? 'true' : undefined}>
      {loading ? (
        <div className="inspection-report-plan-empty">
          <Loader2 size={20} className="inspection-spin" />
          Loading floor plan
        </div>
      ) : signedUrl ? (
        <img
          src={signedUrl}
          alt={`${zone?.name || 'Inspection zone'} floor plan`}
          onLoad={() => setImageReady(true)}
          onError={() => setImageReady(true)}
        />
      ) : (
        <div className="inspection-report-plan-empty">
          <MapPin size={22} />
          {error || 'No floor plan uploaded for this zone'}
        </div>
      )}

      {pinnedDefects.map((defect, index) => {
        const sequence = sequenceMap[defect.id] || index + 1;
        return (
          <span
            key={defect.id}
            className={`inspection-report-plan-pin tone-${getSeverityTone(defect.severity)}`}
            style={{
              left: `${clampPlanCoordinate(defect.plan_x)}%`,
              top: `${clampPlanCoordinate(defect.plan_y)}%`,
            }}
            title={`NO ${formatDefectSequence(sequence)} / ${defect.display_no || `D-${sequence}`} ${defect.title || ''}`.trim()}
          >
            {sequence}
          </span>
        );
      })}
    </div>
  );
}

function ReportPlanMap({ defects, zones, selectedZoneId, sequenceMap = {} }) {
  const zoneGroups = zones
    .filter((zone) => (selectedZoneId ? zone.id === selectedZoneId : true))
    .map((zone) => ({
      zone,
      defects: defects.filter((defect) => defect.zone_id === zone.id),
    }))
    .filter((group) => group.defects.length || group.zone?.plan_file_id);
  const fallbackZone = selectedZoneId ? getZoneById(zones, selectedZoneId) : zones[0];
  const visibleGroups = zoneGroups.length ? zoneGroups.slice(0, 3) : [{ zone: fallbackZone, defects }];

  return (
    <section className="inspection-report-document-section">
      <div className="inspection-report-section-title">
        <div>
          <span>Localization</span>
          <h3>Defect Location Map</h3>
        </div>
        <MapPin size={18} />
      </div>

      <div className="inspection-report-plan-grid">
        {visibleGroups.map(({ zone, defects: zoneDefects }, groupIndex) => (
          <article key={zone?.id || `zone-${groupIndex}`} className="inspection-report-plan-card">
            <ReportPlanImage zone={zone} defects={zoneDefects} sequenceMap={sequenceMap} />
            <p>
              {zone?.name || 'Inspection plan'} / {zoneDefects.length} marked defects
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ReportDefectRows({ defects, zones, limit = 8, sequenceMap = {} }) {
  const visibleDefects = defects.slice(0, limit);

  if (!visibleDefects.length) {
    return <div className="inspection-soft-empty">No defects in this section</div>;
  }

  return (
    <div className="inspection-report-list">
      {visibleDefects.map((defect, index) => {
        const sequence = sequenceMap[defect.id] || index + 1;
        return (
          <article key={defect.id} className="inspection-report-defect">
            <div>
              <strong>NO: {formatDefectSequence(sequence)} / ID: {defect.display_no || '-'}</strong>
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
        );
      })}
    </div>
  );
}

function ReportPhotoGrid({ defect }) {
  const fileIds = getDefectPhotoIds(defect).slice(0, 7);

  if (!fileIds.length) {
    return (
      <div className="inspection-report-photo-grid empty">
        <div className="inspection-report-photo-empty">
          <ImageOff size={18} />
          <span>No photos attached</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`inspection-report-photo-grid count-${Math.min(fileIds.length, 7)}`}>
      {fileIds.map((fileId, index) => (
        <ReportImage
          key={`${defect.id}-${fileId}`}
          fileId={fileId}
          label={`${defect.display_no || 'Defect'} photo ${index + 1}`}
          className={index === 0 ? 'featured' : ''}
          badge={String(index + 1)}
        />
      ))}
    </div>
  );
}

function ReportDefectDetailCard({ defect, zones, index, showPhotos, sequence }) {
  const defectSequence = sequence || index + 1;

  return (
    <article className="inspection-report-detail-card">
      {showPhotos ? <ReportPhotoGrid defect={defect} /> : null}
      <div className="inspection-report-detail-body">
        <div>
          <div className="inspection-report-id-row">
            <span className="inspection-report-no-pill">NO: {formatDefectSequence(defectSequence)}</span>
            <span className="inspection-report-id-pill">
              ID: {defect.display_no || String(index + 1).padStart(3, '0')}
            </span>
          </div>
          <h4>{defect.title || 'Untitled defect'}</h4>
          <div className="inspection-report-detail-badges">
            <span className={`inspection-badge tone-${getSeverityTone(defect.severity)}`}>
              {INSPECTION_SEVERITY_LABELS[defect.severity] || defect.severity || 'Unrated'}
            </span>
            <span className={`inspection-badge tone-${getStatusTone(defect.status)}`}>
              {INSPECTION_STATUS_LABELS[defect.status] || defect.status || 'Open'}
            </span>
          </div>
        </div>

        <p>{getDefectNarrative(defect)}</p>

        <dl className="inspection-report-detail-meta">
          <div>
            <dt>Location</dt>
            <dd>{getZoneName(zones, defect.zone_id)}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{defect.category || '-'}</dd>
          </div>
          <div>
            <dt>Trade</dt>
            <dd>{getContractorName(defect)}</dd>
          </div>
          <div>
            <dt>Due</dt>
            <dd className={isInspectionDefectOverdue(defect) ? 'danger' : ''}>{formatInspectionDate(defect.due_date)}</dd>
          </div>
          <div>
            <dt>Reported</dt>
            <dd>{formatInspectionDate(defect.created_at || defect.updated_at)}</dd>
          </div>
        </dl>
      </div>
    </article>
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

function ReportDocumentHeader({ projectName, round, selectedReport, summary, visibleCount, reportId }) {
  const SelectedIcon = selectedReport.icon;

  return (
    <header className="inspection-report-document-head">
      <div>
        <span className="inspection-report-document-kicker">
          <SelectedIcon size={16} />
          {selectedReport.label} Report
        </span>
        <h2>{projectName || 'Inspection Project'}</h2>
        <p>{round?.name || 'Inspection Round'} / Issued {formatInspectionDate(new Date())}</p>
        <div className="inspection-report-document-meta">
          <span>Report ID: {reportId}</span>
          <span>Target: {formatInspectionDate(round?.target_close_at)}</span>
          <span>{visibleCount} visible defects</span>
        </div>
      </div>
      <div className="inspection-report-readiness-seal">
        <strong>{formatReadinessScore(summary?.readiness_score)}</strong>
        <small>readiness</small>
      </div>
    </header>
  );
}

function ReportSignatureFooter({ reportId }) {
  return (
    <footer className="inspection-report-signature-footer">
      <div>
        <span>Inspector Signature</span>
        <div aria-hidden="true" />
      </div>
      <div>
        <strong>Page generated for PDF</strong>
        <span>{reportId} / {formatInspectionDateTime(new Date())}</span>
      </div>
    </footer>
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

function ManagementSummary({ statusCounts, severityCounts, contractorCounts, riskDefects, zones, sequenceMap }) {
  return (
    <>
      <div className="inspection-report-panel-grid">
        <CountPanel title="Status Breakdown" counts={statusCounts} />
        <CountPanel title="Severity Breakdown" counts={severityCounts} />
        <CountPanel title="Open By Contractor" counts={contractorCounts} />
      </div>
      <section className="inspection-report-document-section">
        <div className="inspection-report-section-title">
          <div>
            <span>Risk</span>
            <h3>Blockers and Review Items</h3>
          </div>
          <BarChart3 size={18} />
        </div>
        <ReportDefectRows defects={riskDefects} zones={zones} limit={12} sequenceMap={sequenceMap} />
      </section>
    </>
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
  const [preparingPrint, setPreparingPrint] = useState(false);
  const printScopeRef = useRef(null);
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
  const reportId = getReportId(round, filters.reportType);
  const defectSequenceMap = buildDefectSequenceMap(filteredDefects);
  const clientDetailDefects = useMemo(() => {
    const preferred = [...criticalDefects, ...overdueDefects, ...openDefects];
    return Array.from(new Map(preferred.map((defect) => [defect.id, defect])).values()).slice(0, 12);
  }, [criticalDefects, openDefects, overdueDefects]);
  const riskDefects = useMemo(() => {
    const preferred = [...overdueDefects, ...criticalDefects, ...readyDefects];
    return Array.from(new Map(preferred.map((defect) => [defect.id, defect])).values());
  }, [criticalDefects, overdueDefects, readyDefects]);

  const updateFilters = (updates) => {
    setFilters((current) => ({ ...current, ...updates }));
  };

  const printReport = async () => {
    if (!canPrint || printing || preparingPrint) return;
    try {
      setPreparingPrint(true);
      await waitForReportAssets(printScopeRef.current);
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
      window.setTimeout(() => window.print(), 160);
    } catch {
      // Parent state renders the backend error.
    } finally {
      setPreparingPrint(false);
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
          <button type="button" className="inspection-button primary" onClick={printReport} disabled={!canPrint || printing || preparingPrint}>
            {printing || preparingPrint ? <Loader2 size={16} className="inspection-spin" /> : <Printer size={16} />}
            {preparingPrint ? 'Preparing...' : 'Print / PDF'}
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
        <article className="inspection-report-page inspection-print-scope" ref={printScopeRef}>
          <ReportDocumentHeader
            projectName={projectName}
            round={round}
            selectedReport={selectedReport}
            summary={summary}
            visibleCount={filteredDefects.length}
            reportId={reportId}
          />

          <section className="inspection-report-metrics">
            <ReportMetric label="Visible defects" value={filteredDefects.length} subtext={`${openDefects.length} open`} />
            <ReportMetric label="Critical" value={criticalDefects.length} subtext="Open critical items" tone={criticalDefects.length ? 'danger' : 'positive'} />
            <ReportMetric label="Overdue" value={overdueDefects.length} subtext="Past due unresolved" tone={overdueDefects.length ? 'warning' : 'neutral'} />
            <ReportMetric label="Ready Review" value={readyDefects.length} subtext={`${resolvedDefects.length} resolved`} tone="neutral" />
          </section>

          {filters.reportType === 'CLIENT' ? (
            <>
              <ReportPlanMap defects={filteredDefects} zones={zones} selectedZoneId={filters.zoneId} sequenceMap={defectSequenceMap} />
              <section className="inspection-report-document-section">
                <div className="inspection-report-section-title">
                  <div>
                    <span>Priority</span>
                    <h3>Open Critical / Handover Blockers</h3>
                  </div>
                  <ShieldCheck size={18} />
                </div>
                <ReportDefectRows defects={[...criticalDefects, ...overdueDefects]} zones={zones} limit={10} sequenceMap={defectSequenceMap} />
              </section>
              {filters.includePhotos ? (
                <section className="inspection-report-document-section">
                  <div className="inspection-report-section-title">
                    <div>
                      <span>Findings</span>
                      <h3>Detailed Defect Details</h3>
                    </div>
                    <FileImage size={18} />
                  </div>
                  <div className="inspection-report-detail-list">
                    {clientDetailDefects.length ? (
                      clientDetailDefects.map((defect, index) => (
                        <ReportDefectDetailCard
                          key={defect.id}
                          defect={defect}
                          zones={zones}
                          index={index}
                          showPhotos={filters.includePhotos}
                          sequence={defectSequenceMap[defect.id]}
                        />
                      ))
                    ) : (
                      <div className="inspection-soft-empty">No detailed defects for current filters</div>
                    )}
                  </div>
                </section>
              ) : null}
            </>
          ) : null}

          {filters.reportType === 'CONTRACTOR' ? (
            <>
              <ReportPlanMap defects={openDefects} zones={zones} selectedZoneId={filters.zoneId} sequenceMap={defectSequenceMap} />
              <section className="inspection-report-document-section">
                <div className="inspection-report-section-title">
                  <div>
                    <span>Action list</span>
                    <h3>Contractor Action List</h3>
                  </div>
                  <BriefcaseBusiness size={18} />
                </div>
                <ContractorActionList defects={openDefects} zones={zones} />
              </section>
              {filters.includePhotos ? (
                <section className="inspection-report-document-section">
                  <div className="inspection-report-section-title">
                    <div>
                      <span>Evidence</span>
                      <h3>Required Photo References</h3>
                    </div>
                    <FileImage size={18} />
                  </div>
                  <div className="inspection-report-detail-list compact">
                    {openDefects.slice(0, 8).map((defect, index) => (
                      <ReportDefectDetailCard
                        key={defect.id}
                        defect={defect}
                        zones={zones}
                        index={index}
                        showPhotos={filters.includePhotos}
                        sequence={defectSequenceMap[defect.id]}
                      />
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          ) : null}

          {filters.reportType === 'MANAGEMENT' ? (
            <>
              <ReportPlanMap defects={riskDefects.length ? riskDefects : filteredDefects} zones={zones} selectedZoneId={filters.zoneId} sequenceMap={defectSequenceMap} />
              <ManagementSummary
                statusCounts={statusCounts}
                severityCounts={severityCounts}
                contractorCounts={contractorCounts}
                riskDefects={riskDefects}
                zones={zones}
                sequenceMap={defectSequenceMap}
              />
              {filters.includePhotos ? (
                <section className="inspection-report-document-section">
                  <div className="inspection-report-section-title">
                    <div>
                      <span>Risk photos</span>
                      <h3>Management Evidence Review</h3>
                    </div>
                    <FileImage size={18} />
                  </div>
                  <div className="inspection-report-detail-list compact">
                    {(riskDefects.length ? riskDefects : filteredDefects).slice(0, 6).map((defect, index) => (
                      <ReportDefectDetailCard
                        key={defect.id}
                        defect={defect}
                        zones={zones}
                        index={index}
                        showPhotos={filters.includePhotos}
                        sequence={defectSequenceMap[defect.id]}
                      />
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          ) : null}

          <ReportSignatureFooter reportId={reportId} />
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
