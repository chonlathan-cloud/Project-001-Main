const DEFAULT_API_BASE_URL = 'http://localhost:8000';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '');

const CHART_COLORS = ['#c9a15c', '#27a57a', '#de5b52', '#7c5cff', '#5a8dee'];

const compactNumber = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const INSIGHTS_MOCK_DATA = {
  filters: {
    users: ['ผู้ทำรายการทั้งหมด', 'Admin', 'Site Engineer'],
    months: ['ม.ค.', 'ก.พ.', 'มี.ค.'],
    years: ['2026', '2025'],
  },
  summary: {
    new: { count: 0, amount: '0' },
    pending: { count: 0, amount: '0' },
    approved: { count: 0, amount: '0' },
  },
  tableName: 'รายการทั้งหมด',
  tableData: [],
};

const toNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatCurrency = (value) =>
  `$${toNumber(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const formatPercent = (value) => `${toNumber(value).toFixed(1)}%`;

const normalizeStatusLabel = (status) => {
  if (!status) return '-';
  return String(status).replace(/_/g, ' ').trim();
};

const shortLabel = (value, fallback) => {
  const label = (value || fallback || '-').trim();
  return label.length > 18 ? `${label.slice(0, 18)}...` : label;
};

const withColor = (items) =>
  items.map((item, index) => ({
    ...item,
    color: item.color || CHART_COLORS[index % CHART_COLORS.length],
  }));

const flattenBoqTree = (nodes = []) =>
  nodes.flatMap((node) => [node, ...flattenBoqTree(node.children || [])]);

const toBoqChartNodes = (nodes = []) => {
  const rootNodes = Array.isArray(nodes) ? nodes : [];
  const summaryNodes = rootNodes.filter((node) => toNumber(node.total_budget) > 0);

  if (summaryNodes.length > 0) {
    return summaryNodes;
  }

  return flattenBoqTree(rootNodes).filter(
    (node) =>
      toNumber(node.total_budget) > 0 &&
      (!Array.isArray(node.children) || node.children.length === 0)
  );
};

const toProjectCardItem = (project) => {
  const id = project.project_id || project.id || '';
  const total = toNumber(project.total_budget ?? project.contingency_budget);
  const progressPercent = toNumber(project.progress_percent);

  return {
    id,
    name: project.name || 'Untitled Project',
    projectType: project.project_type || '-',
    status: normalizeStatusLabel(project.status),
    rawStatus: project.status || '-',
    progressPercent,
    spent: toNumber(project.spent, total * (progressPercent / 100)),
    total,
    overheadPercent: toNumber(project.overhead_percent),
    profitPercent: toNumber(project.profit_percent),
    vatPercent: toNumber(project.vat_percent),
    contingencyBudget: toNumber(project.contingency_budget, total),
  };
};

async function apiRequest(path, options = {}) {
  const { timeoutMs = 30000, headers, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(headers || {}),
      },
      signal: controller.signal,
      ...fetchOptions,
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error?.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)} seconds.`);
    }
    throw error;
  }
  clearTimeout(timeoutId);

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = Array.isArray(payload?.detail)
      ? payload.detail
          .map((item) => {
            const location = Array.isArray(item?.loc) ? item.loc.join('.') : 'request';
            return `${location}: ${item?.msg || 'Validation error'}`;
          })
          .join(' | ')
      : payload?.detail || payload?.message || `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  if (payload?.status && payload.status !== 'success') {
    throw new Error(payload.detail || 'API request failed.');
  }

  return payload?.data ?? payload;
}

const receiptPreviewCache = new Map();

function getReceiptPreviewCache(cacheKey) {
  const cached = receiptPreviewCache.get(cacheKey);
  if (!cached) return null;
  if (cached.expiresAt <= Date.now()) {
    receiptPreviewCache.delete(cacheKey);
    return null;
  }
  return cached.data;
}

function setReceiptPreviewCache(cacheKey, data, expiresInMinutes) {
  const ttlMs = Math.max(1, Number(expiresInMinutes) || 15) * 60 * 1000;
  receiptPreviewCache.set(cacheKey, {
    data,
    expiresAt: Date.now() + ttlMs - 10 * 1000,
  });
}

function buildReceiptPreviewCacheKey(prefix, requestId, cacheToken, expiresInMinutes) {
  return `${prefix}:${requestId}:${cacheToken || 'default'}:${expiresInMinutes}`;
}

async function getReceiptPreview(path, {
  requestId,
  expiresInMinutes = 15,
  cacheToken = '',
  forceRefresh = false,
  cachePrefix,
}) {
  const cacheKey = buildReceiptPreviewCacheKey(
    cachePrefix,
    requestId,
    cacheToken,
    expiresInMinutes
  );

  if (!forceRefresh) {
    const cached = getReceiptPreviewCache(cacheKey);
    if (cached) return cached;
  }

  const data = await apiRequest(path);
  setReceiptPreviewCache(cacheKey, data, expiresInMinutes);
  return data;
}

export async function getDashboardData() {
  const data = await apiRequest('/api/v1/dashboard/summary');

  const kpis = data?.kpis || {};
  const monthlyCashflow = Array.isArray(data?.monthly_cashflow) ? data.monthly_cashflow : [];

  const totalIncome = monthlyCashflow.reduce((sum, item) => sum + toNumber(item.income), 0);
  const totalExpense = monthlyCashflow.reduce((sum, item) => sum + toNumber(item.expense), 0);
  const balance = totalIncome - totalExpense;

  const shipmentData = monthlyCashflow.map((item) => ({
    name: item.month || '-',
    green: toNumber(item.income),
    red: toNumber(item.expense),
  }));

  const budgetData = withColor(
    [
      { name: 'Budget', value: toNumber(kpis.total_budget) },
      { name: 'Actual Cost', value: toNumber(kpis.actual_cost) },
      { name: 'Overdue', value: toNumber(kpis.overdue_amount) },
    ].filter((item) => item.value > 0)
  );

  const wagesData = withColor(
    [
      { id: 'income', value: totalIncome },
      { id: 'expense', value: totalExpense },
      { id: 'balance', value: Math.max(balance, 0) },
    ].filter((item) => item.value > 0)
  );

  const valueData = withColor(
    monthlyCashflow.map((item) => ({
      name: item.month || '-',
      value: toNumber(item.income),
    }))
  );

  const workPeriodData = withColor(
    monthlyCashflow.map((item) => ({
      name: item.month || '-',
      value: toNumber(item.expense),
    }))
  );

  return {
    stats: [
      { title: 'งบรวม', value: formatCurrency(kpis.total_budget) },
      { title: 'ต้นทุนจริง', value: formatCurrency(kpis.actual_cost) },
      { title: 'รออนุมัติ', value: String(toNumber(kpis.pending_approval_count)) },
      {
        title: 'Margin',
        value: kpis.total_profit_margin || formatPercent(0),
      },
    ],
    shipmentData,
    budgetData,
    wagesData,
    valueData,
    workPeriodData,
  };
}

export async function getProjectsData() {
  const data = await apiRequest('/api/v1/projects');
  const projects = Array.isArray(data) ? data : [];

  return projects.map(toProjectCardItem);
}

export async function createProject(payload) {
  const project = await apiRequest('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  return toProjectCardItem(project);
}

export async function updateProject(projectId, payload) {
  const project = await apiRequest(`/api/v1/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });

  return toProjectCardItem(project);
}

