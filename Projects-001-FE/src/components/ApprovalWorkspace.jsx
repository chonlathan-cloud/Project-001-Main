import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Banknote,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleDollarSign,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Filter,
  Info,
  ReceiptText,
  ShieldAlert,
} from 'lucide-react';
import ApprovalPaymentInstructions from './ApprovalPaymentInstructions';

const formatAmount = (value) =>
  Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

const titleizeStatus = (value) => String(value || 'UNKNOWN').replaceAll('_', ' ');

const hasFlowAccountIssue = (item) =>
  [
    item?.flowaccount_sync_error,
    item?.flowaccount_attachment_error,
    item?.flowaccount_supplier_invoice_error,
    item?.flowaccount_payment_error,
  ].some(Boolean) ||
  [
    item?.flowaccount_sync_status,
    item?.flowaccount_attachment_status,
    item?.flowaccount_supplier_invoice_status,
    item?.flowaccount_payment_status,
  ].some((status) => String(status || '').includes('FAILED'));

const getStatusTone = (status) => {
  if (status === 'PAID') return 'success';
  if (status === 'APPROVED') return 'ready';
  if (status === 'REJECTED') return 'danger';
  if (status === 'PENDING_ADMIN') return 'warning';
  return 'neutral';
};

const getFlowStatusTone = (status) => {
  const normalized = String(status || 'NOT_READY').toUpperCase();
  if (normalized.includes('FAILED') || normalized.includes('ERROR')) return 'danger';
  if (normalized.includes('SYNCED') || normalized.includes('PAID')) return 'success';
  if (normalized.includes('PENDING') || normalized.includes('READY')) return 'warning';
  return 'neutral';
};

const getQueueAlerts = (item) => {
  const alerts = [];
  if (item?.is_duplicate_flag) alerts.push({ label: 'Duplicate', tone: 'warning' });
  if (item?.ocr_low_confidence_fields?.length) alerts.push({ label: 'OCR', tone: 'warning' });
  if (hasFlowAccountIssue(item)) alerts.push({ label: 'FlowAccount', tone: 'danger' });
  if (!item?.receipt_storage_key) alerts.push({ label: 'No receipt', tone: 'neutral' });
  return alerts;
};

function AlertIcon({ tone }) {
  if (tone === 'success') return <CheckCircle2 size={17} />;
  if (tone === 'critical' || tone === 'danger') return <AlertCircle size={17} />;
  if (tone === 'warning') return <AlertTriangle size={17} />;
  return <Info size={17} />;
}

function ActionButton({ action, compact = false }) {
  const Icon = action.icon;

  return (
    <button
      type="button"
      className={`approval-button ${action.variant || 'secondary'}${compact ? ' compact' : ''}`}
      onClick={action.onClick}
      disabled={action.disabled}
      title={action.disabled && action.disabledReason ? action.disabledReason : action.label}
    >
      {Icon ? <Icon size={compact ? 14 : 16} /> : null}
      <span>{action.label}</span>
    </button>
  );
}

