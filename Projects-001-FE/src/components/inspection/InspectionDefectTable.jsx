import { useState } from 'react';
import { Camera, ChevronLeft, ChevronRight, Eye, Filter, RefreshCw, Search } from 'lucide-react';
import {
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_SEVERITY_OPTIONS,
  INSPECTION_STATUS_LABELS,
  INSPECTION_STATUS_OPTIONS,
  formatInspectionDate,
  getSeverityTone,
  getStatusTone,
  isInspectionDefectOverdue,
} from './inspectionUtils';

const EMPTY_FILTERS = {
  search: '',
  zoneId: '',
  status: '',
  severity: '',
  category: '',
  overdueOnly: false,
};

const PAGE_SIZE = 12;

function matchesSearch(defect, search) {
  if (!search) return true;
  const needle = search.toLowerCase();
  const haystack = [
    defect.display_no,
    defect.title,
    defect.description,
    defect.category,
    defect.assigned_subcontractor_name,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(needle);
}

function getZoneName(zones, zoneId) {
  return zones.find((zone) => zone.id === zoneId)?.name || '-';
}

export default function InspectionDefectTable({
  defects = [],
  zones = [],
  categories = [],
  loading = false,
  onOpenDefect,
  onRefresh,
}) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);

  const filteredDefects = defects.filter((defect) => {
    if (!matchesSearch(defect, filters.search.trim())) return false;
    if (filters.zoneId && defect.zone_id !== filters.zoneId) return false;
    if (filters.status && defect.status !== filters.status) return false;
    if (filters.severity && defect.severity !== filters.severity) return false;
    if (filters.category && defect.category !== filters.category) return false;
    if (filters.overdueOnly && !isInspectionDefectOverdue(defect)) return false;
    return true;
  });
  const totalPages = Math.max(1, Math.ceil(filteredDefects.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pageDefects = filteredDefects.slice(pageStart, pageStart + PAGE_SIZE);
  const showingStart = filteredDefects.length ? pageStart + 1 : 0;
  const showingEnd = filteredDefects.length ? pageStart + pageDefects.length : 0;

  const updateFilters = (updates) => {
    setFilters((current) => ({ ...current, ...updates }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setPage(1);
  };

  return (
    <section className="inspection-register">
      <div className="inspection-register-head">
        <div>
          <span>Defect Register</span>
          <h3>{filteredDefects.length} defects</h3>
        </div>
        <button type="button" className="inspection-button secondary" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="inspection-register-filters">
        <label className="inspection-filter-search">
          <Search size={16} />
          <input
            value={filters.search}
            onChange={(event) => updateFilters({ search: event.target.value })}
            placeholder="Search ID, description, contractor"
          />
        </label>
        <select value={filters.zoneId} onChange={(event) => updateFilters({ zoneId: event.target.value })}>
          <option value="">All zones</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
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
        <select value={filters.severity} onChange={(event) => updateFilters({ severity: event.target.value })}>
          <option value="">All severities</option>
          {INSPECTION_SEVERITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select value={filters.category} onChange={(event) => updateFilters({ category: event.target.value })}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <label className="inspection-filter-toggle">
          <input
            type="checkbox"
            checked={filters.overdueOnly}
            onChange={(event) => updateFilters({ overdueOnly: event.target.checked })}
          />
          Overdue
        </label>
        <button type="button" className="inspection-filter-reset" onClick={resetFilters}>
          <Filter size={14} />
          Reset
        </button>
      </div>

      <div className="inspection-register-table-wrap">
        <table className="inspection-register-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Photo</th>
              <th>Description</th>
              <th>Zone</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Responsible</th>
              <th>Due</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pageDefects.map((defect) => {
              const beforeCount = Array.isArray(defect.before_file_ids) ? defect.before_file_ids.length : 0;
              const afterCount = Array.isArray(defect.after_file_ids) ? defect.after_file_ids.length : 0;
              const overdue = isInspectionDefectOverdue(defect);
              return (
                <tr key={defect.id} className={overdue ? 'is-overdue' : ''}>
                  <td>
                    <strong>{defect.display_no}</strong>
                  </td>
                  <td>
                    <span className="inspection-photo-count">
                      <Camera size={14} />
                      {beforeCount + afterCount}
                    </span>
                  </td>
                  <td>
                    <div className="inspection-table-title">
                      <strong>{defect.title}</strong>
                      <span>{defect.description || 'No notes'}</span>
                    </div>
                  </td>
                  <td>{getZoneName(zones, defect.zone_id)}</td>
                  <td>{defect.category || '-'}</td>
                  <td>
                    <span className={`inspection-badge tone-${getSeverityTone(defect.severity)}`}>
                      {INSPECTION_SEVERITY_LABELS[defect.severity] || defect.severity}
                    </span>
                  </td>
                  <td>{defect.assigned_subcontractor_name || 'Unassigned'}</td>
                  <td className={overdue ? 'inspection-overdue-text' : ''}>{formatInspectionDate(defect.due_date)}</td>
                  <td>
                    <span className={`inspection-badge tone-${getStatusTone(defect.status)}`}>
                      {INSPECTION_STATUS_LABELS[defect.status] || defect.status}
                    </span>
                  </td>
                  <td>{formatInspectionDate(defect.updated_at)}</td>
                  <td>
                    <button type="button" className="inspection-row-action" onClick={() => onOpenDefect(defect.id)}>
                      <Eye size={15} />
                      Open
                    </button>
                  </td>
                </tr>
              );
            })}
            {!filteredDefects.length ? (
              <tr>
                <td colSpan={11}>
                  <div className="inspection-table-empty" role="status" aria-live="polite">
                    {loading ? 'Loading defects' : 'No defects match the current filters'}
                  </div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {filteredDefects.length ? (
        <div className="inspection-pagination">
          <span>
            Showing {showingStart}-{showingEnd} of {filteredDefects.length}
          </span>
          <div className="inspection-pagination-actions">
            <button
              type="button"
              onClick={() => setPage(Math.max(1, currentPage - 1))}
              disabled={loading || currentPage <= 1}
              aria-label="Previous defects page"
            >
              <ChevronLeft size={15} />
              Previous
            </button>
            <strong>Page {currentPage} / {totalPages}</strong>
            <button
              type="button"
              onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
              disabled={loading || currentPage >= totalPages}
              aria-label="Next defects page"
            >
              Next
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
