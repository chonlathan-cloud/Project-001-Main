import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  AlertCircle,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileCheck2,
  FileText,
  Image as ImageIcon,
  LoaderCircle,
  Paperclip,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

import {
  getMyPaymentConfirmationPayments,
  getPaymentConfirmationSignedUrl,
  submitMyPaymentConfirmation,
} from '../../api';
import logoImage from '../../assets/Logo.png';

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_FILE_TYPES = new Set([
  'application/pdf',
  'image/heic',
  'image/heif',
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
]);

const STATUS_COPY = {
  AWAITING_SUBMISSION: {
    label: 'รอยืนยันการรับเงิน',
    description: 'บริษัทบันทึกการโอนเงินแล้ว กรุณาตรวจสอบและแนบหลักฐาน',
    tone: 'warning',
    Icon: Clock3,
  },
  SUBMITTED: {
    label: 'ส่งแล้ว — รอตรวจสอบ',
    description: 'ระบบได้รับหลักฐานแล้ว ผู้ดูแลกำลังตรวจสอบ',
    tone: 'info',
    Icon: FileCheck2,
  },
  CHANGES_REQUESTED: {
    label: 'กรุณาแก้ไขและส่งใหม่',
    description: 'ผู้ดูแลขอให้ส่งหลักฐานใหม่ กรุณาดูเหตุผลด้านล่าง',
    tone: 'danger',
    Icon: RotateCcw,
  },
  VERIFIED: {
    label: 'ตรวจสอบเรียบร้อย',
    description: 'ผู้ดูแลตรวจสอบหลักฐานการรับเงินเรียบร้อยแล้ว',
    tone: 'success',
    Icon: CheckCircle2,
  },
  SUPERSEDED: {
    label: 'มีหลักฐานฉบับใหม่แล้ว',
    description: 'หลักฐานฉบับนี้ถูกแทนที่ด้วยฉบับที่ส่งใหม่',
    tone: 'info',
    Icon: FileCheck2,
  },
};

function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

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

