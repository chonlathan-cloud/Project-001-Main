import { getStoredAuthUser, getStoredSessionToken } from './auth';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '');

const CHART_COLORS = ['#c9a15c', '#27a57a', '#de5b52', '#7c5cff', '#5a8dee'];

const compactNumber = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

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

const appendArrayParams = (searchParams, key, values) => {
  if (!Array.isArray(values)) return;
  values
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .forEach((item) => searchParams.append(key, item));
};

const normalizeInsightFlag = (flag, index) => ({
  key: String(flag?.key || `flag-${index}`),
  label: String(flag?.label || 'Flag').trim(),
  tone: String(flag?.tone || 'neutral').trim(),
});

const normalizeInsightRow = (row, index) => ({
  id: String(row?.id || `row-${index}`),
  sourceType: String(row?.source_type || '').trim(),
  sourceId: String(row?.source_id || '').trim(),
  projectId: String(row?.project_id || '').trim(),
  projectName: String(row?.project_name || '').trim(),
  actorId: String(row?.actor_id || '').trim(),
  actorName: String(row?.actor_name || '').trim(),
  referenceNo: String(row?.reference_no || '').trim(),
  title: String(row?.title || '').trim(),
  description: String(row?.description || '').trim(),
  entryType: String(row?.entry_type || '').trim(),
  flowDirection: String(row?.flow_direction || '').trim(),
  requestType: String(row?.request_type || '').trim(),
  status: String(row?.status || '').trim(),
  amount: row?.amount == null ? null : toNumber(row.amount),
  currency: String(row?.currency || 'THB').trim(),
  eventDate: String(row?.event_date || '').trim(),
  dueDate: String(row?.due_date || '').trim(),
  approvedAt: String(row?.approved_at || '').trim(),
  paidAt: String(row?.paid_at || '').trim(),
  createdAt: String(row?.created_at || '').trim(),
  updatedAt: String(row?.updated_at || '').trim(),
  isDuplicateFlag: Boolean(row?.is_duplicate_flag),
  isOverdue: Boolean(row?.is_overdue),
  tags: Array.isArray(row?.tags) ? row.tags.filter(Boolean) : [],
  flags: Array.isArray(row?.flags) ? row.flags.map(normalizeInsightFlag) : [],
  navigationTarget: row?.navigation_target
    ? {
        label: String(row.navigation_target.label || 'Open').trim(),
        path: String(row.navigation_target.path || '').trim(),
      }
    : null,
});

const normalizeInsightSummaryCard = (card, index) => ({
  key: String(card?.key || `card-${index}`),
  label: String(card?.label || `Card ${index + 1}`).trim(),
  count: card?.count == null ? null : toNumber(card.count),
  amount: card?.amount == null ? null : toNumber(card.amount),
  tone: String(card?.tone || 'neutral').trim(),
  description: String(card?.description || '').trim(),
});

const normalizeInsightFilterOption = (item, index, fallbackPrefix = 'option') => ({
  value: String(item?.value || `${fallbackPrefix}-${index}`).trim(),
  label: String(item?.label || item?.value || `${fallbackPrefix}-${index}`).trim(),
  count: item?.count == null ? null : toNumber(item.count),
});

function buildInsightWarehouseQuery(filters = {}) {
  const searchParams = new URLSearchParams();

  if (filters.q) searchParams.set('q', String(filters.q).trim());
  if (filters.quickView) searchParams.set('quick_view', String(filters.quickView).trim());
  if (filters.projectId) searchParams.set('project_id', String(filters.projectId).trim());
  if (filters.dateField) searchParams.set('date_field', String(filters.dateField).trim());
  if (filters.dateFrom) searchParams.set('date_from', String(filters.dateFrom).trim());
  if (filters.dateTo) searchParams.set('date_to', String(filters.dateTo).trim());
  if (filters.amountMin != null && filters.amountMin !== '') searchParams.set('amount_min', String(filters.amountMin));
  if (filters.amountMax != null && filters.amountMax !== '') searchParams.set('amount_max', String(filters.amountMax));
  if (filters.sortBy) searchParams.set('sort_by', String(filters.sortBy).trim());
  if (filters.sortOrder) searchParams.set('sort_order', String(filters.sortOrder).trim());
  if (filters.format) searchParams.set('format', String(filters.format).trim());
  if (filters.page) searchParams.set('page', String(filters.page));
  if (filters.pageSize) searchParams.set('page_size', String(filters.pageSize));
  if (filters.duplicateOnly) searchParams.set('duplicate_only', 'true');
  if (filters.overdueOnly) searchParams.set('overdue_only', 'true');

  appendArrayParams(searchParams, 'source_types', filters.sourceTypes);
  appendArrayParams(searchParams, 'statuses', filters.statuses);
  appendArrayParams(searchParams, 'entry_types', filters.entryTypes);
  appendArrayParams(searchParams, 'flow_directions', filters.flowDirections);

  return searchParams.toString();
}