export async function syncProjectBoq(payload) {
  return apiRequest('/api/v1/projects/boq/sync', {
    method: 'POST',
    timeoutMs: 195000,
    body: JSON.stringify({
      project_id: payload.projectId,
      boq_type: payload.boqType,
      sheet_url: payload.sheetUrl,
      sheet_name: payload.sheetName,
    }),
  });
}

export async function getProjectBoqTabs(payload) {
  return apiRequest('/api/v1/projects/boq/tabs', {
    method: 'POST',
    timeoutMs: 45000,
    body: JSON.stringify({
      sheet_url: payload.sheetUrl,
    }),
  });
}

export async function syncProjectBoqBatch(payload) {
  const selectedSheetNames = Array.isArray(payload.sheetNames)
    ? payload.sheetNames.filter(Boolean)
    : [];

  return apiRequest('/api/v1/projects/boq/sync-batch', {
    method: 'POST',
    timeoutMs: 30000,
    body: JSON.stringify({
      project_id: payload.projectId,
      boq_type: payload.boqType,
      sheet_url: payload.sheetUrl,
      sheet_names: selectedSheetNames,
    }),
  });
}

export async function getProjectBoqSyncJob(jobId) {
  return apiRequest(`/api/v1/projects/boq/sync-jobs/${jobId}`, {
    timeoutMs: 30000,
  });
}

