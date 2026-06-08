import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  BadgeDollarSign,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  Filter as FilterIcon,
  RefreshCcw,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import {
  getInsightWarehouseFilters,
  getInsightWarehouseExportUrl,
  getInsightWarehouseRows,
  getInsightWarehouseSummary,
} from './api';
import Loading from './components/Loading';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat('en-CA', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

const summaryToneStyles = {
  neutral: { background: '#ffffff', border: '#e5e7eb', text: '#111827', subtle: '#6b7280' },
  warning: { background: '#fff7ed', border: '#fdba74', text: '#9a3412', subtle: '#c2410c' },
  danger: { background: '#fef2f2', border: '#fca5a5', text: '#991b1b', subtle: '#b91c1c' },
  positive: { background: '#ecfdf5', border: '#86efac', text: '#166534', subtle: '#15803d' },
};

const flagToneStyles = {
  neutral: { background: '#f3f4f6', color: '#4b5563' },
  warning: { background: '#fef3c7', color: '#92400e' },
  danger: { background: '#fee2e2', color: '#b91c1c' },
  positive: { background: '#dcfce7', color: '#166534' },
};

const inputStyle = {
  width: '100%',
  padding: '11px 14px',
  borderRadius: '12px',
  border: '1px solid #e5e7eb',
  backgroundColor: 'white',
  fontSize: '14px',
  outline: 'none',
  color: '#111827',
};

const buttonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '8px',
  padding: '10px 14px',
  borderRadius: '12px',
  border: '1px solid #d1d5db',
  backgroundColor: 'white',
  color: '#374151',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: '600',
};

const pageInfoFallback = {
  page: 1,
  pageSize: 25,
  totalItems: 0,
  totalPages: 0,
  hasNext: false,
  hasPrevious: false,
};

const formatCurrency = (value) => `${currencyFormatter.format(Number(value || 0))} THB`;

const formatDate = (value) => {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return dateFormatter.format(parsed);
};

