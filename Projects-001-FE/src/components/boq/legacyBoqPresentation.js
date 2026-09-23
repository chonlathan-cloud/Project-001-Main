const normalizeSheetName = (value) => String(value || '').trim();
const normalizeSheetKey = (value) => normalizeSheetName(value).toUpperCase();

export function buildLegacySheetOptions(rows = [], allLabel = 'All sheets') {
  const countsBySheet = new Map();
  const labelsBySheet = new Map();

  rows.forEach((row) => {
    const sheetName = normalizeSheetName(row?.sheetName);
    const sheetKey = normalizeSheetKey(sheetName);
    if (!sheetKey) return;
    if (!labelsBySheet.has(sheetKey)) labelsBySheet.set(sheetKey, sheetName);
    countsBySheet.set(sheetKey, (countsBySheet.get(sheetKey) || 0) + 1);
  });

  return [
    { value: 'ALL', label: allLabel, count: rows.length },
    ...Array.from(labelsBySheet, ([value, label]) => ({
      value,
      label,
      count: countsBySheet.get(value) || 0,
    })),
  ];
}

export function getLegacyBoqPresentation({
  legacyHistoryOnly = false,
  hasCustomerBoq = false,
  hasSubcontractorBoq = false,
} = {}) {
  const hasLegacyRows = hasCustomerBoq || hasSubcontractorBoq;
  const nativeOnly = legacyHistoryOnly && !hasLegacyRows;

  return {
    hasLegacyRows,
    nativeOnly,
    collapseHistory: legacyHistoryOnly && hasLegacyRows,
    showIncompleteWarning:
      !legacyHistoryOnly && (!hasCustomerBoq || !hasSubcontractorBoq),
    navigationLabel: legacyHistoryOnly ? 'Legacy BOQ History' : 'BOQ Comparison',
  };
}

export { normalizeSheetKey, normalizeSheetName };
