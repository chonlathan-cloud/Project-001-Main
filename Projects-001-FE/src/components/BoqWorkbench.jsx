import { useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Search,
  Table2,
} from 'lucide-react';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatCurrency = (value) => `${currencyFormatter.format(Number(value || 0))} THB`;
const formatPercent = (value) => (value == null ? '-' : `${Number(value || 0).toFixed(1)}%`);
const displayBudget = (row, displayKey, fallbackKey) =>
  row?.[displayKey] == null ? row?.[fallbackKey] : row?.[displayKey];

const VIEW_OPTIONS = [
  { value: 'compare', label: 'Compare' },
  { value: 'customer', label: 'Customer' },
  { value: 'subcontractor', label: 'Subcontractor' },
];

const PRIMARY_SHEETS = ['EE', 'AC', 'IN', 'SN'];
const TABLE_COLUMN_COUNT = 8;

const normalizeSheetName = (value) => String(value || '').trim();
const normalizeSheetKey = (value) => normalizeSheetName(value).toUpperCase();

const buildSheetOptions = (sheetNames = [], rows = []) => {
  const countsBySheet = rows.reduce((accumulator, row) => {
    const sheetKey = normalizeSheetKey(row.sheetName);
    if (!sheetKey) return accumulator;
    return {
      ...accumulator,
      [sheetKey]: (accumulator[sheetKey] || 0) + 1,
    };
  }, {});

  const apiSheets = sheetNames
    .map((sheetName) => normalizeSheetName(sheetName))
    .filter(Boolean);
  const rowSheets = rows
    .map((row) => normalizeSheetName(row.sheetName))
    .filter(Boolean);
  const orderedSheets = [...PRIMARY_SHEETS, ...apiSheets, ...rowSheets]
    .filter((sheetName, index, list) => {
      const sheetKey = normalizeSheetKey(sheetName);
      return sheetKey && list.findIndex((item) => normalizeSheetKey(item) === sheetKey) === index;
    });

  return [
    { value: 'ALL', label: 'All sheets', count: rows.length },
    ...orderedSheets.map((sheetName) => {
      const sheetKey = normalizeSheetKey(sheetName);
      return {
        value: sheetKey,
        label: sheetName,
        count: countsBySheet[sheetKey] || 0,
      };
    }),
  ];
};

const matchStatusLabel = (status) => {
  if (status === 'CUSTOMER_ONLY') return 'Customer only';
  if (status === 'SUBCONTRACTOR_ONLY') return 'Subcontractor only';
  return 'Matched';
};

const getRowKey = (mode, node, path) => `${mode}:${node?.key || node?.itemNo || path}`;

