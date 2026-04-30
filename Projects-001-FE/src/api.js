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

const normalizeStatusLabel = (status) => {
  if (!status) return '-';
  return String(status).replace(/_/g, ' ').trim();
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
      line_picture_url: '',
      profile_image_url: '',
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
          line_picture_url: profile.line_picture_url || '',
          profile_image_url: profile.profile_image_url || '',
        },
      };
    }
  }

  return buildMockProfileData();
}

const sanitizeBoqTreeNode = (node, prefix = 'boq-node', index = 0) => ({
  key: String(node?.key || `${prefix}-${index}`),
  sheetName: String(node?.sheet_name || '').trim(),
  boqType: String(node?.boq_type || '').trim(),
  wbsLevel: toNumber(node?.wbs_level, 1),
  description: String(node?.description || '').trim(),
  itemNo: String(node?.item_no || '').trim(),
  qty: node?.qty == null ? null : toNumber(node.qty),
  unit: String(node?.unit || '').trim(),
  totalBudget: toNumber(node?.total_budget),
  actualSpent: node?.actual_spent == null ? null : toNumber(node.actual_spent),
  variance: node?.variance == null ? null : String(node.variance).trim(),
  materialBudget: toNumber(node?.material_budget),
  laborBudget: toNumber(node?.labor_budget),
  customerPrice: node?.customer_price == null ? null : toNumber(node.customer_price),
  subcontractorPrice: node?.subcontractor_price == null ? null : toNumber(node.subcontractor_price),
  marginPerUnit: node?.margin_per_unit == null ? null : toNumber(node.margin_per_unit),
  children: Array.isArray(node?.children)
    ? node.children.map((child, childIndex) =>
        sanitizeBoqTreeNode(child, `${prefix}-${index}`, childIndex))
    : [],
});

const sanitizeCompareBoqNode = (node, prefix = 'compare-node', index = 0) => ({
  key: String(node?.key || `${prefix}-${index}`),
  sheetName: String(node?.sheet_name || '').trim(),
  wbsLevel: toNumber(node?.wbs_level, 1),
  description: String(node?.description || '').trim(),
  itemNo: String(node?.item_no || '').trim(),
  unit: String(node?.unit || '').trim(),
  customerQty: node?.customer_qty == null ? null : toNumber(node.customer_qty),
  subcontractorQty: node?.subcontractor_qty == null ? null : toNumber(node.subcontractor_qty),
  customerTotalBudget: toNumber(node?.customer_total_budget),
  subcontractorTotalBudget: toNumber(node?.subcontractor_total_budget),
  customerMaterialBudget: toNumber(node?.customer_material_budget),
  subcontractorMaterialBudget: toNumber(node?.subcontractor_material_budget),
  customerLaborBudget: toNumber(node?.customer_labor_budget),
  subcontractorLaborBudget: toNumber(node?.subcontractor_labor_budget),
  variance: toNumber(node?.variance),
  marginPercent: node?.margin_percent == null ? null : toNumber(node.margin_percent),
  matchStatus: String(node?.match_status || 'MATCHED').trim(),
  children: Array.isArray(node?.children)
    ? node.children.map((child, childIndex) =>
        sanitizeCompareBoqNode(child, `${prefix}-${index}`, childIndex))
    : [],
});

const sanitizeWbsSummaryItem = (item, index = 0) => ({
  key: String(item?.key || `wbs-summary-${index}`),
  label: String(item?.label || `WBS ${index + 1}`).trim(),
  sheetName: String(item?.sheet_name || '').trim(),
  customerTotalBudget: toNumber(item?.customer_total_budget),
  subcontractorTotalBudget: toNumber(item?.subcontractor_total_budget),
  variance: toNumber(item?.variance),
  marginPercent: item?.margin_percent == null ? null : toNumber(item.margin_percent),
  customerMaterialBudget: toNumber(item?.customer_material_budget),
  subcontractorMaterialBudget: toNumber(item?.subcontractor_material_budget),
  customerLaborBudget: toNumber(item?.customer_labor_budget),
  subcontractorLaborBudget: toNumber(item?.subcontractor_labor_budget),
  matchStatus: String(item?.match_status || 'MATCHED').trim(),
});