export async function getProjectDetailData(projectId) {
  const project = await apiRequest(`/api/v1/projects/${projectId}`);

  const boqResponse = await apiRequest(`/api/v1/projects/${projectId}/boq`).catch(() => null);
  const boqTree = Array.isArray(boqResponse?.boq_tree) ? boqResponse.boq_tree : [];
  const chartNodes = toBoqChartNodes(boqTree);
  const topItems = chartNodes
    .filter((item) => toNumber(item.total_budget) > 0)
    .sort((left, right) => toNumber(right.total_budget) - toNumber(left.total_budget))
    .slice(0, 5);

  const chartBase = topItems.map((item, index) => ({
    name: shortLabel(item.description || item.item_no, `BOQ ${index + 1}`),
    totalBudget: toNumber(item.total_budget),
    laborBudget: toNumber(item.labor_budget),
    materialBudget: toNumber(item.material_budget),
    color: CHART_COLORS[index % CHART_COLORS.length],
  }));

  return {
    projectId: project.project_id || project.id || projectId,
    name: project.name || boqResponse?.project_name || 'Project',
    stats: [
      { title: 'สถานะ', value: normalizeStatusLabel(project.status) },
      { title: 'งบสำรอง', value: formatCurrency(project.contingency_budget) },
      { title: 'Overhead', value: formatPercent(project.overhead_percent) },
      { title: 'Profit', value: formatPercent(project.profit_percent) },
    ],
    shipmentData: chartBase.map((item) => ({
      name: item.name,
      green: item.totalBudget,
      red: item.laborBudget,
    })),
    salesData: chartBase.map((item) => ({
      name: item.name,
      sales: item.totalBudget,
      target: Math.max(item.totalBudget, item.materialBudget + item.laborBudget),
    })),
    wagesData: chartBase
      .filter((item) => item.laborBudget > 0)
      .map((item) => ({
        id: item.name,
        value: item.laborBudget,
        color: item.color,
      })),
    valueData: chartBase.map((item) => ({
      name: item.name,
      value: item.totalBudget,
      color: item.color,
    })),
    workPeriodData: chartBase
      .filter((item) => item.materialBudget > 0)
      .map((item) => ({
        name: item.name,
        value: item.materialBudget,
        color: item.color,
      })),
  };
}

export async function getInputProjectOptions() {
  const data = await apiRequest('/api/v1/input/projects');
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    ...item,
    project_id: item.project_id || item.id || '',
  }));
}

function normalizeChatSource(source, index) {
  if (typeof source === 'string') {
    const label = source.trim();
    return {
      id: `source-${index}`,
      label: label || `Source ${index + 1}`,
      sheetName: '',
      description: label,
      projectId: '',
    };
  }

  if (source && typeof source === 'object') {
    const description = String(source.description || source.label || '').trim();
    const sheetName = String(source.sheet_name || source.sheetName || '').trim();
    return {
      id: String(source.id || `source-${index}`),
      label: description || sheetName || `Source ${index + 1}`,
      sheetName,
      description,
      projectId: String(source.project_id || source.projectId || '').trim(),
    };
  }

  return {
    id: `source-${index}`,
    label: `Source ${index + 1}`,
    sheetName: '',
    description: '',
    projectId: '',
  };
}

function normalizeChatMetric(metric, index) {
  if (!metric || typeof metric !== 'object') {
    return {
      id: `metric-${index}`,
      label: `Metric ${index + 1}`,
      value: '-',
    };
  }

  return {
    id: String(metric.id || `metric-${index}`),
    label: String(metric.label || `Metric ${index + 1}`).trim(),
    value: String(metric.value ?? '-').trim() || '-',
  };
}

function normalizeChatAction(action, index) {
  const label = typeof action === 'string' ? action.trim() : '';
  return {
    id: `action-${index}`,
    label: label || `Action ${index + 1}`,
  };
}

function normalizeChatTimeScope(timeScope) {
  if (!timeScope || typeof timeScope !== 'object') return null;

  const label = String(timeScope.label || '').trim();
  const startDate = String(timeScope.start_date || timeScope.startDate || '').trim();
  const endDate = String(timeScope.end_date || timeScope.endDate || '').trim();

  if (!label && !startDate && !endDate) return null;

  return {
    key: String(timeScope.key || '').trim(),
    label: label || 'Custom Range',
    startDate,
    endDate,
  };
}

