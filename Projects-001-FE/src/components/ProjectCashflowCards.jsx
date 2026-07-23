import React from 'react';
import { ArrowDownToLine, ArrowUpFromLine, ChevronRight, Clock3 } from 'lucide-react';
import { Link } from 'react-router-dom';

const amountFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatAmount = (value) => `${amountFormatter.format(Number(value || 0))} บาท`;

const buildApprovalLink = (projectId, entryType, status) => {
  const params = new URLSearchParams({
    project_id: String(projectId || ''),
    entry_type: entryType,
    status,
  });
  return `/approval?${params.toString()}`;
};

const summarizeRows = (rows, entryType) => {
  const matchingRows = (Array.isArray(rows) ? rows : []).filter(
    (row) => row.sourceType === 'INPUT_REQUEST' && row.entryType === entryType
  );
  const rowsByStatus = (status) => matchingRows.filter((row) => row.status === status);
  const paidRows = rowsByStatus('PAID');
  const approvedRows = rowsByStatus('APPROVED');
  const pendingRows = rowsByStatus('PENDING_ADMIN');
  const sumAmount = (items) => items.reduce((total, item) => total + Number(item.amount || 0), 0);

  return {
    paidAmount: sumAmount(paidRows),
    paidCount: paidRows.length,
    approvedAmount: sumAmount(approvedRows),
    approvedCount: approvedRows.length,
    pendingCount: pendingRows.length,
  };
};

function CashflowMetricLink({ label, value, detail, to, prominent = false }) {
  return (
    <Link className={prominent ? 'project-cashflow-primary' : 'project-cashflow-metric'} to={to}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>
        {detail}
        <ChevronRight aria-hidden="true" size={15} />
      </small>
    </Link>
  );
}

function ProjectCashflowCard({ projectId, entryType, summary }) {
  const isIncome = entryType === 'INCOME';
  const Icon = isIncome ? ArrowDownToLine : ArrowUpFromLine;
  const labels = isIncome
    ? {
        title: 'รายรับโครงการ',
        completed: 'รับเงินแล้ว',
        approved: 'รอรับเงิน',
        tone: 'income',
      }
    : {
        title: 'รายจ่ายโครงการ',
        completed: 'จ่ายเงินแล้ว',
        approved: 'รอจ่ายเงิน',
        tone: 'expense',
      };

  return (
    <article className={`project-cashflow-card ${labels.tone}`}>
      <header className="project-cashflow-card-header">
        <span className="project-cashflow-icon" aria-hidden="true">
          <Icon size={19} />
        </span>
        <div>
          <span>PROJECT CASH FLOW</span>
          <h3>{labels.title}</h3>
        </div>
      </header>

      <CashflowMetricLink
        prominent
        label={labels.completed}
        value={formatAmount(summary.paidAmount)}
        detail={`${summary.paidCount} รายการ`}
        to={buildApprovalLink(projectId, entryType, 'PAID')}
      />

      <div className="project-cashflow-secondary-grid">
        <CashflowMetricLink
          label={labels.approved}
          value={formatAmount(summary.approvedAmount)}
          detail={`${summary.approvedCount} รายการ`}
          to={buildApprovalLink(projectId, entryType, 'APPROVED')}
        />
        <CashflowMetricLink
          label="รอตรวจสอบ"
          value={`${summary.pendingCount} รายการ`}
          detail="ยังไม่รวมในยอด"
          to={buildApprovalLink(projectId, entryType, 'PENDING_ADMIN')}
        />
      </div>
    </article>
  );
}

function ProjectCashflowLoading() {
  return (
    <div className="project-cashflow-grid" aria-label="กำลังโหลดภาพรวมรายรับรายจ่าย" aria-busy="true">
      {['income', 'expense'].map((tone) => (
        <div className={`project-cashflow-card ${tone} loading`} key={tone}>
          <div className="project-cashflow-skeleton short" />
          <div className="project-cashflow-skeleton amount" />
          <div className="project-cashflow-skeleton" />
        </div>
      ))}
    </div>
  );
}

export default function ProjectCashflowCards({
  projectId,
  rows = [],
  loading = false,
  error = '',
}) {
  const incomeSummary = summarizeRows(rows, 'INCOME');
  const expenseSummary = summarizeRows(rows, 'EXPENSE');

  return (
    <section className="project-cashflow-section" aria-labelledby="project-cashflow-title">
      <div className="project-cashflow-section-heading">
        <div>
          <span className="project-cashflow-kicker">
            <Clock3 size={14} />
            อัปเดตจากหน้าอนุมัติ
          </span>
          <h2 id="project-cashflow-title">ภาพรวมรับ–จ่ายของโครงการ</h2>
        </div>
        <p>ยอดรอตรวจสอบจะแสดงเป็นจำนวนรายการ และยังไม่นำมารวมกับยอดเงินจริง</p>
      </div>

      {loading ? <ProjectCashflowLoading /> : null}

      {!loading && error ? (
        <div className="project-cashflow-error" role="status">
          ไม่สามารถโหลดภาพรวมรับ–จ่ายได้ในขณะนี้ แต่ข้อมูลส่วนอื่นของโครงการยังใช้งานได้
        </div>
      ) : null}

      {!loading && !error ? (
        <div className="project-cashflow-grid">
          <ProjectCashflowCard projectId={projectId} entryType="INCOME" summary={incomeSummary} />
          <ProjectCashflowCard projectId={projectId} entryType="EXPENSE" summary={expenseSummary} />
        </div>
      ) : null}
    </section>
  );
}