const withColor = (items) =>
  items.map((item, index) => ({
    ...item,
    color: item.color || CHART_COLORS[index % CHART_COLORS.length],
  }));

function buildMockProfileData() { // This is only used for subcontractor profile preview when the subcontractor list API does not return detailed info. It will be removed once the API is ready.
  const authUser = getStoredAuthUser() || {};
  const displayName = authUser.display_name || authUser.email || authUser.subcontractor_id || 'Manee Son User';
  const role = authUser.role === 'subcontractor' ? 'Subcontractor' : 'Admin / Project Manager';
  const company = authUser.role === 'subcontractor' ? 'Subcontractor Portal' : 'Manee Son Construction';

  return {
    user: {
      name: displayName,
      company,
      role,
      time: 'Asia/Bangkok',
    },
    stats: [
      {
        id: 'active_projects',
        value: '8',
        label: 'Active Projects',
        subtext: 'Projects currently visible to this account',
      },
      {
        id: 'pending_approvals',
        value: '12',
        label: 'Pending Approvals',
        subtext: 'Bills and input requests waiting for review',
      },
      {
        id: 'completed_tasks',
        value: '47',
        label: 'Completed Tasks',
        subtext: 'Approved or completed workflow actions',
      },
      {
        id: 'team_members',
        value: '24',
        label: 'Team Members',
        subtext: 'Users and subcontractors in the working directory',
      },
      {
        id: 'reports_generated',
        value: '18',
        label: 'Reports Generated',
        subtext: 'Dashboard, insights, and AI summaries generated locally',
      },
      {
        id: 'budget_managed',
        value: '15.8M',
        label: 'Budget Managed',
        subtext: 'Mock financial coverage for profile preview',
      },
    ],
    chartData: [
      { name: 'Jan', Activity: 42, Expenses: 28 },
      { name: 'Feb', Activity: 55, Expenses: 41 },
      { name: 'Mar', Activity: 48, Expenses: 36 },
      { name: 'Apr', Activity: 71, Expenses: 52 },
      { name: 'May', Activity: 64, Expenses: 47 },
      { name: 'Jun', Activity: 78, Expenses: 59 },
    ],
  };
}

async function getProfileData() {
  const authUser = getStoredAuthUser() || {};
  const liveProfile = await apiRequest('/api/v1/profile/me').catch(() => null);

  if (liveProfile?.user) {
    return {
      user: liveProfile.user,
      stats: Array.isArray(liveProfile.stats) ? liveProfile.stats : [],
      chartData: Array.isArray(liveProfile.chartData) ? liveProfile.chartData : [],
    };
  }

  if (authUser.role === 'subcontractor' && authUser.subcontractor_id) {
    const subcontractors = await getSettingSubcontractors().catch(() => []);
    const profile = subcontractors.find((item) => item.id === authUser.subcontractor_id);
    if (profile) {
      const mock = buildMockProfileData();
      return {
        ...mock,
        user: {
          ...mock.user,
          name: profile.name || mock.user.name,
          company: profile.tax_id ? `Tax ID: ${profile.tax_id}` : mock.user.company,
          role: 'Subcontractor',
        },
      };
    }
  }

  return buildMockProfileData();
}

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
  const sessionToken = getStoredSessionToken();
  const authHeaders = sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {};

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...authHeaders,
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

export async function getInsightWarehouseFilters() {
  const data = await apiRequest('/api/v1/insights/filters');

  return {
    projects: Array.isArray(data?.projects)
      ? data.projects.map((item, index) => normalizeInsightFilterOption(item, index, 'project'))
      : [],
    sourceTypes: Array.isArray(data?.source_types)
      ? data.source_types.map((item, index) => normalizeInsightFilterOption(item, index, 'source'))
      : [],
    statuses: Array.isArray(data?.statuses)
      ? data.statuses.map((item, index) => normalizeInsightFilterOption(item, index, 'status'))
      : [],
    entryTypes: Array.isArray(data?.entry_types)
      ? data.entry_types.map((item, index) => normalizeInsightFilterOption(item, index, 'entry'))
      : [],
    flowDirections: Array.isArray(data?.flow_directions)
      ? data.flow_directions.map((item, index) => normalizeInsightFilterOption(item, index, 'flow'))
      : [],
    quickViews: Array.isArray(data?.quick_views)
      ? data.quick_views.map((item, index) => ({
          key: String(item?.key || `view-${index}`),
          label: String(item?.label || `View ${index + 1}`).trim(),
          description: String(item?.description || '').trim(),
        }))
      : [],
    columns: Array.isArray(data?.columns)
      ? data.columns.map((item, index) => ({
          key: String(item?.key || `column-${index}`),
          label: String(item?.label || `Column ${index + 1}`).trim(),
          dataType: String(item?.data_type || 'text').trim(),
          sortable: item?.sortable !== false,
          defaultVisible: item?.default_visible !== false,
        }))
      : [],
    dateFields: Array.isArray(data?.date_fields)
      ? data.date_fields.map((item, index) => normalizeInsightFilterOption(item, index, 'date'))
      : [],
    sortFields: Array.isArray(data?.sort_fields)
      ? data.sort_fields.map((item, index) => normalizeInsightFilterOption(item, index, 'sort'))
      : [],
    exportFormats: Array.isArray(data?.export_formats)
      ? data.export_formats.map((item, index) => normalizeInsightFilterOption(item, index, 'export'))
      : [],
    lastUpdatedAt: String(data?.last_updated_at || '').trim(),
  };
}