function createIdempotencyKey() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `payment-confirmation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function statusFor(payment) {
  return STATUS_COPY[payment?.confirmation_status] || STATUS_COPY.AWAITING_SUBMISSION;
}

function StatusBadge({ payment }) {
  const status = statusFor(payment);
  const Icon = status.Icon;
  return (
    <span className={`pc-status pc-status-${status.tone}`}>
      <Icon size={14} aria-hidden="true" />
      {status.label}
    </span>
  );
}

function PaymentSummary({ payment }) {
  return (
    <dl className="pc-payment-summary">
      <div className="pc-payment-amount">
        <dt>ยอดเงินที่โอน</dt>
        <dd>{formatMoney(payment.amount)}</dd>
      </div>
      <div>
        <dt>โครงการ</dt>
        <dd>{payment.project_name}</dd>
      </div>
      <div>
        <dt>วันที่โอน</dt>
        <dd>{formatDate(payment.payment_date)}</dd>
      </div>
      <div>
        <dt>เลขอ้างอิง</dt>
        <dd className="pc-reference">{payment.internal_reference}</dd>
      </div>
    </dl>
  );
}

function PaymentListCard({ payment, selected, onSelect }) {
  const status = statusFor(payment);
  return (
    <button
      type="button"
      className={`pc-payment-card${selected ? ' selected' : ''}`}
      onClick={() => onSelect(payment.payment_id)}
      aria-pressed={selected}
    >
      <span className="pc-payment-card-top">
        <span className="pc-payment-card-project">{payment.project_name}</span>
        <StatusBadge payment={payment} />
      </span>
      <strong>{formatMoney(payment.amount)}</strong>
      <span className="pc-payment-card-meta">
        โอนวันที่ {formatDate(payment.payment_date)} · {payment.internal_reference}
      </span>
      <span className="pc-payment-card-hint">{status.description}</span>
    </button>
  );
}

function FilePreview({ file, previewUrl, onRemove }) {
  const isImage = file.type.startsWith('image/');
  return (
    <article className="pc-file-preview">
      <div className="pc-file-preview-media">
        {isImage && previewUrl ? (
          <img src={previewUrl} alt={`ตัวอย่าง ${file.name}`} />
        ) : (
          <FileText size={38} aria-hidden="true" />
        )}
      </div>
      <div className="pc-file-preview-copy">
        <strong>{file.name}</strong>
        <span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
        <span>ตรวจสอบไฟล์ให้ชัดเจนก่อนส่ง</span>
        <label className="pc-replace-file" htmlFor="pc-file-input">
          <RotateCcw size={13} />
          เลือกไฟล์ใหม่
        </label>
      </div>
      <button
        type="button"
        className="pc-icon-button pc-remove-file"
        onClick={onRemove}
        aria-label="ลบไฟล์ที่เลือก"
      >
        <Trash2 size={18} />
      </button>
    </article>
  );
}

function PreviewDialog({ preview, onClose }) {
  useEffect(() => {
    if (!preview) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, preview]);

  if (!preview) return null;
  const isImage = String(preview.content_type || '').startsWith('image/');
  const isPdf = preview.content_type === 'application/pdf';

  return (
    <div className="pc-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="pc-preview-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pc-preview-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span>หลักฐานที่ส่ง</span>
            <h2 id="pc-preview-title">{preview.file_name}</h2>
          </div>
          <button
            type="button"
            className="pc-icon-button"
            onClick={onClose}
            aria-label="ปิดตัวอย่างหลักฐาน"
          >
            <X size={20} />
          </button>
        </header>

        <div className="pc-preview-dialog-body">
          {isImage ? (
            <img src={preview.url} alt={preview.file_name} />
          ) : isPdf ? (
            <iframe src={preview.url} title={preview.file_name} />
          ) : (
            <div className="pc-preview-unsupported">
              <FileText size={42} />
              <p>อุปกรณ์นี้ไม่สามารถแสดงตัวอย่างไฟล์ได้</p>
            </div>
          )}
        </div>

        <footer>
          <a href={preview.url} target="_blank" rel="noreferrer">
            เปิดเอกสาร
            <ExternalLink size={16} />
          </a>
        </footer>
      </section>
    </div>
  );
}

function SubmittedStatusPanel({ payment, onPreview, previewBusy }) {
  const status = statusFor(payment);
  const Icon = status.Icon;
  return (
    <section className="pc-detail-card pc-status-detail">
      <div className={`pc-status-illustration pc-status-${status.tone}`}>
        <Icon size={28} aria-hidden="true" />
      </div>
      <StatusBadge payment={payment} />
      <h2>{status.label}</h2>
      <p>{status.description}</p>

      <PaymentSummary payment={payment} />

      {payment.latest_file_name ? (
        <div className="pc-submitted-file">
          <div>
            <Paperclip size={18} aria-hidden="true" />
            <span>
              <strong>{payment.latest_file_name}</strong>
              <small>ส่งเมื่อ {formatDate(payment.latest_submitted_at, true)}</small>
            </span>
          </div>
          <button
            type="button"
            className="pc-secondary-button"
            onClick={() => onPreview(payment)}
            disabled={previewBusy}
          >
            {previewBusy ? <LoaderCircle className="pc-spin" size={16} /> : <ImageIcon size={16} />}
            ดูหลักฐาน
          </button>
        </div>
      ) : null}

      {payment.latest_verified_at ? (
        <div className="pc-verified-note">
          <ShieldCheck size={18} aria-hidden="true" />
          ตรวจสอบเมื่อ {formatDate(payment.latest_verified_at, true)}
        </div>
      ) : null}
    </section>
  );
}

export default function PaymentConfirmationWorkspace() {
  const cameraInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const detailRef = useRef(null);
  const [payments, setPayments] = useState([]);
  const [selectedPaymentId, setSelectedPaymentId] = useState('');
  const [file, setFile] = useState(null);
  const [receivedDate, setReceivedDate] = useState(todayIso);
  const [acknowledged, setAcknowledged] = useState(false);
  const [note, setNote] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [fileError, setFileError] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewBusyId, setPreviewBusyId] = useState('');

  const actionablePayments = useMemo(
    () => payments.filter((payment) => payment.action_required),
    [payments],
  );
  const completedPayments = useMemo(
    () => payments.filter((payment) => !payment.action_required),
    [payments],
  );
  const selectedPayment = useMemo(
    () => payments.find((payment) => payment.payment_id === selectedPaymentId) || null,
    [payments, selectedPaymentId],
  );
  const localPreviewUrl = useMemo(
    () => (file?.type?.startsWith('image/') ? URL.createObjectURL(file) : ''),
    [file],
  );

  useEffect(() => () => {
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
  }, [localPreviewUrl]);

  const resetForm = useCallback(() => {
    setFile(null);
    setFileError('');
    setReceivedDate(todayIso());
    setAcknowledged(false);
    setNote('');
    setIdempotencyKey(createIdempotencyKey());
    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const loadPayments = useCallback(async ({ quiet = false } = {}) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    try {
      const items = await getMyPaymentConfirmationPayments();
      setPayments(items);
      setSelectedPaymentId((current) => {
        if (current && items.some((item) => item.payment_id === current)) return current;
        const actions = items.filter((item) => item.action_required);
        return actions.length === 1 ? actions[0].payment_id : '';
      });
      if (!quiet) setNotice(null);
    } catch (error) {
      setNotice({
        tone: 'danger',
        message: error.message || 'ไม่สามารถโหลดรายการโอนเงินได้ กรุณาลองใหม่อีกครั้ง',
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  useEffect(() => {
    resetForm();
  }, [resetForm, selectedPaymentId]);

  const handleSelectPayment = (paymentId) => {
    setSelectedPaymentId(paymentId);
    setNotice(null);
    window.requestAnimationFrame(() => {
      detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  const handleFile = (selectedFile) => {
    setFileError('');
    setNotice(null);
    if (!selectedFile) return;
    const normalizedType = String(selectedFile.type || '').toLowerCase();
    if (!ACCEPTED_FILE_TYPES.has(normalizedType)) {
      setFile(null);
      setFileError('รองรับเฉพาะไฟล์ JPG, PNG, WEBP, HEIC, HEIF หรือ PDF');
      return;
    }
    if (selectedFile.size > MAX_FILE_BYTES) {
      setFile(null);
      setFileError('ไฟล์มีขนาดเกิน 10 MB กรุณาเลือกไฟล์ที่เล็กลง');
      return;
    }
    if (selectedFile.size <= 0) {
      setFile(null);
      setFileError('ไฟล์นี้ไม่มีข้อมูล กรุณาเลือกไฟล์ใหม่');
      return;
    }
    setFile(selectedFile);
    setIdempotencyKey(createIdempotencyKey());
  };

  const removeFile = () => {
    setFile(null);
    setFileError('');
    setIdempotencyKey(createIdempotencyKey());
    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedPayment || !selectedPayment.action_required || !file || !acknowledged) return;

    setSubmitting(true);
    setNotice(null);
    try {
      await submitMyPaymentConfirmation(selectedPayment.payment_id, {
        file,
        receivedDate,
        receivedFullAmount: true,
        note,
        idempotencyKey,
      });
      resetForm();
      await loadPayments({ quiet: true });
      setNotice({
        tone: 'success',
        message: 'ส่งหลักฐานเรียบร้อยแล้ว ระบบกำลังรอผู้ดูแลตรวจสอบ',
      });
    } catch (error) {
      if (error.status === 409) {
        await loadPayments({ quiet: true });
      }
      setNotice({
        tone: 'danger',
        message: error.message || 'ส่งหลักฐานไม่สำเร็จ กรุณาตรวจสอบแล้วลองใหม่',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handlePreview = async (payment) => {
    if (!payment.latest_confirmation_id) return;
    setPreviewBusyId(payment.payment_id);
    setNotice(null);
    try {
      const data = await getPaymentConfirmationSignedUrl(payment.latest_confirmation_id);
      setPreview(data);
    } catch (error) {
      setNotice({
        tone: 'danger',
        message: error.message || 'ไม่สามารถเปิดหลักฐานได้ กรุณาลองใหม่อีกครั้ง',
      });
    } finally {
      setPreviewBusyId('');
    }
  };

  return (
    <main className="pc-page">
      <div className="pc-shell">
        <header className="pc-page-header">
          <div className="pc-brand">
            <img src={logoImage} alt="" />
            <span>
              <small>RAYADEE</small>
              <strong>ยืนยันการรับเงิน</strong>
            </span>
          </div>
          <button
            type="button"
            className="pc-icon-button"
            onClick={() => loadPayments({ quiet: true })}
            disabled={refreshing}
            aria-label="โหลดรายการใหม่"
          >
            <RefreshCw className={refreshing ? 'pc-spin' : ''} size={20} />
          </button>
        </header>

        <section className="pc-intro">
          <span className="pc-eyebrow">
            <ReceiptText size={15} aria-hidden="true" />
            หลักฐานการรับเงิน
          </span>
          <h1>ตรวจสอบยอด แล้วส่งหลักฐานได้ในไม่กี่ขั้นตอน</h1>
          <p>ข้อมูลทุกไฟล์เป็นส่วนตัวและใช้สำหรับตรวจสอบการชำระเงินเท่านั้น</p>
        </section>

        {notice ? (
          <div className={`pc-notice pc-notice-${notice.tone}`} role="status" aria-live="polite">
            {notice.tone === 'success'
              ? <CheckCircle2 size={19} />
              : <AlertCircle size={19} />}
            <span>{notice.message}</span>
          </div>
        ) : null}

        {loading ? (
          <div className="pc-loading-card" role="status">
            <LoaderCircle className="pc-spin" size={26} />
            <strong>กำลังโหลดรายการโอนเงิน</strong>
            <span>กรุณารอสักครู่</span>
          </div>
        ) : null}

        {!loading && payments.length === 0 ? (
          <section className="pc-empty-card">
            <div><Check size={28} /></div>
            <h2>ยังไม่มีรายการที่ต้องยืนยัน</h2>
            <p>เมื่อบริษัทบันทึกการโอนเงินแล้ว รายการจะปรากฏที่หน้านี้โดยอัตโนมัติ</p>
            <button
              type="button"
              className="pc-secondary-button"
              onClick={() => loadPayments({ quiet: true })}
              disabled={refreshing}
            >
              <RefreshCw className={refreshing ? 'pc-spin' : ''} size={16} />
              ตรวจสอบอีกครั้ง
            </button>
          </section>
        ) : null}

        {!loading && actionablePayments.length > 0 ? (
          <section className="pc-section" aria-labelledby="pc-action-title">
            <div className="pc-section-heading">
              <div>
                <span>ต้องดำเนินการ</span>
                <h2 id="pc-action-title">รายการรอยืนยัน</h2>
              </div>
              <strong>{actionablePayments.length}</strong>
            </div>
            <div className="pc-payment-list">
              {actionablePayments.map((payment) => (
                <PaymentListCard
                  key={payment.payment_id}
                  payment={payment}
                  selected={payment.payment_id === selectedPaymentId}
                  onSelect={handleSelectPayment}
                />
              ))}
            </div>
          </section>
        ) : null}

        {selectedPayment ? (
          <div ref={detailRef} className="pc-detail-anchor">
            {selectedPayment.action_required ? (
              <form className="pc-detail-card" onSubmit={handleSubmit}>
                <header className="pc-detail-heading">
                  <div>
                    <span>รายการที่เลือก</span>
                    <h2>ยืนยันว่าได้รับเงินแล้ว</h2>
                  </div>
                  <StatusBadge payment={selectedPayment} />
                </header>

                {selectedPayment.confirmation_status === 'CHANGES_REQUESTED' ? (
                  <div className="pc-change-request">
                    <AlertCircle size={20} aria-hidden="true" />
                    <div>
                      <strong>เหตุผลที่ขอให้ส่งใหม่</strong>
                      <p>
                        {selectedPayment.latest_verification_note
                          || 'กรุณาตรวจสอบความชัดเจนของหลักฐานแล้วส่งใหม่อีกครั้ง'}
                      </p>
                      {selectedPayment.latest_confirmation_id ? (
                        <button
                          type="button"
                          onClick={() => handlePreview(selectedPayment)}
                          disabled={previewBusyId === selectedPayment.payment_id}
                        >
                          {previewBusyId === selectedPayment.payment_id
                            ? <LoaderCircle className="pc-spin" size={14} />
                            : <ImageIcon size={14} />}
                          ดูหลักฐานเดิม
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                <PaymentSummary payment={selectedPayment} />

                <section className="pc-form-section">
                  <div className="pc-form-heading">
                    <span>1</span>
                    <div>
                      <h3>แนบหลักฐาน</h3>
                      <p>ถ่ายรูปใหม่ หรือเลือกภาพ/PDF ที่มีอยู่แล้ว</p>
                    </div>
                  </div>

                  <input
                    ref={cameraInputRef}
                    id="pc-camera-input"
                    className="pc-visually-hidden"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
                    capture="environment"
                    onChange={(event) => {
                      handleFile(event.target.files?.[0]);
                      event.target.value = '';
                    }}
                  />
                  <input
                    ref={fileInputRef}
                    id="pc-file-input"
                    className="pc-visually-hidden"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf"
                    onChange={(event) => {
                      handleFile(event.target.files?.[0]);
                      event.target.value = '';
                    }}
                  />

                  {!file ? (
                    <div className={`pc-upload-box${fileError ? ' has-error' : ''}`}>
                      <div className="pc-upload-icon"><Upload size={26} /></div>
                      <strong>เลือกวิธีแนบหลักฐาน</strong>
                      <span>ไฟล์ต้องชัดเจน และมีขนาดไม่เกิน 10 MB</span>
                      <div className="pc-upload-actions">
                        <label className="pc-primary-button" htmlFor="pc-camera-input">
                          <Camera size={18} />
                          ถ่ายรูป
                        </label>
                        <label className="pc-secondary-button" htmlFor="pc-file-input">
                          <Paperclip size={18} />
                          เลือกไฟล์
                        </label>
                      </div>
                    </div>
                  ) : (
                    <FilePreview file={file} previewUrl={localPreviewUrl} onRemove={removeFile} />
                  )}
                  {fileError ? <p className="pc-field-error">{fileError}</p> : null}
                </section>

                <section className="pc-form-section">
                  <div className="pc-form-heading">
                    <span>2</span>
                    <div>
                      <h3>ตรวจสอบการรับเงิน</h3>
                      <p>ยืนยันวันที่และยอดเงินก่อนส่ง</p>
                    </div>
                  </div>

                  <label className="pc-field">
                    <span>วันที่ได้รับเงิน</span>
                    <input
                      type="date"
                      value={receivedDate}
                      max={todayIso()}
                      onChange={(event) => setReceivedDate(event.target.value)}
                      required
                    />
                  </label>

                  <label className="pc-acknowledgement">
                    <input
                      type="checkbox"
                      checked={acknowledged}
                      onChange={(event) => setAcknowledged(event.target.checked)}
                    />
                    <span className="pc-checkbox" aria-hidden="true">
                      {acknowledged ? <Check size={16} /> : null}
                    </span>
                    <span>
                      ฉันได้รับเงินจำนวน
                      <strong>{formatMoney(selectedPayment.amount)}</strong>
                      ครบถ้วนแล้ว
                    </span>
                  </label>

                  <details className="pc-optional-note">
                    <summary>เพิ่มรายละเอียด (ไม่บังคับ)</summary>
                    <label className="pc-field">
                      <span>หมายเหตุถึงผู้ตรวจสอบ</span>
                      <textarea
                        rows="3"
                        value={note}
                        maxLength={500}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder="เช่น ได้รับเงินเข้าบัญชีเรียบร้อยแล้ว"
                      />
                    </label>
                  </details>
                </section>

                <div className="pc-submit-area">
                  <p>
                    <ShieldCheck size={16} />
                    หลักฐานจะถูกเก็บอย่างปลอดภัยและเปิดดูได้เฉพาะผู้เกี่ยวข้อง
                  </p>
                  <button
                    type="submit"
                    className="pc-submit-button"
                    disabled={!file || !receivedDate || !acknowledged || submitting}
                  >
                    {submitting ? (
                      <>
                        <LoaderCircle className="pc-spin" size={19} />
                        กำลังส่งหลักฐาน...
                      </>
                    ) : (
                      <>
                        <Send size={19} />
                        ยืนยันว่าได้รับเงินแล้ว
                      </>
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <SubmittedStatusPanel
                payment={selectedPayment}
                onPreview={handlePreview}
                previewBusy={previewBusyId === selectedPayment.payment_id}
              />
            )}
          </div>
        ) : null}

        {!loading && actionablePayments.length > 1 && !selectedPayment ? (
          <div className="pc-selection-hint">
            <ReceiptText size={21} />
            เลือกรายการด้านบนเพื่อยืนยันการรับเงิน
          </div>
        ) : null}

        {!loading && completedPayments.length > 0 ? (
          <section className="pc-section pc-history" aria-labelledby="pc-history-title">
            <div className="pc-section-heading">
              <div>
                <span>ประวัติ</span>
                <h2 id="pc-history-title">รายการที่ส่งแล้ว</h2>
              </div>
            </div>
            <div className="pc-payment-list">
              {completedPayments.map((payment) => (
                <PaymentListCard
                  key={payment.payment_id}
                  payment={payment}
                  selected={payment.payment_id === selectedPaymentId}
                  onSelect={handleSelectPayment}
                />
              ))}
            </div>
          </section>
        ) : null}

        <footer className="pc-page-footer">
          <ShieldCheck size={16} />
          RAYADEE · ระบบยืนยันการรับเงินที่ปลอดภัย
        </footer>
      </div>

      <PreviewDialog preview={preview} onClose={() => setPreview(null)} />
    </main>
  );
}
