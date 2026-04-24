import React, { useMemo, useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import StatCard from './components/StatCard';
import ShipmentChart from './components/ShipmentChart';
import SalesChart from './components/SalesChart';
import WagesChart from './components/WagesChart';
import ValueChart from './components/ValueChart';
import WorkPeriodChart from './components/WorkPeriodChart';
import { getInsightWarehouseRows, getProjectDetailData } from './api';
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

const formatCurrency = (value) => `${currencyFormatter.format(Number(value || 0))} THB`;

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

const ProjectDetailPage = () => {
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

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '32px' }}>Project</h1>
        <div style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          gap: '8px', 
          backgroundColor: 'white', 
          padding: '8px 40px', 
          borderRadius: '12px',
          border: '1.5px solid var(--border-color)',
          width: 'fit-content',
          fontSize: '24px'
        }}>
          {passedProjectName || data.name}
        </div>
        {focusMessage ? (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#ecfdf5',
              color: '#166534',
              border: '1px solid #86efac',
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
      
      <div className="dashboard-grid">
        {data.stats.map((stat, index) => (
          <StatCard key={index} index={index} title={stat.title} value={stat.value} />
        ))}
      </div>

      <div className="chart-section">
        <ShipmentChart data={data.shipmentData} />
        <SalesChart data={data.salesData} />
      </div>

      <div className="bottom-section" style={{ marginBottom: '40px' }}>
        <WagesChart data={data.wagesData} />
        <ValueChart data={data.valueData} />
        <WorkPeriodChart data={data.workPeriodData} />
      </div>

      <div
        className="card"
        style={{
          backgroundColor: 'white',
          marginBottom: '40px',
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
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px' }}>Installments</h3>
                  <p style={{ margin: '6px 0 0', color: '#666', fontSize: '14px' }}>
                    {projectInstallmentRows.length} records in this project
                  </p>
                </div>
              </div>

              {projectInstallmentRows.length === 0 ? (
                <div style={{ color: '#666' }}>ไม่พบ installment records สำหรับโครงการนี้</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
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
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px' }}>Transactions</h3>
                  <p style={{ margin: '6px 0 0', color: '#666', fontSize: '14px' }}>
                    {projectTransactionRows.length} records in this project
                  </p>
                </div>
              </div>

              {projectTransactionRows.length === 0 ? (
                <div style={{ color: '#666' }}>ไม่พบ transaction records สำหรับโครงการนี้</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
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
            marginBottom: '40px',
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

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
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
    </>
  );
};

export default ProjectDetailPage;