function normalizeChatPayload(data, fallbackProjectId = '') {
  const rawSources = Array.isArray(data?.sources) ? data.sources : [];

  return {
    intent: String(data?.intent || '').trim(),
    summary: String(data?.summary || '').trim(),
    reply: String(data?.reply || '').trim() || 'AI did not return a response.',
    sources: rawSources.map(normalizeChatSource),
    metrics: Array.isArray(data?.metrics) ? data.metrics.map(normalizeChatMetric) : [],
    nextActions: Array.isArray(data?.next_actions)
      ? data.next_actions.map(normalizeChatAction)
      : [],
    timeScope: normalizeChatTimeScope(data?.time_scope),
    projectId: String(data?.project_id || fallbackProjectId || '').trim(),
    projectName: String(data?.project_name || '').trim(),
    contextItemCount: toNumber(data?.context_item_count),
  };
}

export async function askChatQuestion({ message, projectId }) {
  const cleanedMessage = String(message || '').trim();
  const payload = {
    message: cleanedMessage,
  };

  if (projectId) {
    payload.project_id = projectId;
  }

  const data = await apiRequest('/api/v1/chat/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 60000,
  });

  return normalizeChatPayload(data, projectId);
}

export async function getChatHistory() {
  const data = await apiRequest('/api/v1/chat/history');
  if (!Array.isArray(data)) return [];

  return data.map((item, index) => ({
    id: String(item?.id || `history-${index}`),
    createdAt: String(item?.created_at || '').trim(),
    question: String(item?.question || '').trim(),
    ...normalizeChatPayload(item, String(item?.project_id || '').trim()),
  }));
}

export async function clearChatHistory() {
  return apiRequest('/api/v1/chat/history', {
    method: 'DELETE',
  });
}

export async function extractInputReceipt(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest('/api/v1/input/receipt-extract', {
    method: 'POST',
    headers: {},
    body: formData,
    timeoutMs: 45000,
  });
}

export async function uploadInputReceipt(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest('/api/v1/input/receipt-upload', {
    method: 'POST',
    headers: {},
    body: formData,
    timeoutMs: 90000,
  });
}

export async function submitInputRequest(payload) {
  return apiRequest('/api/v1/input/requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getAdminInputRequests(filters = {}) {
  const searchParams = new URLSearchParams();

  if (filters.status) searchParams.set('status', filters.status);
  if (filters.entryType) searchParams.set('entry_type', filters.entryType);
  if (filters.projectId) searchParams.set('project_id', filters.projectId);

  const query = searchParams.toString();
  const path = query ? `/api/v1/input/admin/requests?${query}` : '/api/v1/input/admin/requests';
  const data = await apiRequest(path);
  return Array.isArray(data) ? data : [];
}

export async function getAdminInputReceiptUrl(
  requestId,
  { expiresInMinutes = 15, cacheToken = '', forceRefresh = false } = {}
) {
  return getReceiptPreview(
    `/api/v1/input/admin/requests/${requestId}/receipt-url?expires_in_minutes=${expiresInMinutes}`,
    {
      requestId,
      expiresInMinutes,
      cacheToken,
      forceRefresh,
      cachePrefix: 'admin-input-receipt',
    }
  );
}

export async function getInputRequestReceiptUrl(
  requestId,
  { expiresInMinutes = 15, cacheToken = '', forceRefresh = false } = {}
) {
  return getReceiptPreview(
    `/api/v1/input/requests/${requestId}/receipt-url?expires_in_minutes=${expiresInMinutes}`,
    {
      requestId,
      expiresInMinutes,
      cacheToken,
      forceRefresh,
      cachePrefix: 'input-receipt',
    }
  );
}

export async function updateAdminInputRequest(requestId, payload) {
  return apiRequest(`/api/v1/input/admin/requests/${requestId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function approveAdminInputRequest(requestId, payload = {}) {
  return apiRequest(`/api/v1/input/admin/requests/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function rejectAdminInputRequest(requestId, payload) {
  return apiRequest(`/api/v1/input/admin/requests/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function markPaidAdminInputRequest(requestId, payload = {}) {
  return apiRequest(`/api/v1/input/admin/requests/${requestId}/mark-paid`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchData(type, param = null) {
  switch (type) {
    case 'dashboard':
      return getDashboardData();
    case 'projects':
      return getProjectsData();
    case 'project_detail':
      return getProjectDetailData(param);
    case 'insights':
      return INSIGHTS_MOCK_DATA;
    case 'settings': {
      const data = await apiRequest('/api/v1/settings/subcontractors').catch(() => []);
      return Array.isArray(data) ? data : [];
    }
    default:
      return null;
  }
}

export { API_BASE_URL, compactNumber };