export async function getInsightWarehouseSummary(filters = {}) {
  const query = buildInsightWarehouseQuery(filters);
  const path = query ? `/api/v1/insights/summary?${query}` : '/api/v1/insights/summary';
  const data = await apiRequest(path);

  return {
    cards: Array.isArray(data?.cards)
      ? data.cards.map(normalizeInsightSummaryCard)
      : [],
    appliedFilters: data?.applied_filters || null,
    lastUpdatedAt: String(data?.last_updated_at || '').trim(),
  };
}

export async function getInsightWarehouseRows(filters = {}) {
  const query = buildInsightWarehouseQuery(filters);
  const path = query ? `/api/v1/insights/rows?${query}` : '/api/v1/insights/rows';
  const data = await apiRequest(path);

  const pageInfo = data?.page_info || {};

  return {
    items: Array.isArray(data?.items) ? data.items.map(normalizeInsightRow) : [],
    pageInfo: {
      page: toNumber(pageInfo.page, 1),
      pageSize: toNumber(pageInfo.page_size, 25),
      totalItems: toNumber(pageInfo.total_items, 0),
      totalPages: toNumber(pageInfo.total_pages, 0),
      hasNext: Boolean(pageInfo.has_next),
      hasPrevious: Boolean(pageInfo.has_previous),
    },
    appliedFilters: data?.applied_filters || null,
    lastUpdatedAt: String(data?.last_updated_at || '').trim(),
    emptyStateMessage: String(data?.empty_state_message || '').trim(),
  };
}

export function getInsightWarehouseExportUrl(filters = {}) {
  const query = buildInsightWarehouseQuery(filters);
  return query
    ? `${API_BASE_URL}/api/v1/insights/export?${query}`
    : `${API_BASE_URL}/api/v1/insights/export`;
}

export async function adminLogin(payload) {
  return apiRequest('/api/v1/auth/admin-login', {
    method: 'POST',
    body: JSON.stringify({
      firebase_id_token: payload.firebaseIdToken,
      email: payload.email,
      display_name: payload.displayName,
    }),
  });
}

export async function lineLogin(payload) {
  return apiRequest('/api/v1/auth/line-login', {
    method: 'POST',
    body: JSON.stringify({
      line_access_token: payload.lineAccessToken,
    }),
  });
}

export async function signUpSubcontractor(payload) {
  const formData = new FormData();
  formData.append('line_uid', payload.lineUid);
  formData.append('name', payload.name);
  formData.append('tax_id', payload.taxId);
  if (payload.kycImage) {
    formData.append('kyc_image', payload.kycImage);
  }

  return apiRequest('/api/v1/auth/sign-up', {
    method: 'POST',
    headers: {},
    body: formData,
    timeoutMs: 90000,
  });
}

export async function getCurrentSessionUser() {
  return apiRequest('/api/v1/auth/me');
}

export async function getSettingSubcontractors() {
  const data = await apiRequest('/api/v1/settings/subcontractors');
  return Array.isArray(data) ? data : [];
}

export async function updateSettingSubcontractor(subcontractorId, payload) {
  return apiRequest(`/api/v1/settings/subcontractors/${subcontractorId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function resetSettingSubcontractorLine(subcontractorId) {
  return apiRequest(`/api/v1/settings/subcontractors/${subcontractorId}/reset-line`, {
    method: 'POST',
  });
}

export async function getSettingSubcontractorKycUrl(subcontractorId) {
  return apiRequest(`/api/v1/settings/users/${subcontractorId}/kyc-image`);
}

export async function getSettingAdmins() {
  const data = await apiRequest('/api/v1/settings/admins');
  return Array.isArray(data) ? data : [];
}

export async function createSettingAdmin(payload) {
  return apiRequest('/api/v1/settings/admins', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateSettingAdmin(adminId, payload) {
  return apiRequest(`/api/v1/settings/admins/${adminId}`, {
    method: 'PUT',
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
    case 'settings': {
      return getSettingSubcontractors().catch(() => []);
    }
    case 'profile':
      return getProfileData();
    default:
      return null;
  }
}

export { API_BASE_URL, compactNumber, buildInsightWarehouseQuery };