const formatDateTime = (value) => {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${dateFormatter.format(parsed)} ${parsed.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
};

const prettifyValue = (value) => {
  const cleaned = String(value || '').trim();
  if (!cleaned) return '-';
  return cleaned.replace(/_/g, ' ');
};

const sourceTypeLabel = (value) => {
  switch (value) {
    case 'INPUT_REQUEST':
      return 'Input';
    case 'INSTALLMENT':
      return 'Installment';
    case 'TRANSACTION':
      return 'Transaction';
    default:
      return prettifyValue(value);
  }
};

function SummaryCard({ card }) {
  const tone = summaryToneStyles[card.tone] || summaryToneStyles.neutral;
  const summaryText = `${card.key || ''} ${card.label || ''}`.toLowerCase();
  const hasAmount = card.amount != null;
  const hasCount = card.count != null;
  const IconComponent =
    summaryText.includes('overdue') || summaryText.includes('risk')
      ? AlertTriangle
      : summaryText.includes('amount') || summaryText.includes('paid') || summaryText.includes('cash')
        ? BadgeDollarSign
        : FileText;

  return (
    <div
      className="insights-summary-card"
      style={{
        '--summary-bg': tone.background,
        '--summary-border': tone.border,
        '--summary-text': tone.text,
        '--summary-subtle': tone.subtle,
      }}
    >
      <div className="insights-summary-card-head">
        <div className="insights-summary-icon">
          <IconComponent size={18} />
        </div>
        <div>
          <div className="insights-summary-label">{card.label}</div>
          <div className="insights-summary-count">
            {hasCount ? `${card.count} รายการ` : 'Amount Focus'}
          </div>
        </div>
      </div>

      <div className="insights-summary-body">
        <div className="insights-summary-value">
          {hasAmount ? formatCurrency(card.amount) : hasCount ? card.count.toLocaleString('en-US') : '-'}
        </div>
        <div className="insights-summary-description">
          {card.description || '-'}
        </div>
      </div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="insights-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="insights-input">
        <option value="">ทั้งหมด</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function MultiSelectFilter({ label, value, onChange, options, size = 4 }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '200px' }}>
      <span style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
        {label}
      </span>
      <select
        multiple
        value={value}
        onChange={(event) =>
          onChange(Array.from(event.target.selectedOptions, (option) => option.value))
        }
        size={Math.min(size, Math.max(options.length || 1, 2))}
        style={{ ...inputStyle, minHeight: '120px', backgroundColor: '#fcfcfd' }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ColumnChooser({ columns, visibleColumns, onToggle }) {
  return (
    <div className="insights-column-chooser">
      <div className="insights-section-label">Visible Columns</div>
      <div className="insights-column-buttons">
        {columns.map((column) => {
          const isVisible = visibleColumns.includes(column.key);
          return (
            <button
              key={column.key}
              type="button"
              onClick={() => onToggle(column.key)}
              className={isVisible ? 'insights-chip-button active' : 'insights-chip-button'}
            >
              {column.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function FlagPill({ flag }) {
  const tone = flagToneStyles[flag.tone] || flagToneStyles.neutral;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 8px',
        borderRadius: '999px',
        backgroundColor: tone.background,
        color: tone.color,
        fontSize: '11px',
        fontWeight: '700',
      }}
    >
      {flag.label}
    </span>
  );
}

function TagPill({ tag }) {
  return (
    <span className="insights-tag-pill">
      {tag}
    </span>
  );
}

const InsightsPage = () => {
  const [metadata, setMetadata] = useState(null);
  const [summary, setSummary] = useState({ cards: [], lastUpdatedAt: '' });
  const [rowsData, setRowsData] = useState({
    items: [],
    pageInfo: pageInfoFallback,
    lastUpdatedAt: '',
    emptyStateMessage: '',
  });
  const [searchDraft, setSearchDraft] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [quickView, setQuickView] = useState('all_records');
  const [projectId, setProjectId] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [entryTypeFilter, setEntryTypeFilter] = useState('');
  const [flowDirectionFilter, setFlowDirectionFilter] = useState('');
  const [tagFilters, setTagFilters] = useState([]);
  const [dateField, setDateField] = useState('event_date');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sortBy, setSortBy] = useState('event_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [exportFormat, setExportFormat] = useState('csv');
  const [duplicateOnly, setDuplicateOnly] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loadingMetadata, setLoadingMetadata] = useState(true);
  const [loadingWarehouse, setLoadingWarehouse] = useState(true);
  const [hasLoadedWarehouseOnce, setHasLoadedWarehouseOnce] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadMetadata = async () => {
      try {
        const result = await getInsightWarehouseFilters();
        if (!isMounted) return;
        setMetadata(result);
        setVisibleColumns((current) =>
          current.length
            ? current
            : (result.columns || [])
                .filter((item) => item.defaultVisible !== false)
                .map((item) => item.key)
        );
      } catch (loadError) {
        if (!isMounted) return;
        setError(loadError.message || 'Failed to load Insight Warehouse filters.');
      } finally {
        if (isMounted) {
          setLoadingMetadata(false);
        }
      }
    };

    loadMetadata();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const requestFilters = {
      q: searchQuery,
      quickView,
      projectId,
      sourceTypes: sourceTypeFilter ? [sourceTypeFilter] : [],
      statuses: statusFilter ? [statusFilter] : [],
      entryTypes: entryTypeFilter ? [entryTypeFilter] : [],
      flowDirections: flowDirectionFilter ? [flowDirectionFilter] : [],
      tags: tagFilters,
      dateField,
      dateFrom,
      dateTo,
      duplicateOnly,
      overdueOnly,
      sortBy,
      sortOrder,
      page,
      pageSize,
    };

    const loadWarehouse = async () => {
      try {
        setLoadingWarehouse(true);
        const [nextSummary, nextRows] = await Promise.all([
          getInsightWarehouseSummary(requestFilters),
          getInsightWarehouseRows(requestFilters),
        ]);

        if (!isMounted) return;
        setSummary(nextSummary);
        setRowsData(nextRows);
        setError('');
      } catch (loadError) {
        if (!isMounted) return;
        setError(loadError.message || 'Failed to load Insight Warehouse data.');
      } finally {
        if (isMounted) {
          setLoadingWarehouse(false);
          setHasLoadedWarehouseOnce(true);
        }
      }
    };

    loadWarehouse();

    return () => {
      isMounted = false;
    };
  }, [dateField, dateFrom, dateTo, duplicateOnly, entryTypeFilter, flowDirectionFilter, overdueOnly, page, pageSize, projectId, quickView, searchQuery, sortBy, sortOrder, sourceTypeFilter, statusFilter, tagFilters]);

  // ✓ Move hooks before early returns to satisfy React Rules of Hooks
  const visibleColumnSet = useMemo(() => new Set(visibleColumns), [visibleColumns]);

  const quickViews = metadata?.quickViews || [];
  const projects = metadata?.projects || [];
  const sourceTypes = metadata?.sourceTypes || [];
  const statuses = metadata?.statuses || [];
  const entryTypes = metadata?.entryTypes || [];
  const flowDirections = metadata?.flowDirections || [];
  const tags = metadata?.tags || [];
  const dateFields = metadata?.dateFields || [];
  const sortFields = metadata?.sortFields || [];
  const exportFormats = metadata?.exportFormats || [];
  const columns = metadata?.columns || [];
  const rows = rowsData.items || [];
  const pageInfo = rowsData.pageInfo || pageInfoFallback;
  const lastUpdatedAt = rowsData.lastUpdatedAt || summary.lastUpdatedAt || metadata?.lastUpdatedAt || '';
  const exportUrl = getInsightWarehouseExportUrl({
    q: searchQuery,
    quickView,
    projectId,
    sourceTypes: sourceTypeFilter ? [sourceTypeFilter] : [],
    statuses: statusFilter ? [statusFilter] : [],
    entryTypes: entryTypeFilter ? [entryTypeFilter] : [],
    flowDirections: flowDirectionFilter ? [flowDirectionFilter] : [],
    tags: tagFilters,
    dateField,
    dateFrom,
    dateTo,
    duplicateOnly,
    overdueOnly,
    sortBy,
    sortOrder,
    format: exportFormat,
  });

  if (!hasLoadedWarehouseOnce || loadingMetadata) {
    return <Loading />;
  }

  if (error && !rowsData.items.length && !loadingWarehouse) {
    return (
      <div
        style={{
          padding: '60px',
          textAlign: 'center',
          color: '#ef4444',
          backgroundColor: 'white',
          borderRadius: '12px',
          margin: '40px',
        }}
      >
        <h2 style={{ marginBottom: '16px' }}>Insight Warehouse Unavailable</h2>
        <p style={{ color: '#6b7280' }}>{error}</p>
        <button onClick={() => window.location.reload()} style={{ ...buttonStyle, marginTop: '24px' }}>
          <RefreshCcw size={16} />
          Reload
        </button>
      </div>
    );
  }

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    setPage(1);
    setSearchQuery(searchDraft.trim());
  };

  const resetFilters = () => {
    setSearchDraft('');
    setSearchQuery('');
    setQuickView('all_records');
    setProjectId('');
    setSourceTypeFilter('');
    setStatusFilter('');
    setEntryTypeFilter('');
    setFlowDirectionFilter('');
    setTagFilters([]);
    setDateField('event_date');
    setDateFrom('');
    setDateTo('');
    setSortBy('event_date');
    setSortOrder('desc');
    setExportFormat('csv');
    setDuplicateOnly(false);
    setOverdueOnly(false);
    setPage(1);
  };

  const getOptionLabel = (options, value) =>
    options.find((option) => option.value === value || option.key === value)?.label || prettifyValue(value);

  const activeQuickView = quickViews.find((item) => item.key === quickView);
  const activeFilters = [
    quickView && quickView !== 'all_records'
      ? {
          key: 'quick-view',
          label: `View: ${activeQuickView?.label || prettifyValue(quickView)}`,
          onRemove: () => {
            setQuickView('all_records');
            setPage(1);
          },
        }
      : null,
    searchQuery
      ? {
          key: 'search',
          label: `Search: ${searchQuery}`,
          onRemove: () => {
            setSearchDraft('');
            setSearchQuery('');
            setPage(1);
          },
        }
      : null,
    projectId
      ? {
          key: 'project',
          label: `Project: ${getOptionLabel(projects, projectId)}`,
          onRemove: () => {
            setProjectId('');
            setPage(1);
          },
        }
      : null,
    sourceTypeFilter
      ? {
          key: 'source',
          label: `Source: ${getOptionLabel(sourceTypes, sourceTypeFilter)}`,
          onRemove: () => {
            setSourceTypeFilter('');
            setPage(1);
          },
        }
      : null,
    statusFilter
      ? {
          key: 'status',
          label: `Status: ${getOptionLabel(statuses, statusFilter)}`,
          onRemove: () => {
            setStatusFilter('');
            setPage(1);
          },
        }
      : null,
    entryTypeFilter
      ? {
          key: 'entry-type',
          label: `Entry: ${getOptionLabel(entryTypes, entryTypeFilter)}`,
          onRemove: () => {
            setEntryTypeFilter('');
            setPage(1);
          },
        }
      : null,
    flowDirectionFilter
      ? {
          key: 'flow',
          label: `Flow: ${getOptionLabel(flowDirections, flowDirectionFilter)}`,
          onRemove: () => {
            setFlowDirectionFilter('');
            setPage(1);
          },
        }
      : null,
    ...tagFilters.map((tag) => ({
      key: `tag-${tag}`,
      label: `Tag: ${getOptionLabel(tags, tag)}`,
      onRemove: () => {
        setTagFilters((current) => current.filter((item) => item !== tag));
        setPage(1);
      },
    })),
    dateFrom
      ? {
          key: 'date-from',
          label: `From: ${dateFrom}`,
          onRemove: () => {
            setDateFrom('');
            setPage(1);
          },
        }
      : null,
    dateTo
      ? {
          key: 'date-to',
          label: `To: ${dateTo}`,
          onRemove: () => {
            setDateTo('');
            setPage(1);
          },
        }
      : null,
    duplicateOnly
      ? {
          key: 'duplicate',
          label: 'Duplicate only',
          onRemove: () => {
            setDuplicateOnly(false);
            setPage(1);
          },
        }
      : null,
    overdueOnly
      ? {
          key: 'overdue',
          label: 'Overdue only',
          onRemove: () => {
            setOverdueOnly(false);
            setPage(1);
          },
        }
      : null,
  ].filter(Boolean);

  return (
    <div className="insights-page">
      <section className="insights-hero">
        <div className="insights-hero-copy">
          <div className="insights-kicker">
            <FileText size={15} />
            Insight Warehouse
          </div>
          <h1>Insight Warehouse</h1>
          <p>
            รวมข้อมูลจาก Input, Installment และ Transaction ไว้ในมุมมองเดียวเพื่อให้ admin ค้นหา กรอง และเปิดงานต่อได้ทันที
          </p>
          <div className="insights-hero-meta">
            <CalendarDays size={15} />
            {lastUpdatedAt ? `Last updated ${formatDateTime(lastUpdatedAt)}` : 'Last updated not available yet'}
          </div>
        </div>

        <div className="insights-actions">
          <a href={exportUrl} className="insights-button insights-button-primary">
            <Download size={16} />
            Export {exportFormat.toUpperCase()}
          </a>
          <button type="button" onClick={resetFilters} className="insights-button">
            <RefreshCcw size={16} />
            Reset
          </button>
        </div>
      </section>

      <nav className="insights-quick-tabs" aria-label="Insight quick views">
        {quickViews.map((item) => (
          <button
            key={item.key}
            type="button"
            className={quickView === item.key ? 'active' : ''}
            onClick={() => {
              setQuickView(item.key || 'all_records');
              setPage(1);
            }}
            title={item.description}
          >
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <section className="insights-filter-panel">
        <form onSubmit={handleSearchSubmit} className="insights-search-form">
          <label className="insights-search-field">
            <span>Global Search</span>
            <div className="insights-search-input-wrap">
              <Search size={17} />
              <input
                type="text"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="ค้นหาเลขเอกสาร, project, actor, note"
              />
            </div>
          </label>

          <FilterSelect
            label="Project"
            value={projectId}
            onChange={(value) => {
              setProjectId(value);
              setPage(1);
            }}
            options={projects}
          />

          <label className="insights-field">
            <span>Date From</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                setPage(1);
              }}
              className="insights-input"
            />
          </label>

          <label className="insights-field">
            <span>Date To</span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                setPage(1);
              }}
              className="insights-input"
            />
          </label>

          <button type="submit" className="insights-button insights-search-button">
            <Search size={16} />
            Search
          </button>

          <button
            type="button"
            onClick={() => setShowAdvancedFilters((current) => !current)}
            className="insights-button insights-advanced-toggle"
            aria-expanded={showAdvancedFilters}
          >
            <SlidersHorizontal size={16} />
            Advanced
            <ChevronDown size={16} className={showAdvancedFilters ? 'open' : ''} />
          </button>
        </form>

        {activeFilters.length ? (
          <div className="insights-active-filters" aria-label="Active filters">
            {activeFilters.map((filter) => (
              <button key={filter.key} type="button" onClick={filter.onRemove}>
                {filter.label}
                <X size={13} />
              </button>
            ))}
          </div>
        ) : null}

        {showAdvancedFilters ? (
          <div className="insights-advanced-panel">
            <div className="insights-filter-grid">
              <FilterSelect label="Date Field" value={dateField} onChange={(value) => { setDateField(value || 'event_date'); setPage(1); }} options={dateFields} />
              <FilterSelect label="Source" value={sourceTypeFilter} onChange={(value) => { setSourceTypeFilter(value); setPage(1); }} options={sourceTypes} />
              <FilterSelect label="Status" value={statusFilter} onChange={(value) => { setStatusFilter(value); setPage(1); }} options={statuses} />
              <FilterSelect label="Entry Type" value={entryTypeFilter} onChange={(value) => { setEntryTypeFilter(value); setPage(1); }} options={entryTypes} />
              <FilterSelect label="Flow Direction" value={flowDirectionFilter} onChange={(value) => { setFlowDirectionFilter(value); setPage(1); }} options={flowDirections} />
              <MultiSelectFilter
                label="Tags"
                value={tagFilters}
                onChange={(value) => {
                  setTagFilters(value);
                  setPage(1);
                }}
                options={tags}
                size={4}
              />
              <FilterSelect label="Sort By" value={sortBy} onChange={(value) => setSortBy(value)} options={sortFields} />
              <FilterSelect
                label="Sort Order"
                value={sortOrder}
                onChange={(value) => setSortOrder(value || 'desc')}
                options={[
                  { value: 'desc', label: 'Newest First' },
                  { value: 'asc', label: 'Oldest First' },
                ]}
              />
              <FilterSelect
                label="Export Format"
                value={exportFormat}
                onChange={(value) => setExportFormat(value || 'csv')}
                options={exportFormats}
              />
            </div>

            <div className="insights-toggle-row">
              <button type="button" onClick={() => { setDuplicateOnly((current) => !current); setPage(1); }} className={duplicateOnly ? 'insights-chip-button active' : 'insights-chip-button'}>
                <FilterIcon size={15} />
                Duplicate Only
              </button>
              <button type="button" onClick={() => { setOverdueOnly((current) => !current); setPage(1); }} className={overdueOnly ? 'insights-chip-button active' : 'insights-chip-button'}>
                <AlertTriangle size={15} />
                Overdue Only
              </button>
            </div>

            <ColumnChooser
              columns={columns}
              visibleColumns={visibleColumns}
              onToggle={(columnKey) =>
                setVisibleColumns((current) =>
                  current.includes(columnKey)
                    ? (current.length > 1 ? current.filter((item) => item !== columnKey) : current)
                    : [...current, columnKey]
                )
              }
            />
          </div>
        ) : null}
      </section>

      <section className="insights-summary-grid">
        {(summary.cards || []).map((card) => (
          <SummaryCard key={card.key} card={card} />
        ))}
      </section>

      {error ? (
        <div className="insights-error">
          {error}
        </div>
      ) : null}

      <section className="insights-records-panel">
        <div className="insights-records-header">
          <div>
            <h2>Warehouse Records</h2>
            <p>
              {pageInfo.totalItems} records found{loadingWarehouse ? ' • refreshing...' : ''}
            </p>
          </div>
          <div className="insights-page-count">
            Page {pageInfo.page} of {Math.max(pageInfo.totalPages, 1)}
          </div>
        </div>

        <div className="insights-table-wrap">
          <table className="insights-table">
            <thead>
              <tr>
                {visibleColumnSet.has('source_type') ? <th>Source</th> : null}
                {visibleColumnSet.has('reference_no') ? <th>Record</th> : null}
                {visibleColumnSet.has('project_name') ? <th>Project / Actor</th> : null}
                {visibleColumnSet.has('status') ? <th>Status</th> : null}
                {visibleColumnSet.has('amount') ? <th className="numeric">Amount</th> : null}
                {visibleColumnSet.has('event_date') ? <th>Event</th> : null}
                {visibleColumnSet.has('due_date') ? <th>Due Date</th> : null}
                {visibleColumnSet.has('tags') ? <th>Tags</th> : null}
                {visibleColumnSet.has('flags') ? <th>Flags</th> : null}
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.length > 0 ? (
                rows.map((row) => (
                  <tr
                    key={row.id}
                    className={`${row.isOverdue ? 'is-overdue' : ''} ${row.isDuplicateFlag ? 'is-duplicate' : ''}`}
                  >
                    {visibleColumnSet.has('source_type') ? (
                      <td>
                        <div className="insights-source-cell">
                          <strong>{sourceTypeLabel(row.sourceType)}</strong>
                          <span>
                            {row.flowDirection === 'INFLOW' ? 'Cash In' : row.flowDirection === 'OUTFLOW' ? 'Cash Out' : prettifyValue(row.flowDirection)}
                          </span>
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('reference_no') ? (
                      <td className="insights-record-title-cell">
                        <strong>{row.title || '-'}</strong>
                        <span>Ref: {row.referenceNo || '-'}</span>
                        {row.description ? <p>{row.description}</p> : null}
                      </td>
                    ) : null}
                    {visibleColumnSet.has('project_name') ? (
                      <td className="insights-project-cell">
                        <strong>{row.projectName || '-'}</strong>
                        <span>{row.actorName || row.actorId || '-'}</span>
                        <small>{prettifyValue(row.requestType || row.entryType || '-')}</small>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('status') ? (
                      <td>
                        <span className={row.isOverdue ? 'insights-status-pill danger' : 'insights-status-pill'}>
                          {prettifyValue(row.status)}
                        </span>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('amount') ? (
                      <td className="numeric insights-amount-cell">
                        <strong>{row.amount == null ? '-' : formatCurrency(row.amount)}</strong>
                        <span>{row.currency || 'THB'}</span>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('event_date') ? (
                      <td className="insights-date-cell">{formatDate(row.eventDate)}</td>
                    ) : null}
                    {visibleColumnSet.has('due_date') ? (
                      <td className="insights-date-cell">{formatDate(row.dueDate)}</td>
                    ) : null}
                    {visibleColumnSet.has('tags') ? (
                      <td>
                        <div className="insights-tag-list">
                          {row.tags.length > 0
                            ? row.tags.map((tag) => <TagPill key={`${row.id}-${tag}`} tag={tag} />)
                            : <span className="insights-muted-cell">-</span>}
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('flags') ? (
                      <td>
                        <div className="insights-flag-list">
                          {row.flags.length > 0
                            ? row.flags.map((flag) => <FlagPill key={`${row.id}-${flag.key}`} flag={flag} />)
                            : <FlagPill flag={{ label: 'Normal', tone: 'neutral' }} />}
                        </div>
                      </td>
                    ) : null}
                    <td>
                      {row.navigationTarget?.path ? (
                        <Link to={row.navigationTarget.path} className="insights-open-link">
                          {row.navigationTarget.label || 'Open'}
                          <ExternalLink size={14} />
                        </Link>
                      ) : (
                        <span className="insights-no-action">No action</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={visibleColumns.length + 1}>
                    <div className="insights-empty-state">
                      <Search size={38} strokeWidth={1.5} />
                      <strong>{rowsData.emptyStateMessage || 'ไม่พบข้อมูลในขณะนี้'}</strong>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {rows.length > 0 ? (
          <div className="insights-mobile-records">
            {rows.map((row) => (
              <article
                key={row.id}
                className={`${row.isOverdue ? 'is-overdue' : ''} ${row.isDuplicateFlag ? 'is-duplicate' : ''}`}
              >
                <div className="insights-mobile-record-head">
                  <div>
                    <span>{sourceTypeLabel(row.sourceType)}</span>
                    <strong>{row.title || '-'}</strong>
                  </div>
                  <span className={row.isOverdue ? 'insights-status-pill danger' : 'insights-status-pill'}>
                    {prettifyValue(row.status)}
                  </span>
                </div>
                <p>{row.description || `Ref: ${row.referenceNo || '-'}`}</p>
                {row.tags.length > 0 ? (
                  <div className="insights-tag-list">
                    {row.tags.map((tag) => <TagPill key={`${row.id}-mobile-tag-${tag}`} tag={tag} />)}
                  </div>
                ) : null}
                <dl>
                  <div>
                    <dt>Project</dt>
                    <dd>{row.projectName || '-'}</dd>
                  </div>
                  <div>
                    <dt>Amount</dt>
                    <dd>{row.amount == null ? '-' : formatCurrency(row.amount)}</dd>
                  </div>
                  <div>
                    <dt>Event</dt>
                    <dd>{formatDate(row.eventDate)}</dd>
                  </div>
                  <div>
                    <dt>Due</dt>
                    <dd>{formatDate(row.dueDate)}</dd>
                  </div>
                </dl>
                <div className="insights-mobile-record-foot">
                  <div className="insights-flag-list">
                    {row.flags.length > 0
                      ? row.flags.map((flag) => <FlagPill key={`${row.id}-mobile-${flag.key}`} flag={flag} />)
                      : <FlagPill flag={{ label: 'Normal', tone: 'neutral' }} />}
                  </div>
                  {row.navigationTarget?.path ? (
                    <Link to={row.navigationTarget.path} className="insights-open-link">
                      {row.navigationTarget.label || 'Open'}
                      <ExternalLink size={14} />
                    </Link>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : null}

        <div className="insights-pagination">
          <div>
            Showing {(pageInfo.page - 1) * pageInfo.pageSize + (rows.length ? 1 : 0)}-{(pageInfo.page - 1) * pageInfo.pageSize + rows.length} of {pageInfo.totalItems}
          </div>

          <div className="insights-pagination-actions">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={!pageInfo.hasPrevious}
              className="insights-button"
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={!pageInfo.hasNext}
              className="insights-button"
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default InsightsPage;
