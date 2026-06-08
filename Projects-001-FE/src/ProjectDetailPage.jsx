import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  ArrowLeftRight,
  Building2,
  Calculator,
  Layers3,
  TriangleAlert,
  Wallet,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getInsightWarehouseRows, getProjectDetailData } from './api';
import BoqSheetCharts from './components/BoqSheetCharts';
import BoqWorkbench from './components/BoqWorkbench';
import Loading from './components/Loading';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const dateFormatter = new Intl.DateTimeFormat('en-CA', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

const formatCurrency = (value) => `${currencyFormatter.format(Number(value || 0))} THB`;
const formatPercent = (value) => `${Number(value || 0).toFixed(1)}%`;

const formatDate = (value) => {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return dateFormatter.format(parsed);
};

const prettifyValue = (value) => {
  const cleaned = String(value || '').trim();
  return cleaned ? cleaned.replace(/_/g, ' ') : '-';
};

const sourceTypeLabel = (value) => {
  switch (value) {
    case 'INSTALLMENT':
      return 'Installment';
    case 'TRANSACTION':
      return 'Transaction';
    default:
      return prettifyValue(value);
  }
};

const shortenLabel = (value, maxLength = 26) => {
  const cleaned = String(value || '').trim();
  if (!cleaned) return '-';
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength - 1)}…`;
};

const buildAnalyzePrompt = (row, projectName) => {
  const details = [
    `ช่วยวิเคราะห์รายการ ${sourceTypeLabel(row.sourceType)} นี้ในบริบทของโครงการ ${projectName || row.projectName || '-'}`,
    row.referenceNo ? `Reference: ${row.referenceNo}` : '',
    row.title ? `Title: ${row.title}` : '',
    row.status ? `Status: ${prettifyValue(row.status)}` : '',
    row.flowDirection ? `Flow: ${prettifyValue(row.flowDirection)}` : '',
    row.amount != null ? `Amount: ${formatCurrency(row.amount)}` : '',
    row.eventDate ? `Event Date: ${formatDate(row.eventDate)}` : '',
    row.dueDate ? `Due Date: ${formatDate(row.dueDate)}` : '',
    row.actorName ? `Actor: ${row.actorName}` : '',
    row.description ? `Description: ${row.description}` : '',
  ].filter(Boolean);

  return `${details.join('\n')}\n\nสรุปความหมายทางธุรกิจ ความเสี่ยง ผลกระทบต่อ cash flow และสิ่งที่ควรทำต่อ`;
};

const warehouseCardTone = (row, isHighlighted = false) => ({
  backgroundColor: isHighlighted ? '#fff8eb' : '#ffffff',
  borderColor: isHighlighted ? '#d6a847' : '#e7decd',
  boxShadow: isHighlighted ? '0 12px 32px rgba(214,168,71,0.14)' : 'none',
});

const executionToneStyles = {
  neutral: { fill: '#94a3b8', text: '#475569', background: '#f8fafc', border: '#e2e8f0' },
  positive: { fill: '#22c55e', text: '#166534', background: '#f0fdf4', border: '#bbf7d0' },
  warning: { fill: '#f59e0b', text: '#92400e', background: '#fff7ed', border: '#fdba74' },
  danger: { fill: '#ef4444', text: '#b91c1c', background: '#fef2f2', border: '#fecaca' },
};

const baseChartTooltipStyle = {
  borderRadius: '14px',
  border: '1px solid #e5e7eb',
  boxShadow: 'none',
};

function SummaryCard({ icon, label, value, subtext, tone = 'neutral' }) {
  const toneStyles = {
    neutral: { background: '#ffffff', border: '#e5e7eb', text: '#111827', subtle: '#6b7280' },
    positive: { background: '#f0fdf4', border: '#bbf7d0', text: '#166534', subtle: '#15803d' },
    warning: { background: '#fff7ed', border: '#fdba74', text: '#9a3412', subtle: '#c2410c' },
    danger: { background: '#fef2f2', border: '#fecaca', text: '#991b1b', subtle: '#b91c1c' },
  };
  const currentTone = toneStyles[tone] || toneStyles.neutral;
  const IconComponent = icon;

  return (
    <div
      style={{
        backgroundColor: currentTone.background,
        border: `1px solid ${currentTone.border}`,
        borderRadius: '12px',
        padding: '22px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        minHeight: '150px',
      }}
    >
      <div
        style={{
          width: '42px',
          height: '42px',
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255,255,255,0.7)',
          color: currentTone.text,
        }}
      >
        {IconComponent ? <IconComponent size={18} /> : null}
      </div>

      <div>
        <div style={{ fontSize: '13px', fontWeight: '700', color: currentTone.subtle }}>{label}</div>
        <div style={{ marginTop: '8px', fontSize: '28px', fontWeight: '800', color: currentTone.text }}>
          {value}
        </div>
      </div>

      <div style={{ marginTop: 'auto', fontSize: '12px', lineHeight: 1.6, color: currentTone.subtle }}>
        {subtext}
      </div>
    </div>
  );
}

function ChartCard({ title, description, children }) {
  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        minHeight: '360px',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <h3 style={{ margin: 0, fontSize: '18px' }}>{title}</h3>
        <p style={{ margin: 0, color: '#6b7280', fontSize: '13px', lineHeight: 1.6 }}>
          {description}
        </p>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
}

function ChartEmptyState({ message }) {
  return (
    <div
      style={{
        height: '100%',
        minHeight: '240px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '18px',
        backgroundColor: '#fafaf9',
        border: '1px dashed #d6d3d1',
        color: '#6b7280',
        fontSize: '14px',
        textAlign: 'center',
        padding: '20px',
      }}
    >
      {message}
    </div>
  );
}

const WarehouseRecordCard = ({ row, projectName, highlight = false }) => (
  <div
    style={{
      border: '1px solid',
      borderRadius: '18px',
      padding: '18px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      ...warehouseCardTone(row, highlight),
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
      <div>
        <div style={{ fontSize: '12px', color: '#9a8b73', fontWeight: '700', textTransform: 'uppercase' }}>
          {sourceTypeLabel(row.sourceType)}
        </div>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginTop: '6px' }}>
          {row.title || '-'}
        </div>
      </div>
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
          textTransform: 'uppercase',
        }}
      >
        {prettifyValue(row.status)}
      </div>
    </div>

    <div style={{ color: '#555', fontSize: '14px' }}>{row.description || '-'}</div>

    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px', color: '#4b5563' }}>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Reference</strong>
        <span>{row.referenceNo || '-'}</span>
      </div>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Amount</strong>
        <span>{row.amount == null ? '-' : formatCurrency(row.amount)}</span>
      </div>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Event Date</strong>
        <span>{formatDate(row.eventDate)}</span>
      </div>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Due Date</strong>
        <span>{formatDate(row.dueDate)}</span>
      </div>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Actor</strong>
        <span>{row.actorName || row.actorId || '-'}</span>
      </div>
      <div>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Flow</strong>
        <span>{prettifyValue(row.flowDirection)}</span>
      </div>
    </div>

    {row.flags?.length ? (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '6px' }}>
        {row.flags.map((flag) => (
          <span
            key={`${row.id}-${flag.key}`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '4px 8px',
              borderRadius: '999px',
              backgroundColor:
                flag.tone === 'danger'
                  ? '#fee2e2'
                  : flag.tone === 'warning'
                    ? '#fef3c7'
                    : flag.tone === 'positive'
                      ? '#dcfce7'
                      : '#f3f4f6',
              color:
                flag.tone === 'danger'
                  ? '#b91c1c'
                  : flag.tone === 'warning'
                    ? '#92400e'
                    : flag.tone === 'positive'
                      ? '#166534'
                      : '#4b5563',
              fontSize: '11px',
              fontWeight: '700',
            }}
          >
            {flag.label}
          </span>
        ))}
      </div>
    ) : null}

    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '6px' }}>
      {row.navigationTarget?.path ? (
        <Link
          to={row.navigationTarget.path}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '9px 12px',
            borderRadius: '12px',
            border: '1px solid #ded4c2',
            backgroundColor: '#faf7f1',
            color: '#5f4b27',
            textDecoration: 'none',
            fontSize: '13px',
            fontWeight: '700',
          }}
        >
          {row.navigationTarget.label || 'Open'}
        </Link>
      ) : null}

      <Link
        to="/chat-ai"
        state={{
          projectId: row.projectId,
          projectName: projectName || row.projectName,
          initialPrompt: buildAnalyzePrompt(row, projectName || row.projectName),
          autoSubmit: true,
          contextLabel: `Focused ${sourceTypeLabel(row.sourceType)} from Project Detail`,
        }}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '9px 12px',
          borderRadius: '12px',
          border: '1px solid #d6a847',
          backgroundColor: '#fff7e8',
          color: '#8b6d3f',
          textDecoration: 'none',
          fontSize: '13px',
          fontWeight: '700',
        }}
      >
        Analyze In Chat
      </Link>
    </div>
  </div>
);

function ProjectDetailPage() {
  const { projectId: routeProjectId } = useParams();
  const location = useLocation();
  const passedProjectName = location.state?.projectName;
  const stateProjectId = location.state?.projectId;
  const projectId = routeProjectId || stateProjectId;
  const deepLinkParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const deepLinkSource = deepLinkParams.get('source') || '';
  const deepLinkInstallmentId = deepLinkParams.get('installment_id') || '';
  const deepLinkTransactionId = deepLinkParams.get('transaction_id') || '';
  const focusMessage = deepLinkInstallmentId
    ? `Focused from Insight Warehouse: installment ${deepLinkInstallmentId}`
    : deepLinkTransactionId
      ? `Focused from Insight Warehouse: transaction ${deepLinkTransactionId}`
      : deepLinkSource
        ? `Focused from Insight Warehouse: ${deepLinkSource}`
        : '';

  const [data, setData] = useState(null);
  const [focusedRows, setFocusedRows] = useState([]);
  const [projectInstallmentRows, setProjectInstallmentRows] = useState([]);
  const [projectTransactionRows, setProjectTransactionRows] = useState([]);
  const [focusedRowsLoading, setFocusedRowsLoading] = useState(false);
  const [projectRowsLoading, setProjectRowsLoading] = useState(false);
  const [focusedRowsError, setFocusedRowsError] = useState('');
  const [projectRowsError, setProjectRowsError] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeView, setActiveView] = useState('compare');
  const [sheetFilter, setSheetFilter] = useState('ALL');

  useEffect(() => {
    const loadData = async () => {
      if (!projectId) {
        setError('Project id is missing. Please open this page from the project list.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError('');
        const result = await getProjectDetailData(projectId);
        setData(result);
      } catch (loadError) {
        setError(loadError.message || 'Failed to load project detail.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [projectId]);

  useEffect(() => {
    const loadFocusedRows = async () => {
      const targetSourceType =
        deepLinkInstallmentId
          ? 'INSTALLMENT'
          : deepLinkTransactionId
            ? 'TRANSACTION'
            : '';

      if (!projectId || !targetSourceType) {
        setFocusedRows([]);
        setFocusedRowsError('');
        setFocusedRowsLoading(false);
        return;
      }

      try {
        setFocusedRowsLoading(true);
        setFocusedRowsError('');
        const response = await getInsightWarehouseRows({
          projectId,
          sourceTypes: [targetSourceType],
          page: 1,
          pageSize: 200,
          sortBy: 'event_date',
          sortOrder: 'desc',
        });

        const targetSourceId = deepLinkInstallmentId || deepLinkTransactionId;
        const matchedRows = (response.items || []).filter((item) => item.sourceId === targetSourceId);
        setFocusedRows(matchedRows);
      } catch (loadError) {
        setFocusedRows([]);
        setFocusedRowsError(loadError.message || 'Failed to load focused project records.');
      } finally {
        setFocusedRowsLoading(false);
      }
    };

    loadFocusedRows();
  }, [deepLinkInstallmentId, deepLinkTransactionId, projectId]);

  useEffect(() => {
    const loadProjectLevelRows = async () => {
      if (!projectId) {
        setProjectInstallmentRows([]);
        setProjectTransactionRows([]);
        setProjectRowsError('');
        setProjectRowsLoading(false);
        return;
      }

      try {
        setProjectRowsLoading(true);
        setProjectRowsError('');

        const [installmentResponse, transactionResponse] = await Promise.all([
          getInsightWarehouseRows({
            projectId,
            sourceTypes: ['INSTALLMENT'],
            page: 1,
            pageSize: 200,
            sortBy: 'event_date',
            sortOrder: 'desc',
          }),
          getInsightWarehouseRows({
            projectId,
            sourceTypes: ['TRANSACTION'],
            page: 1,
            pageSize: 200,
            sortBy: 'event_date',
            sortOrder: 'desc',
          }),
        ]);

        setProjectInstallmentRows(installmentResponse.items || []);
        setProjectTransactionRows(transactionResponse.items || []);
      } catch (loadError) {
        setProjectInstallmentRows([]);
        setProjectTransactionRows([]);
        setProjectRowsError(loadError.message || 'Failed to load project-level warehouse records.');
      } finally {
        setProjectRowsLoading(false);
      }
    };

    loadProjectLevelRows();
  }, [projectId]);

  if (loading) return <Loading />;
  if (error) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {error}
      </div>
    );
  }

  const sheetNames = data?.compareSummary?.sheetNames || [];
  const customerTree = Array.isArray(data?.customerTree) ? data.customerTree : [];
  const subcontractorTree = Array.isArray(data?.subcontractorTree) ? data.subcontractorTree : [];
  const compareTree = Array.isArray(data?.compareTree) ? data.compareTree : [];
  const hasCustomerBoq = customerTree.length > 0;
  const hasSubcontractorBoq = subcontractorTree.length > 0;
  const compareSummary = data?.compareSummary || {};
  const wbsSummary = Array.isArray(data?.wbsSummary) ? data.wbsSummary : [];
  const executionSummary = Array.isArray(data?.executionSummary) ? data.executionSummary : [];
  const compareTone =
    compareSummary.totalVariance > 0
      ? 'positive'
      : compareSummary.totalVariance < 0
        ? 'danger'
        : 'neutral';
  const executionChartData = executionSummary.map((item) => ({
    ...item,
    shortLabel: shortenLabel(item.label, 18),
    fill: (executionToneStyles[item.tone] || executionToneStyles.neutral).fill,
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <section
        style={{
          borderRadius: '12px',
          padding: '28px',
          color: 'var(--text-main)',
          background: 'var(--card-bg)',
          border: '1px solid var(--border-color)',
          boxShadow: 'none',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              borderRadius: '999px',
              backgroundColor: 'rgba(79, 111, 100, 0.12)',
              color: 'var(--primary)',
              width: 'fit-content',
              fontSize: '12px',
              fontWeight: '700',
            }}
          >
            <Layers3 size={14} />
            Project Detail for dual BOQ comparison
          </div>

          <div>
            <h1 style={{ fontSize: '34px', lineHeight: 1.12, marginBottom: '8px' }}>
              {passedProjectName || data.name}
            </h1>
            <p style={{ maxWidth: '760px', fontSize: '15px', lineHeight: 1.7, color: 'var(--text-muted)' }}>
              หน้านี้ใช้เทียบ Customer BOQ กับ Subcontractor BOQ ในโครงสร้าง WBS เดียวกัน เพื่อให้เห็นงบ,
              variance และ margin ในแต่ละ node ได้ทันที
            </p>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '7px 10px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              Type: {data.projectType || '-'}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '7px 10px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              Status: {prettifyValue(data.status)}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '7px 10px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              Overhead {formatPercent(data.overheadPercent)}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '7px 10px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              Profit {formatPercent(data.profitPercent)}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '7px 10px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '12px',
                fontWeight: '700',
              }}
            >
              Contingency {formatCurrency(data.contingencyBudget)}
            </span>
          </div>

          {focusMessage ? (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                padding: '10px 14px',
                borderRadius: '12px',
                width: 'fit-content',
                fontSize: '13px',
                fontWeight: '600',
              }}
            >
              {focusMessage}
            </div>
          ) : null}
        </div>
      </section>

      {!hasCustomerBoq || !hasSubcontractorBoq ? (
        <section
          className="card"
          style={{
            backgroundColor: '#fff7ed',
            border: '1px solid #fdba74',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}
        >
          <TriangleAlert size={20} color="#c2410c" />
          <div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: '#9a3412' }}>
              Dual BOQ ยังไม่ครบ
            </div>
            <div style={{ marginTop: '6px', fontSize: '13px', lineHeight: 1.6, color: '#c2410c' }}>
              {hasCustomerBoq && !hasSubcontractorBoq
                ? 'พบ Customer BOQ แล้ว แต่ยังไม่มี Subcontractor BOQ'
                : !hasCustomerBoq && hasSubcontractorBoq
                  ? 'พบ Subcontractor BOQ แล้ว แต่ยังไม่มี Customer BOQ'
                  : 'ยังไม่พบทั้ง Customer BOQ และ Subcontractor BOQ สำหรับโครงการนี้'}
            </div>
          </div>
        </section>
      ) : null}

      <section className="project-detail-summary-grid">
        <SummaryCard
          icon={Building2}
          label="Customer BOQ"
          value={formatCurrency(compareSummary.customerTotalBudget)}
          subtext="มูลค่างบรวมฝั่ง Customer ที่ sync เข้ามาในปัจจุบัน"
        />
        <SummaryCard
          icon={Wallet}
          label="Subcontractor BOQ"
          value={formatCurrency(compareSummary.subcontractorTotalBudget)}
          subtext="มูลค่างบรวมฝั่ง Subcontractor ที่ sync เข้ามาในปัจจุบัน"
        />
        <SummaryCard
          icon={ArrowLeftRight}
          label="Total Variance"
          value={formatCurrency(compareSummary.totalVariance)}
          subtext={
            compareSummary.marginPercent == null
              ? 'ยังคำนวณ margin ไม่ได้เพราะไม่มี Customer BOQ total'
              : `Margin ${formatPercent(compareSummary.marginPercent)} จากฐาน Customer BOQ`
          }
          tone={compareTone}
        />
        <SummaryCard
          icon={Calculator}
          label="Matching Coverage"
          value={`${compareSummary.matchedCount || 0} matched`}
          subtext={`Customer only ${compareSummary.customerOnlyCount || 0} • Subcontractor only ${compareSummary.subcontractorOnlyCount || 0}`}
          tone={(compareSummary.customerOnlyCount || 0) + (compareSummary.subcontractorOnlyCount || 0) > 0 ? 'warning' : 'positive'}
        />
      </section>

      <section className="project-detail-chart-grid">
        <BoqSheetCharts wbsSummary={wbsSummary} />

        <ChartCard
          title="Execution Status"
          description="ดูผลกระทบด้าน execution ของโครงการจาก approved transactions, rejected requests และ input requests"
        >
          {executionChartData.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
              <div style={{ flex: 1, minHeight: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={executionChartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                    <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="shortLabel"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#6b7280' }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#6b7280' }}
                      tickFormatter={(value) => compactCurrencyFormatter.format(Number(value || 0))}
                    />
                    <Tooltip
                      formatter={(value, _name, item) => [
                        `${formatCurrency(value)} • ${item?.payload?.count || 0} items`,
                        item?.payload?.label || 'Execution Status',
                      ]}
                      labelFormatter={(_, payload) => payload?.[0]?.payload?.label || '-'}
                      contentStyle={baseChartTooltipStyle}
                    />
                    <Bar dataKey="amount" radius={[8, 8, 0, 0]}>
                      {executionChartData.map((entry) => (
                        <Cell key={entry.key} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="project-detail-execution-grid">
                {executionChartData.map((item) => {
                  const tone = executionToneStyles[item.tone] || executionToneStyles.neutral;
                  return (
                    <div
                      key={item.key}
                      style={{
                        border: `1px solid ${tone.border}`,
                        backgroundColor: tone.background,
                        borderRadius: '16px',
                        padding: '14px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div style={{ fontSize: '12px', fontWeight: '700', color: tone.text }}>{item.label}</div>
                      <div style={{ fontSize: '18px', fontWeight: '800', color: '#111827' }}>
                        {formatCurrency(item.amount)}
                      </div>
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>{item.count} records</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <ChartEmptyState message="ยังไม่มี execution summary ของโครงการนี้" />
          )}
        </ChartCard>
      </section>

      <BoqWorkbench
        activeView={activeView}
        onActiveViewChange={setActiveView}
        sheetFilter={sheetFilter}
        onSheetFilterChange={setSheetFilter}
        sheetNames={sheetNames}
        customerTree={customerTree}
        subcontractorTree={subcontractorTree}
        compareTree={compareTree}
      />

      <div
        className="card"
        style={{
          backgroundColor: 'white',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '22px', marginBottom: '8px' }}>Project Warehouse Records</h2>
          <p style={{ color: '#666', margin: 0 }}>
            แสดงรายการระดับโครงการทั้งหมดจาก warehouse สำหรับ installments และ transactions
          </p>
        </div>

        {projectRowsLoading ? (
          <div style={{ color: '#666' }}>กำลังโหลด project-level records...</div>
        ) : null}

        {projectRowsError ? (
          <div
            style={{
              color: '#912018',
              backgroundColor: '#fde8e8',
              border: '1px solid #de5b52',
              borderRadius: '12px',
              padding: '10px 12px',
            }}
          >
            {projectRowsError}
          </div>
        ) : null}

        {!projectRowsLoading && !projectRowsError ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
            <section style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px' }}>Installments</h3>
                <p style={{ margin: '6px 0 0', color: '#666', fontSize: '14px' }}>
                  {projectInstallmentRows.length} records in this project
                </p>
              </div>

              {projectInstallmentRows.length === 0 ? (
                <div style={{ color: '#666' }}>ไม่พบ installment records สำหรับโครงการนี้</div>
              ) : (
                <div className="project-detail-record-grid">
                  {projectInstallmentRows.map((row) => (
                    <WarehouseRecordCard
                      key={row.id}
                      row={row}
                      projectName={passedProjectName || data.name}
                      highlight={Boolean(deepLinkInstallmentId && row.sourceId === deepLinkInstallmentId)}
                    />
                  ))}
                </div>
              )}
            </section>

            <section style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px' }}>Transactions</h3>
                <p style={{ margin: '6px 0 0', color: '#666', fontSize: '14px' }}>
                  {projectTransactionRows.length} records in this project
                </p>
              </div>

              {projectTransactionRows.length === 0 ? (
                <div style={{ color: '#666' }}>ไม่พบ transaction records สำหรับโครงการนี้</div>
              ) : (
                <div className="project-detail-record-grid">
                  {projectTransactionRows.map((row) => (
                    <WarehouseRecordCard
                      key={row.id}
                      row={row}
                      projectName={passedProjectName || data.name}
                      highlight={Boolean(deepLinkTransactionId && row.sourceId === deepLinkTransactionId)}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        ) : null}
      </div>

      {deepLinkInstallmentId || deepLinkTransactionId ? (
        <div
          className="card"
          style={{
            backgroundColor: 'white',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px',
          }}
        >
          <div>
            <h2 style={{ fontSize: '22px', marginBottom: '8px' }}>Focused Records</h2>
            <p style={{ color: '#666', margin: 0 }}>
              แสดงรายการที่ถูก deep link มาจาก Insight Warehouse โดยตรง
            </p>
          </div>

          {focusedRowsLoading ? (
            <div style={{ color: '#666' }}>กำลังโหลด focused records...</div>
          ) : null}

          {focusedRowsError ? (
            <div
              style={{
                color: '#912018',
                backgroundColor: '#fde8e8',
                border: '1px solid #de5b52',
                borderRadius: '12px',
                padding: '10px 12px',
              }}
            >
              {focusedRowsError}
            </div>
          ) : null}

          {!focusedRowsLoading && !focusedRowsError && focusedRows.length === 0 ? (
            <div style={{ color: '#666' }}>ไม่พบรายการที่ตรงกับ deep link นี้ใน warehouse records</div>
          ) : null}

          <div className="project-detail-record-grid">
            {focusedRows.map((row) => (
              <WarehouseRecordCard
                key={row.id}
                row={row}
                projectName={passedProjectName || data.name}
                highlight
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ProjectDetailPage;