const flattenTree = (nodes, mode, depth = 0, parentPath = '') =>
  (nodes || []).flatMap((node, index) => {
    const path = parentPath ? `${parentPath}.${index}` : `${index}`;
    const children = Array.isArray(node.children) ? node.children : [];
    const row = {
      ...node,
      mode,
      depth,
      path,
      rowKey: getRowKey(mode, node, path),
      hasChildren: children.length > 0,
      searchText: [
        node.itemNo,
        node.description,
        node.sheetName,
        node.unit,
        node.matchStatus,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    };

    return [row, ...flattenTree(children, mode, depth + 1, path)];
  });

const getAllExpandableKeys = (rows) => rows.filter((row) => row.hasChildren).map((row) => row.rowKey);

function buildVisibleRows(nodes, mode, options, depth = 0, parentPath = '') {
  const { expandedKeys, query, sheetFilter } = options;
  const hasSearch = Boolean(query);
  const activeSheetKey = normalizeSheetKey(sheetFilter);
  const hasSheetFilter = Boolean(activeSheetKey && activeSheetKey !== 'ALL');

  return (nodes || []).flatMap((node, index) => {
    const path = parentPath ? `${parentPath}.${index}` : `${index}`;
    const children = Array.isArray(node.children) ? node.children : [];
    const rowKey = getRowKey(mode, node, path);
    const row = {
      ...node,
      mode,
      depth,
      path,
      rowKey,
      hasChildren: children.length > 0,
      searchText: [
        node.itemNo,
        node.description,
        node.sheetName,
        node.unit,
        node.matchStatus,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    };
    const childRows = buildVisibleRows(children, mode, options, depth + 1, path);
    const matchesQuery = !hasSearch || row.searchText.includes(query);
    const matchesSheet = !hasSheetFilter || normalizeSheetKey(row.sheetName) === activeSheetKey;
    const matchesSelf = matchesQuery && matchesSheet;
    const shouldShowBranch = matchesSelf || childRows.length > 0;
    const shouldShowChildren = hasSearch || expandedKeys.has(rowKey);

    if (!shouldShowBranch) return [];
    return [row, ...(shouldShowChildren ? childRows : [])];
  });
}

const buildRowsWithSheetSections = (rows = [], sheetFilter) => {
  const activeSheetKey = normalizeSheetKey(sheetFilter);
  const hasSheetFilter = Boolean(activeSheetKey && activeSheetKey !== 'ALL');

  if (hasSheetFilter) {
    return rows.map((row) => ({ type: 'row', key: row.rowKey, row }));
  }

  const countsBySheet = rows.reduce((accumulator, row) => {
    const sheetKey = normalizeSheetKey(row.sheetName) || 'UNASSIGNED';
    return {
      ...accumulator,
      [sheetKey]: (accumulator[sheetKey] || 0) + 1,
    };
  }, {});
  let previousSheetKey = '';

  return rows.flatMap((row, index) => {
    const sheetName = normalizeSheetName(row.sheetName) || 'Unassigned';
    const sheetKey = normalizeSheetKey(sheetName) || 'UNASSIGNED';
    const nextRows = [];

    if (sheetKey !== previousSheetKey) {
      nextRows.push({
        type: 'section',
        key: `sheet-section-${sheetKey}-${index}`,
        sheetName,
        count: countsBySheet[sheetKey] || 0,
      });
      previousSheetKey = sheetKey;
    }

    nextRows.push({ type: 'row', key: row.rowKey, row });
    return nextRows;
  });
};

function NumericCell({ children, tone = 'neutral' }) {
  return (
    <td className={`boq-workbench-number boq-workbench-number-${tone}`}>
      {children}
    </td>
  );
}

function MatchBadge({ status }) {
  return (
    <span className={`boq-workbench-status boq-workbench-status-${status || 'MATCHED'}`}>
      {matchStatusLabel(status)}
    </span>
  );
}

function EmptyState({ activeView, sheetFilter, query }) {
  const sheetKey = normalizeSheetKey(sheetFilter);
  const hasSheetFilter = Boolean(sheetKey && sheetKey !== 'ALL');

  return (
    <div className="boq-workbench-empty">
      <Table2 size={22} />
      <strong>No BOQ rows found</strong>
      <span>
        {query
          ? `No ${activeView} rows match "${query}".`
          : hasSheetFilter
            ? `No ${activeView} rows in sheet ${sheetFilter}.`
            : `No ${activeView} BOQ rows are available yet.`}
      </span>
    </div>
  );
}

export default function BoqWorkbench({
  activeView,
  onActiveViewChange,
  sheetFilter,
  onSheetFilterChange,
  sheetNames,
  customerTree,
  subcontractorTree,
  compareTree,
}) {
  const [queryDraft, setQueryDraft] = useState('');
  const [expandedState, setExpandedState] = useState(() => ({
    signature: '',
    keys: [],
  }));
  const activeTree = activeView === 'compare'
    ? compareTree
    : activeView === 'customer'
      ? customerTree
      : subcontractorTree;
  const normalizedQuery = queryDraft.trim().toLowerCase();

  const allRows = useMemo(
    () => flattenTree(activeTree, activeView),
    [activeTree, activeView]
  );
  const sheetOptions = useMemo(
    () => buildSheetOptions(sheetNames, allRows),
    [sheetNames, allRows]
  );
  const expandableKeys = useMemo(() => getAllExpandableKeys(allRows), [allRows]);
  const rootKeys = useMemo(
    () => allRows.filter((row) => row.depth === 0 && row.hasChildren).map((row) => row.rowKey),
    [allRows]
  );
  const rootKeySignature = useMemo(() => rootKeys.join('|'), [rootKeys]);
  const expandedKeys = useMemo(
    () =>
      new Set(
        expandedState.signature === rootKeySignature
          ? expandedState.keys
          : []
      ),
    [expandedState, rootKeySignature]
  );
  const visibleRows = useMemo(
    () =>
      buildVisibleRows(activeTree, activeView, {
        expandedKeys,
        query: normalizedQuery,
        sheetFilter,
      }),
    [activeTree, activeView, expandedKeys, normalizedQuery, sheetFilter]
  );
  const displayRows = useMemo(
    () => buildRowsWithSheetSections(visibleRows, sheetFilter),
    [visibleRows, sheetFilter]
  );

  const toggleRow = (rowKey) => {
    setExpandedState((current) => {
      const next = new Set(current.signature === rootKeySignature ? current.keys : []);
      if (next.has(rowKey)) {
        next.delete(rowKey);
      } else {
        next.add(rowKey);
      }
      return {
        signature: rootKeySignature,
        keys: Array.from(next),
      };
    });
  };

  const expandAll = () => {
    setExpandedState({
      signature: rootKeySignature,
      keys: expandableKeys,
    });
  };

  const collapseAll = () => {
    setExpandedState({
      signature: rootKeySignature,
      keys: [],
    });
  };

  const selectSheetFilter = (nextSheetFilter) => {
    onSheetFilterChange(nextSheetFilter);
    setExpandedState({
      signature: rootKeySignature,
      keys: [],
    });
  };

  return (
    <section className="boq-workbench card">
      <div className="boq-workbench-header">
        <div>
          <div className="boq-workbench-kicker">
            <Table2 size={16} />
            BOQ Workbench
          </div>
          <h2>Bill of Quantities</h2>
          <p>
            Inspect WBS hierarchy, sheet source, quantities, material/labor split, and customer vs subcontractor variance in a table layout.
          </p>
        </div>
        <div className="boq-workbench-count">
          <span>{visibleRows.length}</span>
          <small>visible rows</small>
        </div>
      </div>

      <div className="boq-workbench-toolbar">
        <div className="boq-workbench-tabs" aria-label="BOQ view">
          {VIEW_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={activeView === option.value ? 'active' : ''}
              onClick={() => onActiveViewChange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <label className="boq-workbench-search">
          <Search size={16} />
          <input
            value={queryDraft}
            onChange={(event) => setQueryDraft(event.target.value)}
            placeholder="Search item no. or description"
            type="search"
          />
        </label>

        <div className="boq-workbench-actions">
          <button type="button" onClick={expandAll} disabled={!expandableKeys.length}>
            <ChevronsUpDown size={16} />
            Expand
          </button>
          <button type="button" onClick={collapseAll} disabled={!expandableKeys.length}>
            <ChevronsDownUp size={16} />
            Collapse
          </button>
        </div>
      </div>

      <div className="boq-workbench-sheet-filter" aria-label="Filter by BOQ sheet">
        {sheetOptions.map((option) => {
          const isActive = normalizeSheetKey(sheetFilter) === normalizeSheetKey(option.value);
          return (
            <button
              key={option.value}
              type="button"
              className={`${isActive ? 'active' : ''} ${option.count ? '' : 'is-empty'}`}
              onClick={() => selectSheetFilter(option.value)}
              aria-pressed={isActive}
            >
              <span>{option.label}</span>
              <strong>{option.count}</strong>
            </button>
          );
        })}
      </div>

      <div className="boq-workbench-table-wrap">
        {visibleRows.length ? (
          <table className="boq-workbench-table">
            <thead>
              {activeView === 'compare' ? (
                <tr>
                  <th>Item No.</th>
                  <th>Description</th>
                  <th>Sheet</th>
                  <th>Status</th>
                  <th className="numeric">Customer Total</th>
                  <th className="numeric">Sub Total</th>
                  <th className="numeric">Variance</th>
                  <th className="numeric">Margin</th>
                </tr>
              ) : (
                <tr>
                  <th>Item No.</th>
                  <th>Description</th>
                  <th>Sheet</th>
                  <th>Unit</th>
                  <th className="numeric">Qty</th>
                  <th className="numeric">Material</th>
                  <th className="numeric">Labor</th>
                  <th className="numeric">Total</th>
                </tr>
              )}
            </thead>
            <tbody>
              {displayRows.map((entry) => {
                if (entry.type === 'section') {
                  return (
                    <tr key={entry.key} className="boq-workbench-sheet-section-row">
                      <td colSpan={TABLE_COLUMN_COUNT}>
                        <div className="boq-workbench-sheet-section">
                          <span>Sheet</span>
                          <strong>{entry.sheetName}</strong>
                          <small>{entry.count} visible rows</small>
                        </div>
                      </td>
                    </tr>
                  );
                }

                const row = entry.row;
                const varianceTone = row.variance > 0 ? 'positive' : row.variance < 0 ? 'danger' : 'neutral';
                const isExpanded = expandedKeys.has(row.rowKey);

                return activeView === 'compare' ? (
                  <tr key={row.rowKey} className={`boq-workbench-row depth-${Math.min(row.depth, 3)}`}>
                    <td className="boq-workbench-item-no">{row.itemNo || '-'}</td>
                    <td>
                      <div
                        className="boq-workbench-description"
                        style={{ '--boq-depth': row.depth }}
                      >
                        <button
                          type="button"
                          onClick={() => toggleRow(row.rowKey)}
                          disabled={!row.hasChildren}
                          aria-label={isExpanded ? 'Collapse BOQ row' : 'Expand BOQ row'}
                        >
                          {row.hasChildren ? (
                            isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />
                          ) : null}
                        </button>
                        <div>
                          <strong>{row.description || '-'}</strong>
                          <span>WBS Level {row.wbsLevel} {row.unit ? `- Unit ${row.unit}` : ''}</span>
                        </div>
                      </div>
                    </td>
                    <td><span className="boq-workbench-sheet">{row.sheetName || '-'}</span></td>
                    <td><MatchBadge status={row.matchStatus} /></td>
                    <NumericCell>{formatCurrency(row.customerTotalBudget)}</NumericCell>
                    <NumericCell>{formatCurrency(row.subcontractorTotalBudget)}</NumericCell>
                    <NumericCell tone={varianceTone}>{formatCurrency(row.variance)}</NumericCell>
                    <NumericCell tone={varianceTone}>{formatPercent(row.marginPercent)}</NumericCell>
                  </tr>
                ) : (
                  <tr key={row.rowKey} className={`boq-workbench-row depth-${Math.min(row.depth, 3)}`}>
                    <td className="boq-workbench-item-no">{row.itemNo || '-'}</td>
                    <td>
                      <div
                        className="boq-workbench-description"
                        style={{ '--boq-depth': row.depth }}
                      >
                        <button
                          type="button"
                          onClick={() => toggleRow(row.rowKey)}
                          disabled={!row.hasChildren}
                          aria-label={isExpanded ? 'Collapse BOQ row' : 'Expand BOQ row'}
                        >
                          {row.hasChildren ? (
                            isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />
                          ) : null}
                        </button>
                        <div>
                          <strong>{row.description || '-'}</strong>
                          <span>WBS Level {row.wbsLevel}</span>
                        </div>
                      </div>
                    </td>
                    <td><span className="boq-workbench-sheet">{row.sheetName || '-'}</span></td>
                    <td>{row.unit || '-'}</td>
                    <NumericCell>{row.qty == null ? '-' : currencyFormatter.format(row.qty)}</NumericCell>
                    <NumericCell>
                      {formatCurrency(displayBudget(row, 'displayMaterialBudget', 'materialBudget'))}
                    </NumericCell>
                    <NumericCell>
                      {formatCurrency(displayBudget(row, 'displayLaborBudget', 'laborBudget'))}
                    </NumericCell>
                    <NumericCell>
                      {formatCurrency(displayBudget(row, 'displayTotalBudget', 'totalBudget'))}
                    </NumericCell>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState activeView={activeView} sheetFilter={sheetFilter} query={queryDraft.trim()} />
        )}
      </div>
    </section>
  );
}