export function ApprovalSummaryStrip({ requests = [], refreshing = false, isDeepLinkedRequest = false, deepLinkRequestId = '' }) {
  const pendingCount = requests.filter((item) => item.status === 'PENDING_ADMIN').length;
  const approvedCount = requests.filter((item) => item.status === 'APPROVED').length;
  const alertCount = requests.filter((item) =>
    item.is_duplicate_flag || item.ocr_low_confidence_fields?.length || hasFlowAccountIssue(item)
  ).length;
  const totalAmount = requests.reduce(
    (sum, item) => sum + Number(item.approved_amount ?? item.amount ?? 0),
    0
  );

  const metrics = [
    { label: 'Current view', value: requests.length, detail: `${formatAmount(totalAmount)} THB`, tone: 'neutral' },
    { label: 'Pending admin', value: pendingCount, detail: 'Needs review', tone: pendingCount ? 'warning' : 'success' },
    { label: 'Approved', value: approvedCount, detail: 'Ready for payment/sync', tone: 'ready' },
    { label: 'Alerts', value: alertCount, detail: 'Duplicate, OCR, or sync', tone: alertCount ? 'danger' : 'success' },
  ];

  return (
    <section className="approval-summary-strip" aria-label="Approval queue summary">
      <div className="approval-summary-grid">
        {metrics.map((metric) => (
          <article className={`approval-summary-card ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </div>

      {(refreshing || isDeepLinkedRequest) ? (
        <div className="approval-context-row">
          {refreshing ? (
            <span className="approval-refreshing">
              <CircleDollarSign size={15} />
              Refreshing queue
            </span>
          ) : null}
          {isDeepLinkedRequest ? (
            <span className="approval-deeplink">
              <ClipboardCheck size={15} />
              Focused from Insight Warehouse: {deepLinkRequestId}
            </span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function ApprovalQueuePanel({
  filters,
  onFilterChange,
  statusOptions,
  entryTypeOptions,
  projectOptions,
  requests,
  selectedRequestId,
  onSelectRequest,
  formatEntryType,
}) {
  return (
    <aside className="approval-queue-panel">
      <header className="approval-panel-header">
        <div>
          <span className="approval-kicker">
            <Filter size={15} />
            Review Queue
          </span>
          <h2>Requests</h2>
        </div>
        <strong>{requests.length}</strong>
      </header>

      <div className="approval-filter-grid">
        <select
          value={filters.status}
          onChange={(event) => onFilterChange((current) => ({ ...current, status: event.target.value }))}
          aria-label="Filter by status"
        >
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.entryType}
          onChange={(event) => onFilterChange((current) => ({ ...current, entryType: event.target.value }))}
          aria-label="Filter by entry type"
        >
          {entryTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.projectId}
          onChange={(event) => onFilterChange((current) => ({ ...current, projectId: event.target.value }))}
          aria-label="Filter by project"
        >
          {projectOptions.map((option) => (
            <option key={option.project_id || 'all-projects'} value={option.project_id}>{option.name}</option>
          ))}
        </select>
      </div>

      <div className="approval-queue-list">
        {requests.length === 0 ? (
          <div className="approval-empty-state">ไม่พบรายการในคิวตาม filter ปัจจุบัน</div>
        ) : (
          requests.map((item) => {
            const isActive = item.request_id === selectedRequestId;
            const queueAlerts = getQueueAlerts(item);

            return (
              <button
                key={item.request_id}
                type="button"
                className={`approval-queue-item${isActive ? ' active' : ''}`}
                onClick={() => onSelectRequest(item.request_id)}
              >
                <span className="approval-queue-topline">
                  <strong>{item.project_name || '-'}</strong>
                  <span className={`approval-status-badge ${getStatusTone(item.status)}`}>
                    {titleizeStatus(item.status)}
                  </span>
                </span>
                <span className="approval-queue-person">{item.vendor_name || item.requester_name || '-'}</span>
                <span className="approval-queue-meta">
                  <span>{formatEntryType(item.entry_type)} · {item.request_type || 'ไม่ระบุประเภท'}</span>
                  <strong>{formatAmount(item.approved_amount ?? item.amount)} THB</strong>
                </span>
                {queueAlerts.length ? (
                  <span className="approval-queue-alerts">
                    {queueAlerts.map((alert) => (
                      <span className={`approval-chip ${alert.tone}`} key={alert.label}>{alert.label}</span>
                    ))}
                  </span>
                ) : null}
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}

export function ApprovalRequestHeader({ request, formatEntryType, alertCount = 0 }) {
  if (!request) return null;

  return (
    <section className="approval-request-header">
      <div>
        <div className="approval-request-eyebrow">
          <span className={`approval-status-badge ${getStatusTone(request.status)}`}>
            {titleizeStatus(request.status)}
          </span>
          <span>{formatEntryType(request.entry_type)}</span>
          <span>{request.request_date || '-'}</span>
        </div>
        <h2>{request.project_name || '-'}</h2>
        <p>{request.requester_name || '-'} · {request.request_type || 'ไม่ระบุประเภท'}</p>
      </div>
      <div className="approval-request-amount">
        <span>Approved amount</span>
        <strong>{formatAmount(request.approved_amount ?? request.amount)} THB</strong>
        <small>{alertCount ? `${alertCount} item${alertCount > 1 ? 's' : ''} need attention` : 'Ready for review'}</small>
      </div>
    </section>
  );
}

export function ApprovalAlertStack({ alerts = [] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleAlerts = expanded ? alerts : alerts.slice(0, 3);

  return (
    <section className="approval-alert-stack" aria-label="Approval alerts">
      <header className="approval-section-heading compact">
        <div>
          <span className="approval-kicker">
            <ShieldAlert size={15} />
            Needs Attention
          </span>
          <h3>Alert management</h3>
        </div>
        {alerts.length ? <strong>{alerts.length}</strong> : null}
      </header>

      {alerts.length === 0 ? (
        <div className="approval-alert-empty">
          <CheckCircle2 size={18} />
          <span>No blocking alerts on this request.</span>
        </div>
      ) : (
        <>
          <div className="approval-alert-list">
            {visibleAlerts.map((alert) => (
              <article className={`approval-alert-item ${alert.tone || 'info'}`} key={`${alert.title}-${alert.message}`}>
                <span className="approval-alert-icon">
                  <AlertIcon tone={alert.tone} />
                </span>
                <span>
                  <strong>{alert.title}</strong>
                  {alert.message ? <small>{alert.message}</small> : null}
                </span>
                {alert.action ? (
                  <button
                    type="button"
                    onClick={alert.action.onClick}
                    disabled={alert.action.disabled}
                  >
                    {alert.action.label}
                  </button>
                ) : null}
              </article>
            ))}
          </div>
          {alerts.length > 3 ? (
            <button
              type="button"
              className="approval-alert-toggle"
              onClick={() => setExpanded((current) => !current)}
            >
              {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
              <span>{expanded ? 'Show fewer alerts' : `Show ${alerts.length - 3} more alert${alerts.length - 3 > 1 ? 's' : ''}`}</span>
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}

export function ApprovalFlowAccountChecklist({
  enabled,
  ready,
  steps = [],
  messages = [],
  actions = [],
  compact = false,
  title,
  statusLabel,
}) {
  return (
    <section className={`approval-flow-card${compact ? ' compact' : ''}`}>
      <header className="approval-section-heading compact">
        <div>
          <span className="approval-kicker">
            <CircleDollarSign size={15} />
            Accounting / FlowAccount
          </span>
          <h3>{title || (enabled ? 'Sync checklist' : 'Integration disabled')}</h3>
        </div>
        <span className={`approval-status-badge ${ready ? 'success' : 'warning'}`}>
          {statusLabel || (ready ? 'READY' : 'NOT READY')}
        </span>
      </header>

      <div className="approval-flow-steps">
        {steps.map((step) => (
          <div className="approval-flow-step" key={step.label}>
            <span className={`approval-flow-dot ${getFlowStatusTone(step.status)}`} />
            <span>
              <strong>{step.label}</strong>
              <small>{step.detail || titleizeStatus(step.status || 'NOT_READY')}</small>
            </span>
            <span className={`approval-status-badge ${getFlowStatusTone(step.status)}`}>
              {titleizeStatus(step.status || 'NOT_READY')}
            </span>
          </div>
        ))}
      </div>

      {messages.length ? (
        <div className="approval-flow-messages">
          {messages.map((message) => (
            <div className={`approval-flow-message ${message.tone || 'info'}`} key={`${message.tone}-${message.text}`}>
              <AlertIcon tone={message.tone} />
              <span>{message.text}</span>
            </div>
          ))}
        </div>
      ) : null}

      {actions.length ? (
        <div className="approval-flow-actions">
          {actions.map((action) => (
            <ActionButton action={action} compact key={action.label} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function ApprovalEvidencePanel({
  request,
  editor,
  onFieldChange,
  canEdit,
  receiptPreview,
  receiptPreviewLoading,
  receiptPreviewError,
  canPreviewReceipt,
  isPreviewImage,
  isPreviewPdf,
}) {
  if (!request) return null;

  return (
    <aside className="approval-evidence-panel">
      <ApprovalPaymentInstructions
        request={request}
        editor={editor}
        onFieldChange={onFieldChange}
        canEdit={canEdit}
      />

      <section className="approval-side-card">
        <header className="approval-side-card-head">
          <div>
            <span className="approval-kicker">
              <ReceiptText size={15} />
              Receipt
            </span>
            <h3>Preview</h3>
            <p>{request.receipt_file_name || 'ไม่มีชื่อไฟล์แนบ'}</p>
          </div>
          {canPreviewReceipt ? (
            <a className="approval-link-button" href={receiptPreview.signed_url} target="_blank" rel="noreferrer">
              <ExternalLink size={15} />
              <span>Open</span>
            </a>
          ) : null}
        </header>

        {receiptPreviewLoading ? (
          <div className="approval-muted-box">กำลังโหลดลิงก์ไฟล์จาก GCS...</div>
        ) : null}

        {receiptPreviewError ? (
          <div className="approval-error-box">{receiptPreviewError}</div>
        ) : null}

        {!request.receipt_storage_key && !receiptPreviewLoading ? (
          <div className="approval-muted-box">รายการนี้ยังไม่มีไฟล์ receipt ที่เก็บไว้</div>
        ) : null}

        {canPreviewReceipt && isPreviewImage ? (
          <div className="approval-receipt-preview">
            <img src={receiptPreview.signed_url} alt={receiptPreview.file_name || 'Receipt preview'} />
          </div>
        ) : null}

        {canPreviewReceipt && isPreviewPdf ? (
          <div className="approval-receipt-preview">
            <iframe src={receiptPreview.signed_url} title={receiptPreview.file_name || 'Receipt PDF preview'} />
          </div>
        ) : null}

        {canPreviewReceipt && !isPreviewImage && !isPreviewPdf ? (
          <div className="approval-muted-box">ไฟล์นี้ไม่ใช่รูปภาพ ใช้ปุ่ม Open เพื่อเปิดไฟล์ต้นฉบับ</div>
        ) : null}
      </section>

      <ApprovalFinancialSnapshot request={request} />
    </aside>
  );
}

export function ApprovalFormSection({ title, description, children }) {
  return (
    <section className="approval-form-section">
      <header className="approval-section-heading">
        <div>
          <h3>{title}</h3>
          {description ? <p>{description}</p> : null}
        </div>
      </header>
      {children}
    </section>
  );
}

export function ApprovalField({ label, wide = false, required = false, hint = '', error = '', children }) {
  return (
    <label className={`approval-field${wide ? ' wide' : ''}${error ? ' has-error' : ''}`}>
      <span className="approval-field-label">
        <span>
          {label}
          {required ? <span className="approval-required-star" aria-label="จำเป็นต้องกรอก">*</span> : null}
        </span>
        {hint ? <small>{hint}</small> : null}
      </span>
      {children}
      {error ? <small className="approval-field-error">{error}</small> : null}
    </label>
  );
}

export function ApprovalFinancialSnapshot({ request }) {
  if (!request) return null;

  const items = [
    ['Requested', `${formatAmount(request.amount)} THB`],
    ['Approved', `${formatAmount(request.approved_amount ?? request.amount)} THB`],
    ['Vendor', request.vendor_name || '-'],
    ['Bank', request.bank_name || request.bank_account?.bank_name || '-'],
    ['Account No', request.account_no || request.bank_account?.account_no || '-'],
    ['Account Name', request.account_name || request.bank_account?.account_name || '-'],
    ['Receipt No', request.receipt_no || '-'],
    ['Document Date', request.document_date || '-'],
    ['VAT Mode', request.accounting_vat_mode || '-'],
    ['WHT Rate', request.accounting_wht_rate ?? '-'],
    ['Reviewed At', request.reviewed_at || '-'],
    ['Paid At', request.paid_at || '-'],
  ];

  return (
    <section className="approval-side-card">
      <header className="approval-side-card-head">
        <div>
          <span className="approval-kicker">
            <Banknote size={15} />
            Financial
          </span>
          <h3>Snapshot</h3>
        </div>
      </header>
      <div className="approval-snapshot-grid">
        {items.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ApprovalActionBar({ canMutate, actions = [] }) {
  const disabledHints = actions
    .filter((action) => action.disabled && action.disabledReason)
    .map((action) => action.disabledReason);

  if (!canMutate) {
    return (
      <div className="approval-action-bar readonly">
        <Info size={17} />
        <span>Read-only admin access. Owner permission is required to edit, approve, reject, or mark requests as paid.</span>
      </div>
    );
  }

  return (
    <div className="approval-action-bar">
      <div className="approval-action-buttons">
        {actions.map((action) => (
          <ActionButton action={action} key={action.label} />
        ))}
      </div>
      {disabledHints.length ? (
        <div className="approval-action-hint">
          <FileText size={14} />
          <span>{disabledHints[0]}</span>
        </div>
      ) : null}
    </div>
  );
}
