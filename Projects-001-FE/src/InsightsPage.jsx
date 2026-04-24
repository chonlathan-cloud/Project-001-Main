import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Filter as FilterIcon,
  RefreshCcw,
  Search,
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

const activeButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#111827',
  borderColor: '#111827',
  color: 'white',
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

  return (
    <div
      style={{
        backgroundColor: tone.background,
        border: `1px solid ${tone.border}`,
        borderRadius: '24px',
        padding: '22px',
        minHeight: '146px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        boxShadow: '0 8px 30px rgba(15, 23, 42, 0.04)',
        flex: '1 1 240px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(255,255,255,0.7)',
            color: tone.text,
          }}
        >
          <AlertTriangle size={18} />
        </div>
        <div>
          <div style={{ fontSize: '15px', fontWeight: '700', color: tone.text }}>{card.label}</div>
          <div style={{ fontSize: '12px', color: tone.subtle }}>
            {card.count == null ? 'Amount Focus' : `${card.count} รายการ`}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 'auto' }}>
        <div style={{ fontSize: '26px', fontWeight: '800', color: tone.text }}>
          {card.amount == null ? '-' : formatCurrency(card.amount)}
        </div>
        <div style={{ marginTop: '8px', fontSize: '12px', color: tone.subtle }}>
          {card.description || '-'}
        </div>
      </div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px' }}>
      <span style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
        {label}
      </span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
        Visible Columns
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {columns.map((column) => {
          const isVisible = visibleColumns.includes(column.key);
          return (
            <button
              key={column.key}
              type="button"
              onClick={() => onToggle(column.key)}
              style={isVisible ? activeButtonStyle : buttonStyle}
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
  const [dateField, setDateField] = useState('event_date');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sortBy, setSortBy] = useState('event_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [exportFormat, setExportFormat] = useState('csv');
  const [duplicateOnly, setDuplicateOnly] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
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
  }, [dateField, dateFrom, dateTo, duplicateOnly, entryTypeFilter, flowDirectionFilter, overdueOnly, page, pageSize, projectId, quickView, searchQuery, sortBy, sortOrder, sourceTypeFilter, statusFilter]);

  // ✓ Move hooks before early returns to satisfy React Rules of Hooks
  const visibleColumnSet = useMemo(() => new Set(visibleColumns), [visibleColumns]);

  const quickViews = metadata?.quickViews || [];
  const projects = metadata?.projects || [];
  const sourceTypes = metadata?.sourceTypes || [];
  const statuses = metadata?.statuses || [];
  const entryTypes = metadata?.entryTypes || [];
  const flowDirections = metadata?.flowDirections || [];
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
          borderRadius: '24px',
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

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px', marginBottom: '28px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '32px', fontWeight: '800', margin: '0 0 8px 0', color: '#111827' }}>
            Insight Warehouse
          </h1>
          <p style={{ color: '#6B7280', margin: 0, fontSize: '14px', maxWidth: '720px' }}>
            รวมข้อมูลจาก Input, Installment และ Transaction ไว้ในมุมมองเดียวเพื่อให้ admin ค้นหา กรอง และเปิดงานต่อได้ทันที
          </p>
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#9ca3af' }}>
            {lastUpdatedAt ? `Last updated ${formatDateTime(lastUpdatedAt)}` : 'Last updated not available yet'}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <a href={exportUrl} style={{ ...buttonStyle, textDecoration: 'none' }}>
            <ExternalLink size={16} />
            Export {exportFormat.toUpperCase()}
          </a>
          <button type="button" onClick={resetFilters} style={buttonStyle}>
            <RefreshCcw size={16} />
            Reset Filters
          </button>
        </div>
      </div>

      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '24px',
          padding: '24px',
          border: '1px solid #f1f5f9',
          marginBottom: '24px',
          boxShadow: '0 10px 30px rgba(15, 23, 42, 0.04)',
          position: 'sticky',
          top: '18px',
          zIndex: 5,
        }}
      >
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ flex: '1 1 320px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
              Global Search
            </span>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="ค้นหาเลขเอกสาร, project, actor, note"
                style={{ ...inputStyle, paddingLeft: '40px' }}
              />
              <Search
                size={18}
                color="#9ca3af"
                style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
              />
            </div>
          </label>

          <button type="submit" style={buttonStyle}>
            <Search size={16} />
            Search
          </button>
        </form>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
          <FilterSelect label="Quick View" value={quickView} onChange={(value) => { setQuickView(value || 'all_records'); setPage(1); }} options={quickViews.map((item) => ({ value: item.key, label: item.label }))} />
          <FilterSelect label="Project" value={projectId} onChange={(value) => { setProjectId(value); setPage(1); }} options={projects} />
          <FilterSelect label="Date Field" value={dateField} onChange={(value) => { setDateField(value || 'event_date'); setPage(1); }} options={dateFields} />
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

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '18px', alignItems: 'flex-start' }}>
          <FilterSelect label="Source" value={sourceTypeFilter} onChange={(value) => { setSourceTypeFilter(value); setPage(1); }} options={sourceTypes} />
          <FilterSelect label="Status" value={statusFilter} onChange={(value) => { setStatusFilter(value); setPage(1); }} options={statuses} />
          <FilterSelect label="Entry Type" value={entryTypeFilter} onChange={(value) => { setEntryTypeFilter(value); setPage(1); }} options={entryTypes} />
          <FilterSelect label="Flow Direction" value={flowDirectionFilter} onChange={(value) => { setFlowDirectionFilter(value); setPage(1); }} options={flowDirections} />
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '18px' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
              Date From
            </span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => { setDateFrom(event.target.value); setPage(1); }}
              style={inputStyle}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', textTransform: 'uppercase' }}>
              Date To
            </span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => { setDateTo(event.target.value); setPage(1); }}
              style={inputStyle}
            />
          </label>
        </div>

        <div style={{ marginTop: '18px' }}>
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

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '18px' }}>
          <button type="button" onClick={() => { setDuplicateOnly((current) => !current); setPage(1); }} style={duplicateOnly ? activeButtonStyle : buttonStyle}>
            <FilterIcon size={15} />
            Duplicate Only
          </button>
          <button type="button" onClick={() => { setOverdueOnly((current) => !current); setPage(1); }} style={overdueOnly ? activeButtonStyle : buttonStyle}>
            <AlertTriangle size={15} />
            Overdue Only
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap', marginBottom: '24px' }}>
        {(summary.cards || []).map((card) => (
          <SummaryCard key={card.key} card={card} />
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '24px',
          padding: '28px',
          border: '1px solid #f1f5f9',
          boxShadow: '0 10px 30px rgba(15, 23, 42, 0.04)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: '800', margin: 0, color: '#111827' }}>
              Warehouse Records
            </h2>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#6b7280' }}>
              {pageInfo.totalItems} records found{loadingWarehouse ? ' • refreshing…' : ''}
            </p>
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>
            Page {pageInfo.page} of {Math.max(pageInfo.totalPages, 1)}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 8px', textAlign: 'left' }}>
            <thead>
              <tr style={{ color: '#9ca3af', fontSize: '12px', textTransform: 'uppercase' }}>
                {visibleColumnSet.has('source_type') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Source</th> : null}
                {visibleColumnSet.has('reference_no') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Record</th> : null}
                {visibleColumnSet.has('project_name') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Project / Actor</th> : null}
                {visibleColumnSet.has('status') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Status</th> : null}
                {visibleColumnSet.has('amount') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Amount</th> : null}
                {visibleColumnSet.has('event_date') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Event</th> : null}
                {visibleColumnSet.has('due_date') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Due Date</th> : null}
                {visibleColumnSet.has('flags') ? <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Flags</th> : null}
                <th style={{ padding: '0 16px 10px 16px', fontWeight: '700' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.length > 0 ? (
                rows.map((row) => (
                  <tr key={row.id} style={{ backgroundColor: '#fafaf9', color: '#111827' }}>
                    {visibleColumnSet.has('source_type') ? (
                      <td style={{ padding: '16px', borderTopLeftRadius: '16px', borderBottomLeftRadius: '16px', verticalAlign: 'top' }}>
                        <div style={{ fontSize: '12px', fontWeight: '800', color: '#374151', letterSpacing: '0.04em' }}>
                          {sourceTypeLabel(row.sourceType)}
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
                          {row.flowDirection === 'INFLOW' ? 'Cash In' : row.flowDirection === 'OUTFLOW' ? 'Cash Out' : prettifyValue(row.flowDirection)}
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('reference_no') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '260px' }}>
                        <div style={{ fontSize: '14px', fontWeight: '700' }}>{row.title || '-'}</div>
                        <div style={{ marginTop: '6px', fontSize: '12px', color: '#6b7280' }}>
                          Ref: {row.referenceNo || '-'}
                        </div>
                        {row.description ? (
                          <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280', lineHeight: 1.5 }}>
                            {row.description}
                          </div>
                        ) : null}
                      </td>
                    ) : null}
                    {visibleColumnSet.has('project_name') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '220px' }}>
                        <div style={{ fontSize: '13px', fontWeight: '700' }}>{row.projectName || '-'}</div>
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280' }}>
                          {row.actorName || row.actorId || '-'}
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
                          {prettifyValue(row.requestType || row.entryType || '-')}
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('status') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top' }}>
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '6px 10px',
                            borderRadius: '999px',
                            backgroundColor: row.isOverdue ? '#fee2e2' : '#f3f4f6',
                            color: row.isOverdue ? '#b91c1c' : '#374151',
                            fontSize: '12px',
                            fontWeight: '700',
                          }}
                        >
                          {prettifyValue(row.status)}
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('amount') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '150px' }}>
                        <div style={{ fontSize: '14px', fontWeight: '800' }}>
                          {row.amount == null ? '-' : formatCurrency(row.amount)}
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
                          {row.currency || 'THB'}
                        </div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('event_date') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '160px' }}>
                        <div style={{ fontSize: '13px', fontWeight: '700' }}>{formatDate(row.eventDate)}</div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('due_date') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '160px' }}>
                        <div style={{ fontSize: '13px', fontWeight: '700' }}>{formatDate(row.dueDate)}</div>
                      </td>
                    ) : null}
                    {visibleColumnSet.has('flags') ? (
                      <td style={{ padding: '16px', verticalAlign: 'top', minWidth: '180px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {row.flags.length > 0 ? row.flags.map((flag) => <FlagPill key={`${row.id}-${flag.key}`} flag={flag} />) : <FlagPill flag={{ label: 'Normal', tone: 'neutral' }} />}
                        </div>
                      </td>
                    ) : null}
                    <td style={{ padding: '16px', borderTopRightRadius: '16px', borderBottomRightRadius: '16px', verticalAlign: 'top' }}>
                      {row.navigationTarget?.path ? (
                        <Link
                          to={row.navigationTarget.path}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            color: '#0f766e',
                            fontSize: '13px',
                            fontWeight: '700',
                            textDecoration: 'none',
                          }}
                        >
                          {row.navigationTarget.label || 'Open'}
                          <ExternalLink size={14} />
                        </Link>
                      ) : (
                        <span style={{ fontSize: '12px', color: '#9ca3af' }}>No action</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={visibleColumns.length + 1} style={{ textAlign: 'center', padding: '56px 20px', color: '#9ca3af' }}>
                    <Search size={42} strokeWidth={1.5} style={{ marginBottom: '16px' }} />
                    <div style={{ fontSize: '15px', fontWeight: '700', color: '#6b7280' }}>
                      {rowsData.emptyStateMessage || 'ไม่พบข้อมูลในขณะนี้'}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginTop: '24px', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '12px', color: '#6b7280' }}>
            Showing {(pageInfo.page - 1) * pageInfo.pageSize + (rows.length ? 1 : 0)}-{(pageInfo.page - 1) * pageInfo.pageSize + rows.length} of {pageInfo.totalItems}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={!pageInfo.hasPrevious}
              style={{
                ...buttonStyle,
                opacity: pageInfo.hasPrevious ? 1 : 0.5,
                cursor: pageInfo.hasPrevious ? 'pointer' : 'not-allowed',
              }}
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={!pageInfo.hasNext}
              style={{
                ...buttonStyle,
                opacity: pageInfo.hasNext ? 1 : 0.5,
                cursor: pageInfo.hasNext ? 'pointer' : 'not-allowed',
              }}
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default InsightsPage;
