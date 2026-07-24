import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileCheck2,
  FileText,
  Image as ImageIcon,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  UserRound,
  X,
} from 'lucide-react';
import {
  getAdminPaymentConfirmations,
  getPaymentConfirmationSignedUrl,
  getSettingSubcontractors,
  reviewAdminPaymentConfirmation,
} from '../api';
import { getStoredAuthUser, isAdminPortalUser } from '../auth';
import Loading from './Loading';
import '../payment-confirmation-review.css';

const STATUS_OPTIONS = [
  {
    value: 'SUBMITTED',
    label: 'รอตรวจสอบ',
    shortLabel: 'รอตรวจ',
    tone: 'warning',
  },
  {
    value: 'VERIFIED',
    label: 'ยืนยันแล้ว',
    shortLabel: 'ยืนยันแล้ว',
    tone: 'success',
  },
  {
    value: 'CHANGES_REQUESTED',
    label: 'ขอแก้ไข',
    shortLabel: 'ขอแก้ไข',
    tone: 'danger',
  },
  {
    value: '',
    label: 'ทั้งหมด',
    shortLabel: 'ทั้งหมด',
    tone: 'neutral',
  },
];

const PREVIEWABLE_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
]);

function formatMoney(value) {
  return new Intl.NumberFormat('th-TH', {
    style: 'currency',
    currency: 'THB',
    minimumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatDate(value, includeTime = false) {
  if (!value) return '—';
  const source = String(value);
  const date = new Date(
    /^\d{4}-\d{2}-\d{2}$/.test(source) ? `${source}T00:00:00` : source,
  );
  if (Number.isNaN(date.getTime())) return source;
  return new Intl.DateTimeFormat('th-TH', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...(includeTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  }).format(date);
}

function formatFileSize(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusMeta(status) {
  return STATUS_OPTIONS.find((item) => item.value === status) || {
    value: status,
    label: status || 'ไม่ทราบสถานะ',
    shortLabel: status || 'ไม่ทราบ',
    tone: 'neutral',
  };
}

function getSubcontractorName(item, profileMap) {
  const profile = profileMap.get(item?.subcontractor_id);
  return profile?.name || profile?.contact_name || item?.subcontractor_id || 'ไม่ทราบผู้รับเงิน';
}

function DetailItem({ label, value, mono = false, wide = false }) {
  return (
    <div className={`payment-review-detail-item${wide ? ' wide' : ''}`}>
      <dt>{label}</dt>
      <dd className={mono ? 'mono' : ''}>{value || '—'}</dd>
    </div>
  );
}

function EvidencePreview({ confirmation, preview, loading, error, onRetry }) {
  const contentType = String(confirmation?.content_type || '').toLowerCase();
  const isImage = PREVIEWABLE_IMAGE_TYPES.has(contentType);
  const isPdf = contentType === 'application/pdf';

  return (
    <section className="payment-review-evidence-card">
      <div className="payment-review-card-heading">
        <div>
          <span className="approval-kicker">
            <FileCheck2 size={15} />
            หลักฐานจากผู้รับเงิน
          </span>
          <h3>{confirmation?.file_name || 'ไฟล์ยืนยันการรับเงิน'}</h3>
          <p>
            {formatFileSize(confirmation?.size_bytes)} · เวอร์ชัน {confirmation?.version || 1}
          </p>
        </div>
        {preview?.url ? (
          <a
            className="payment-review-open-file"
            href={preview.url}
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={15} />
            เปิดต้นฉบับ
          </a>
        ) : null}
      </div>

      <div className="payment-review-preview">
        {loading ? (
          <div className="payment-review-preview-state">
            <span className="payment-review-mini-spinner" aria-hidden="true" />
            กำลังเปิดหลักฐาน...
          </div>
        ) : error ? (
          <div className="payment-review-preview-state error">
            <AlertCircle size={24} />
            <strong>เปิดหลักฐานไม่สำเร็จ</strong>
            <span>{error}</span>
            <button type="button" onClick={onRetry}>
              <RefreshCw size={15} />
              ลองอีกครั้ง
            </button>
          </div>
        ) : preview?.url && isImage ? (
          <img
            src={preview.url}
            alt={`หลักฐานยืนยันการรับเงิน ${confirmation?.internal_reference || ''}`}
          />
        ) : preview?.url && isPdf ? (
          <iframe
            src={preview.url}
            title={`หลักฐานยืนยันการรับเงิน ${confirmation?.internal_reference || ''}`}
          />
        ) : preview?.url ? (
          <div className="payment-review-preview-state">
            <FileText size={32} />
            <strong>เบราว์เซอร์ไม่รองรับการแสดงไฟล์ชนิดนี้</strong>
            <span>กรุณากด “เปิดต้นฉบับ” เพื่อตรวจสอบไฟล์</span>
          </div>
        ) : (
          <div className="payment-review-preview-state">
            <ImageIcon size={32} />
            <span>ยังไม่มีตัวอย่างหลักฐาน</span>
          </div>
        )}
      </div>
    </section>
  );
}

function ReviewDialog({
  dialog,
  confirmation,
  subcontractorName,
  note,
  onNoteChange,
  onClose,
  onConfirm,
  busy,
}) {
  if (!dialog || !confirmation) return null;

  const isVerify = dialog.action === 'VERIFY';
  const noteRequired = !isVerify;
  const ConfirmIcon = isVerify ? ShieldCheck : RotateCcw;

  return (
    <div className="approval-reject-scrim" onMouseDown={onClose}>
      <section
        className={`payment-review-dialog ${isVerify ? 'verify' : 'changes'}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="payment-review-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && !busy) onClose();
        }}
      >
        <header className="payment-review-dialog-header">
          <div>
            <span className="approval-kicker">
              <ConfirmIcon size={15} />
              {isVerify ? 'ยืนยันหลักฐาน' : 'ส่งกลับให้แก้ไข'}
            </span>
            <h3 id="payment-review-dialog-title">
              {isVerify ? 'ยืนยันว่าได้รับเงินถูกต้อง?' : 'ต้องการให้ผู้รับเงินส่งหลักฐานใหม่?'}
            </h3>
            <p>
              {isVerify
                ? 'รายการจะเปลี่ยนเป็น “ยืนยันแล้ว” และปิดงานตรวจสอบนี้'
                : 'เหตุผลจะปรากฏให้ผู้รับเงินเห็น เพื่อให้แก้ไขได้ตรงจุด'}
            </p>
          </div>
          <button
            type="button"
            className="approval-reject-close"
            onClick={onClose}
            disabled={busy}
            aria-label="ปิดหน้าต่างตรวจสอบ"
          >
            <X size={18} />
          </button>
        </header>

        <dl className="payment-review-dialog-summary">
          <div>
            <dt>ผู้รับเงิน</dt>
            <dd>{subcontractorName}</dd>
          </div>
          <div>
            <dt>เลขอ้างอิง</dt>
            <dd>{confirmation.internal_reference}</dd>
          </div>
          <div>
            <dt>โครงการ</dt>
            <dd>{confirmation.project_name}</dd>
          </div>
          <div>
            <dt>ยอดเงิน</dt>
            <dd>{formatMoney(confirmation.amount)}</dd>
          </div>
        </dl>

        <label className="payment-review-note-field">
          <span>
            หมายเหตุถึงผู้รับเงิน
            {noteRequired ? <strong>จำเป็น</strong> : <small>ไม่จำเป็น</small>}
          </span>
          <textarea
            rows={4}
            value={note}
            onChange={(event) => onNoteChange(event.target.value)}
            placeholder={
              isVerify
                ? 'เช่น ตรวจสอบยอดและวันที่รับเงินแล้ว ถูกต้องครบถ้วน'
                : 'เช่น ภาพไม่ชัด กรุณาถ่ายใหม่ให้เห็นยอดเงินและวันที่โอน'
            }
            disabled={busy}
            autoFocus
          />
        </label>

        <footer className="payment-review-dialog-actions">
          <button type="button" className="approval-reject-secondary" onClick={onClose} disabled={busy}>
            ยกเลิก
          </button>
          <button
            type="button"
            className={`payment-review-confirm-button ${isVerify ? 'verify' : 'changes'}`}
            onClick={onConfirm}
            disabled={busy || (noteRequired && !note.trim())}
          >
            <ConfirmIcon size={16} />
            {busy
              ? 'กำลังบันทึก...'
              : isVerify
                ? 'ยืนยันว่าได้รับเงินแล้ว'
                : 'ส่งคำขอแก้ไข'}
          </button>
        </footer>
      </section>
    </div>
  );
}

function PaymentConfirmationReviewWorkspace({ onPendingCountChange }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [confirmations, setConfirmations] = useState([]);
  const [subcontractors, setSubcontractors] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [statusFilter, setStatusFilter] = useState('SUBMITTED');
  const [projectFilter, setProjectFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [pageError, setPageError] = useState('');
  const [flashMessage, setFlashMessage] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [reviewDialog, setReviewDialog] = useState(null);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewBusy, setReviewBusy] = useState(false);
  const previewRequestIdRef = useRef(0);

  const profileMap = useMemo(
    () => new Map(subcontractors.map((item) => [item.id, item])),
    [subcontractors],
  );

  const statusCounts = useMemo(
    () => confirmations.reduce(
      (counts, item) => ({
        ...counts,
        all: counts.all + 1,
        [item.status]: (counts[item.status] || 0) + 1,
      }),
      {
        all: 0,
        SUBMITTED: 0,
        VERIFIED: 0,
        CHANGES_REQUESTED: 0,
      },
    ),
    [confirmations],
  );

  const projectOptions = useMemo(() => {
    const projects = new Map();
    confirmations.forEach((item) => {
      if (item.project_id) {
        projects.set(item.project_id, item.project_name || item.project_id);
      }
    });
    return Array.from(projects, ([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label, 'th'));
  }, [confirmations]);

  const filteredConfirmations = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLowerCase();
    return confirmations.filter((item) => {
      if (statusFilter && item.status !== statusFilter) return false;
      if (projectFilter && item.project_id !== projectFilter) return false;
      if (!normalizedSearch) return true;
      const subcontractorName = getSubcontractorName(item, profileMap);
      return [
        item.internal_reference,
        item.project_name,
        item.subcontractor_id,
        subcontractorName,
        item.file_name,
      ].some((value) => String(value || '').toLowerCase().includes(normalizedSearch));
    });
  }, [confirmations, profileMap, projectFilter, searchQuery, statusFilter]);

  const selectedConfirmation = useMemo(
    () => confirmations.find((item) => item.confirmation_id === selectedId) || null,
    [confirmations, selectedId],
  );

  const selectedSubcontractorName = selectedConfirmation
    ? getSubcontractorName(selectedConfirmation, profileMap)
    : '';
  const canReview = isAdminPortalUser(getStoredAuthUser());

  const loadData = async ({ initial = false } = {}) => {
    if (initial) setLoading(true);
    else setRefreshing(true);
    setPageError('');

    try {
      const [confirmationItems, subcontractorItems] = await Promise.all([
        getAdminPaymentConfirmations(),
        getSettingSubcontractors().catch(() => []),
      ]);
      setConfirmations(confirmationItems);
      setSubcontractors(subcontractorItems);
      setSelectedId((current) => (
        confirmationItems.some((item) => item.confirmation_id === current)
          ? current
          : confirmationItems.find((item) => item.status === 'SUBMITTED')?.confirmation_id
            || confirmationItems[0]?.confirmation_id
            || ''
      ));
    } catch (error) {
      setPageError(error.message || 'โหลดรายการยืนยันการรับเงินไม่สำเร็จ');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadPreview = async (confirmation = selectedConfirmation) => {
    const requestId = previewRequestIdRef.current + 1;
    previewRequestIdRef.current = requestId;

    if (!confirmation?.confirmation_id) {
      setPreview(null);
      setPreviewError('');
      setPreviewLoading(false);
      return;
    }

    setPreviewLoading(true);
    setPreviewError('');
    try {
      const result = await getPaymentConfirmationSignedUrl(
        confirmation.confirmation_id,
        15,
      );
      if (previewRequestIdRef.current === requestId) {
        setPreview(result);
      }
    } catch (error) {
      if (previewRequestIdRef.current === requestId) {
        setPreview(null);
        setPreviewError(error.message || 'เปิดหลักฐานไม่สำเร็จ');
      }
    } finally {
      if (previewRequestIdRef.current === requestId) {
        setPreviewLoading(false);
      }
    }
  };

  useEffect(() => {
    loadData({ initial: true });
  }, []);

  useEffect(() => {
    onPendingCountChange?.(statusCounts.SUBMITTED);
  }, [onPendingCountChange, statusCounts.SUBMITTED]);

  useEffect(() => {
    if (filteredConfirmations.some((item) => item.confirmation_id === selectedId)) {
      return;
    }
    setSelectedId(filteredConfirmations[0]?.confirmation_id || '');
  }, [filteredConfirmations, selectedId]);

  useEffect(() => {
    setPreview(null);
    setPreviewError('');
    loadPreview(selectedConfirmation);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConfirmation?.confirmation_id]);

  const openReviewDialog = (action) => {
    setReviewNote('');
    setReviewDialog({ action });
    setFlashMessage('');
  };

  const closeReviewDialog = () => {
    if (reviewBusy) return;
    setReviewDialog(null);
    setReviewNote('');
  };

  const handleReview = async () => {
    if (!selectedConfirmation || !reviewDialog) return;
    if (reviewDialog.action === 'REQUEST_CHANGES' && !reviewNote.trim()) return;

    setReviewBusy(true);
    setPageError('');
    try {
      const updated = await reviewAdminPaymentConfirmation(
        selectedConfirmation.confirmation_id,
        {
          action: reviewDialog.action,
          note: reviewNote,
        },
      );
      setConfirmations((current) => (
        current.map((item) => (
          item.confirmation_id === updated.confirmation_id ? updated : item
        ))
      ));
      setFlashMessage(
        reviewDialog.action === 'VERIFY'
          ? `ยืนยันหลักฐาน ${selectedConfirmation.internal_reference} เรียบร้อยแล้ว`
          : `ส่งคำขอแก้ไข ${selectedConfirmation.internal_reference} เรียบร้อยแล้ว`,
      );
      setReviewDialog(null);
      setReviewNote('');
    } catch (error) {
      setPageError(error.message || 'บันทึกผลการตรวจสอบไม่สำเร็จ');
    } finally {
      setReviewBusy(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <section className="payment-review-workspace">
      <div className="payment-review-summary">
        <div className="payment-review-summary-copy">
          <span className="approval-kicker">
            <ShieldCheck size={15} />
            PAYMENT CONFIRMATION REVIEW
          </span>
          <h2>ตรวจสอบหลักฐานยืนยันการรับเงิน</h2>
          <p>ตรวจสอบยอด วันที่ และเอกสารจากผู้รับเงินก่อนปิดรายการ</p>
        </div>
        <div className="payment-review-stat-grid" aria-label="สรุปสถานะหลักฐาน">
          <div className="payment-review-stat warning">
            <Clock3 size={18} />
            <span>รอตรวจสอบ</span>
            <strong>{statusCounts.SUBMITTED}</strong>
          </div>
          <div className="payment-review-stat success">
            <CheckCircle2 size={18} />
            <span>ยืนยันแล้ว</span>
            <strong>{statusCounts.VERIFIED}</strong>
          </div>
          <div className="payment-review-stat danger">
            <RotateCcw size={18} />
            <span>ขอแก้ไข</span>
            <strong>{statusCounts.CHANGES_REQUESTED}</strong>
          </div>
        </div>
      </div>

      {pageError ? (
        <div className="payment-review-message error" role="alert">
          <AlertCircle size={18} />
          <span>{pageError}</span>
          <button type="button" onClick={() => loadData()}>
            ลองอีกครั้ง
          </button>
        </div>
      ) : null}

      {flashMessage ? (
        <div className="payment-review-message success" role="status">
          <CheckCircle2 size={18} />
          <span>{flashMessage}</span>
        </div>
      ) : null}

      <div className="approval-workspace-grid payment-review-grid">
        <aside className="approval-queue-panel payment-review-queue">
          <div className="approval-panel-header">
            <div>
              <span className="approval-kicker">
                <FileCheck2 size={15} />
                คิวหลักฐาน
              </span>
              <h2>{statusMeta(statusFilter).label}</h2>
            </div>
            <button
              type="button"
              className="payment-review-refresh"
              onClick={() => loadData()}
              disabled={refreshing}
              aria-label="รีเฟรชรายการหลักฐาน"
              title="รีเฟรชรายการ"
            >
              <RefreshCw size={17} className={refreshing ? 'spinning' : ''} />
            </button>
          </div>

          <div className="payment-review-status-tabs" role="tablist" aria-label="กรองสถานะ">
            {STATUS_OPTIONS.map((option) => (
              <button
                type="button"
                role="tab"
                aria-selected={statusFilter === option.value}
                className={`${option.tone}${statusFilter === option.value ? ' active' : ''}`}
                key={option.value || 'all'}
                onClick={() => setStatusFilter(option.value)}
              >
                <span>{option.shortLabel}</span>
                <strong>{option.value ? statusCounts[option.value] || 0 : statusCounts.all}</strong>
              </button>
            ))}
          </div>

          <label className="payment-review-search">
            <Search size={16} />
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="ค้นหาเลขอ้างอิง ผู้รับเงิน..."
              aria-label="ค้นหาหลักฐานยืนยันการรับเงิน"
            />
          </label>

          <select
            className="payment-review-project-filter"
            value={projectFilter}
            onChange={(event) => setProjectFilter(event.target.value)}
            aria-label="กรองตามโครงการ"
          >
            <option value="">ทุกโครงการ</option>
            {projectOptions.map((project) => (
              <option value={project.value} key={project.value}>
                {project.label}
              </option>
            ))}
          </select>

          <div className="approval-queue-list payment-review-queue-list">
            {filteredConfirmations.length ? filteredConfirmations.map((item) => {
              const status = statusMeta(item.status);
              const subcontractorName = getSubcontractorName(item, profileMap);
              return (
                <button
                  type="button"
                  className={`approval-queue-item${selectedId === item.confirmation_id ? ' active' : ''}`}
                  key={item.confirmation_id}
                  onClick={() => {
                    setSelectedId(item.confirmation_id);
                    setFlashMessage('');
                  }}
                >
                  <div className="approval-queue-topline">
                    <strong>{item.internal_reference}</strong>
                    <span className={`approval-status-badge ${status.tone}`}>
                      {status.shortLabel}
                    </span>
                  </div>
                  <span className="approval-queue-person">{subcontractorName}</span>
                  <span className="payment-review-project-name">{item.project_name}</span>
                  <div className="approval-queue-meta">
                    <span>ส่ง {formatDate(item.submitted_at, true)}</span>
                    <strong>{formatMoney(item.amount)}</strong>
                  </div>
                </button>
              );
            }) : (
              <div className="payment-review-empty">
                <FileCheck2 size={30} />
                <strong>ไม่พบหลักฐานในตัวกรองนี้</strong>
                <span>ลองเปลี่ยนสถานะ โครงการ หรือคำค้นหา</span>
              </div>
            )}
          </div>
        </aside>

        <div className="approval-review-panel payment-review-panel">
          {!selectedConfirmation ? (
            <div className="payment-review-empty detail">
              <FileCheck2 size={38} />
              <strong>เลือกรายการเพื่อเริ่มตรวจสอบ</strong>
              <span>รายละเอียดและหลักฐานจะแสดงในพื้นที่นี้</span>
            </div>
          ) : (
            <>
              <header className="payment-review-header">
                <div>
                  <div className="payment-review-header-meta">
                    <span className={`approval-status-badge ${statusMeta(selectedConfirmation.status).tone}`}>
                      {statusMeta(selectedConfirmation.status).label}
                    </span>
                    <span>เวอร์ชัน {selectedConfirmation.version}</span>
                    <span>ส่ง {formatDate(selectedConfirmation.submitted_at, true)}</span>
                  </div>
                  <h2>{selectedConfirmation.internal_reference}</h2>
                  <p>
                    {selectedConfirmation.project_name} · {selectedSubcontractorName}
                  </p>
                </div>
                <div className="payment-review-amount">
                  <span>ยอดที่โอน</span>
                  <strong>{formatMoney(selectedConfirmation.amount)}</strong>
                  <small>โอนวันที่ {formatDate(selectedConfirmation.payment_date)}</small>
                </div>
              </header>

              <div className={`payment-review-decision ${statusMeta(selectedConfirmation.status).tone}`}>
                {selectedConfirmation.status === 'SUBMITTED' ? (
                  <>
                    <Clock3 size={22} />
                    <div>
                      <strong>รอผู้ดูแลตรวจสอบหลักฐาน</strong>
                      <span>ตรวจยอดเงิน วันที่รับ และความชัดเจนของเอกสารก่อนเลือกผลตรวจ</span>
                    </div>
                  </>
                ) : selectedConfirmation.status === 'VERIFIED' ? (
                  <>
                    <ShieldCheck size={22} />
                    <div>
                      <strong>หลักฐานได้รับการยืนยันแล้ว</strong>
                      <span>
                        ตรวจเมื่อ {formatDate(selectedConfirmation.verified_at, true)}
                        {selectedConfirmation.verification_note
                          ? ` · ${selectedConfirmation.verification_note}`
                          : ''}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <RotateCcw size={22} />
                    <div>
                      <strong>ส่งกลับให้ผู้รับเงินแก้ไข</strong>
                      <span>{selectedConfirmation.verification_note || 'ไม่ได้ระบุเหตุผล'}</span>
                    </div>
                  </>
                )}
              </div>

              <div className="payment-review-content">
                <main className="payment-review-information">
                  <section className="payment-review-info-card">
                    <div className="payment-review-card-heading">
                      <div>
                        <span className="approval-kicker">
                          <UserRound size={15} />
                          ข้อมูลการรับเงิน
                        </span>
                        <h3>ตรวจสอบข้อมูลที่ผู้รับเงินยืนยัน</h3>
                      </div>
                    </div>
                    <dl className="payment-review-detail-grid">
                      <DetailItem label="ผู้รับเงิน" value={selectedSubcontractorName} />
                      <DetailItem
                        label="รหัสผู้รับเงิน"
                        value={selectedConfirmation.subcontractor_id}
                        mono
                      />
                      <DetailItem
                        label="วันที่รับเงิน"
                        value={formatDate(selectedConfirmation.received_date)}
                      />
                      <DetailItem
                        label="รับเต็มจำนวน"
                        value={selectedConfirmation.received_full_amount ? 'ใช่ — ครบเต็มจำนวน' : 'ไม่ครบจำนวน'}
                      />
                      <DetailItem
                        label="วันที่ระบบบันทึกการจ่าย"
                        value={formatDate(selectedConfirmation.payment_date)}
                      />
                      <DetailItem
                        label="ยอดตามรายการ"
                        value={formatMoney(selectedConfirmation.amount)}
                      />
                      <DetailItem
                        label="โครงการ"
                        value={selectedConfirmation.project_name}
                        wide
                      />
                      <DetailItem
                        label="หมายเหตุจากผู้รับเงิน"
                        value={selectedConfirmation.note || 'ไม่มีหมายเหตุ'}
                        wide
                      />
                    </dl>
                  </section>

                  <section className="payment-review-info-card">
                    <div className="payment-review-card-heading">
                      <div>
                        <span className="approval-kicker">
                          <CalendarDays size={15} />
                          ประวัติการตรวจ
                        </span>
                        <h3>ข้อมูลติดตามและเอกสาร</h3>
                      </div>
                    </div>
                    <dl className="payment-review-detail-grid">
                      <DetailItem
                        label="เลขอ้างอิง"
                        value={selectedConfirmation.internal_reference}
                        mono
                      />
                      <DetailItem
                        label="รหัสคำขอ"
                        value={selectedConfirmation.request_id}
                        mono
                      />
                      <DetailItem
                        label="ชื่อไฟล์"
                        value={selectedConfirmation.file_name}
                      />
                      <DetailItem
                        label="ขนาดไฟล์"
                        value={formatFileSize(selectedConfirmation.size_bytes)}
                      />
                      <DetailItem
                        label="ส่งเมื่อ"
                        value={formatDate(selectedConfirmation.submitted_at, true)}
                      />
                      <DetailItem
                        label="ตรวจเมื่อ"
                        value={formatDate(selectedConfirmation.verified_at, true)}
                      />
                      <DetailItem
                        label="หมายเหตุการตรวจ"
                        value={selectedConfirmation.verification_note || 'ยังไม่มีหมายเหตุ'}
                        wide
                      />
                    </dl>
                  </section>

                  {selectedConfirmation.status === 'SUBMITTED' ? (
                    <div className="payment-review-action-bar">
                      <div>
                        <strong>เลือกผลการตรวจสอบ</strong>
                        <span>ตรวจหลักฐานและข้อมูลด้านบนให้ครบก่อนบันทึก</span>
                      </div>
                      {canReview ? (
                        <div className="payment-review-actions">
                          <button
                            type="button"
                            className="approval-button danger"
                            onClick={() => openReviewDialog('REQUEST_CHANGES')}
                          >
                            <RotateCcw size={17} />
                            ขอให้แก้ไข
                          </button>
                          <button
                            type="button"
                            className="approval-button success"
                            onClick={() => openReviewDialog('VERIFY')}
                          >
                            <ShieldCheck size={17} />
                            ยืนยันว่าได้รับเงินแล้ว
                          </button>
                        </div>
                      ) : (
                        <span className="payment-review-readonly">
                          บัญชีนี้ดูข้อมูลได้ แต่ไม่มีสิทธิ์บันทึกผลตรวจ
                        </span>
                      )}
                    </div>
                  ) : null}
                </main>

                <EvidencePreview
                  confirmation={selectedConfirmation}
                  preview={preview}
                  loading={previewLoading}
                  error={previewError}
                  onRetry={() => loadPreview()}
                />
              </div>
            </>
          )}
        </div>
      </div>

      <ReviewDialog
        dialog={reviewDialog}
        confirmation={selectedConfirmation}
        subcontractorName={selectedSubcontractorName}
        note={reviewNote}
        onNoteChange={setReviewNote}
        onClose={closeReviewDialog}
        onConfirm={handleReview}
        busy={reviewBusy}
      />
    </section>
  );
}

export default PaymentConfirmationReviewWorkspace;