const sanitizeExecutionSummaryItem = (item, index = 0) => ({
  key: String(item?.key || `execution-summary-${index}`),
  label: String(item?.label || `Metric ${index + 1}`).trim(),
  amount: toNumber(item?.amount),
  count: toNumber(item?.count),
  tone: String(item?.tone || 'neutral').trim(),
});

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
  const recentActions = Array.isArray(data?.recent_actions) ? data.recent_actions : [];

  const cashflow = monthlyCashflow.map((item) => {
    const income = toNumber(item.income);
    const expense = toNumber(item.expense);

    return {
      month: item.month || '-',
      income,
      expense,
      balance: income - expense,
    };
  });

  const totalBudget = toNumber(kpis.total_budget);
  const actualCost = toNumber(kpis.actual_cost);
  const pendingApprovalCount = toNumber(kpis.pending_approval_count);
  const overdueAmount = toNumber(kpis.overdue_amount);
  const profitMargin = toNumber(
    String(kpis.total_profit_margin || 0).replace('%', ''),
  );

  const totalIncome = cashflow.reduce((sum, item) => sum + item.income, 0);
  const totalExpense = cashflow.reduce((sum, item) => sum + item.expense, 0);
  const netCashflow = totalIncome - totalExpense;
  const remainingBudget = totalBudget - actualCost;
  const budgetUtilization = totalBudget > 0 ? (actualCost / totalBudget) * 100 : 0;
  const overdueRatio = totalBudget > 0 ? (overdueAmount / totalBudget) * 100 : 0;

  return {
    kpis: {
      totalBudget,
      actualCost,
      pendingApprovalCount,
      overdueAmount,
      profitMargin,
      totalIncome,
      totalExpense,
      netCashflow,
      remainingBudget,
      budgetUtilization,
      overdueRatio,
    },
    statCards: [
      {
        key: 'total-budget',
        label: 'งบรวมโครงการ',
        value: totalBudget,
        kind: 'currency',
        description: 'งบประมาณรวมจากทุกโครงการที่มีอยู่ในระบบ',
        tone: 'neutral',
      },
      {
        key: 'actual-cost',
        label: 'ต้นทุนที่บันทึกแล้ว',
        value: actualCost,
        kind: 'currency',
        description: 'มูลค่ารายจ่ายที่อนุมัติแล้วทั้งหมด',
        tone: budgetUtilization > 85 ? 'warning' : 'positive',
      },
      {
        key: 'pending-approvals',
        label: 'รายการรออนุมัติ',
        value: pendingApprovalCount,
        kind: 'number',
        description: 'จำนวน input request ที่มีสถานะ Pending Admin',
        tone: pendingApprovalCount > 0 ? 'warning' : 'positive',
      },
      {
        key: 'profit-margin',
        label: 'Profit Margin',
        value: profitMargin,
        kind: 'percent',
        description: 'คำนวณจากงบรวมเทียบกับต้นทุนจริงที่บันทึกแล้ว',
        tone: profitMargin < 0 ? 'danger' : 'neutral',
      },
    ],
    budgetBreakdown: [
      {
        key: 'actual-cost',
        label: 'ต้นทุนจริง',
        value: actualCost,
        ratio: Math.min(budgetUtilization, 100),
        tone: budgetUtilization > 85 ? 'warning' : 'positive',
      },
      {
        key: 'remaining-budget',
        label: 'งบคงเหลือ',
        value: remainingBudget,
        ratio: totalBudget > 0 ? Math.min(Math.max((remainingBudget / totalBudget) * 100, 0), 100) : 0,
        tone: remainingBudget < 0 ? 'danger' : 'neutral',
      },
      {
        key: 'overdue-amount',
        label: 'ยอดค้างชำระ',
        value: overdueAmount,
        ratio: Math.min(overdueRatio, 100),
        tone: overdueAmount > 0 ? 'danger' : 'positive',
      },
    ],
    attentionItems: [
      {
        key: 'pending',
        label: 'Pending approvals',
        value: pendingApprovalCount,
        kind: 'number',
        description: 'ควรเคลียร์รายการรออนุมัติเพื่อลดคอขวดงานเอกสาร',
        tone: pendingApprovalCount > 0 ? 'warning' : 'positive',
      },
      {
        key: 'overdue',
        label: 'Overdue amount',
        value: overdueAmount,
        kind: 'currency',
        description: 'ยอดที่เกินกำหนดชำระและยังไม่อนุมัติ',
        tone: overdueAmount > 0 ? 'danger' : 'positive',
      },
      {
        key: 'cashflow',
        label: 'Net cashflow',
        value: netCashflow,
        kind: 'currency',
        description: 'รายรับจาก installments หักรายจ่ายที่อนุมัติแล้ว',
        tone: netCashflow < 0 ? 'danger' : 'positive',
      },
    ],
    cashflow,
    recentActions: recentActions.map((item, index) => ({
      id: `recent-action-${index}`,
      time: String(item?.time || '').trim(),
      action: String(item?.action || '').trim(),
    })),
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
  const customerTree = Array.isArray(boqResponse?.customer_tree)
    ? boqResponse.customer_tree.map((node, index) => sanitizeBoqTreeNode(node, 'customer-node', index))
    : [];
  const subcontractorTree = Array.isArray(boqResponse?.subcontractor_tree)
    ? boqResponse.subcontractor_tree.map((node, index) => sanitizeBoqTreeNode(node, 'subcontractor-node', index))
    : [];
  const compareTree = Array.isArray(boqResponse?.compare_tree)
    ? boqResponse.compare_tree.map((node, index) => sanitizeCompareBoqNode(node, 'compare-node', index))
    : [];
  const compareSummary = boqResponse?.compare_summary || {};
  const wbsSummary = Array.isArray(boqResponse?.wbs_summary)
    ? boqResponse.wbs_summary.map((item, index) => sanitizeWbsSummaryItem(item, index))
    : [];
  const executionSummary = Array.isArray(boqResponse?.execution_summary)
    ? boqResponse.execution_summary.map((item, index) => sanitizeExecutionSummaryItem(item, index))
    : [];
  const sheetNames = Array.isArray(compareSummary?.sheet_names)
    ? compareSummary.sheet_names.map((item) => String(item || '').trim()).filter(Boolean)
    : [];

  return {
    projectId: project.project_id || project.id || projectId,
    name: project.name || boqResponse?.project_name || 'Project',
    projectType: String(project.project_type || '').trim(),
    status: String(project.status || '').trim(),
    overheadPercent: toNumber(project.overhead_percent),
    profitPercent: toNumber(project.profit_percent),
    vatPercent: toNumber(project.vat_percent),
    contingencyBudget: toNumber(project.contingency_budget),
    customerTree,
    subcontractorTree,
    compareTree,
    wbsSummary,
    executionSummary,
    compareSummary: {
      customerTotalBudget: toNumber(compareSummary?.customer_total_budget),
      subcontractorTotalBudget: toNumber(compareSummary?.subcontractor_total_budget),
      totalVariance: toNumber(compareSummary?.total_variance),
      marginPercent: compareSummary?.margin_percent == null ? null : toNumber(compareSummary.margin_percent),
      matchedCount: toNumber(compareSummary?.matched_count),
      customerOnlyCount: toNumber(compareSummary?.customer_only_count),
      subcontractorOnlyCount: toNumber(compareSummary?.subcontractor_only_count),
      sheetNames,
    },
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

export async function getInputDefaults() {
  const data = await apiRequest('/api/v1/input/defaults').catch(() => null);
  const bankAccount = data?.bank_account || {};

  return {
    requesterName: String(data?.requester_name || '').trim(),
    phone: String(data?.phone || '').trim(),
    bankName: String(bankAccount?.bank_name || '').trim(),
    accountNo: String(bankAccount?.account_no || '').trim(),
    accountName: String(bankAccount?.account_name || '').trim(),
  };
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
  formData.append('line_picture_url', payload.linePictureUrl || '');
  formData.append('name', payload.name);
  formData.append('contact_name', payload.contactName);
  formData.append('phone', payload.phone);
  formData.append('tax_id', payload.taxId);
  formData.append('bank_name', payload.bankName);
  formData.append('account_no', payload.accountNo);
  formData.append('account_name', payload.accountName);
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

export async function uploadProfileAvatar(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiRequest('/api/v1/profile/me/avatar', {
    method: 'POST',
    headers: {},
    body: formData,
    timeoutMs: 90000,
  });
}

export async function resetProfileAvatar() {
  return apiRequest('/api/v1/profile/me/avatar', {
    method: 'DELETE',
  });
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
