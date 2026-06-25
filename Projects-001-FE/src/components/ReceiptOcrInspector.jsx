import React from 'react';
import { CheckCircle2, ExternalLink, FileText, ReceiptText, TriangleAlert } from 'lucide-react';

const cleanText = (value) => String(value || '').trim();

const toFiniteNumber = (value, fallback = 0) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};

const formatMoneyValue = (value) =>
  toFiniteNumber(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const getOcrLineItemsTotal = (data = {}) => {
  if (data?.line_items_total != null) return toFiniteNumber(data.line_items_total);
  if (data?.ocr_raw_json?.normalized?.line_items_total != null) {
    return toFiniteNumber(data.ocr_raw_json.normalized.line_items_total);
  }
  return Array.isArray(data?.items)
    ? data.items.reduce((total, item) => total + toFiniteNumber(item?.amount), 0)
    : 0;
};

const getLineItemCount = (data = {}) => {
  if (Array.isArray(data?.items)) return data.items.length;
  if (Array.isArray(data?.line_items)) return data.line_items.length;
  return 0;
};

const DetailRow = ({ label, value, strong = false }) => (
  <div className="receipt-inspector-detail-row">
    <span className="receipt-inspector-detail-label">{label}</span>
    <span className={strong ? 'receipt-inspector-detail-value is-strong' : 'receipt-inspector-detail-value'} title={cleanText(value)}>
      {value || '-'}
    </span>
  </div>
);

const Kpi = ({ label, value, tone = 'neutral' }) => (
  <div className={`receipt-inspector-kpi ${tone}`}>
    <span>{label}</span>
    <strong>{value}</strong>
  </div>
);

function ReceiptPreview({
  fileName,
  previewUrl,
  contentType,
  loading = false,
  error = '',
  emptyMessage = 'ยังไม่มีไฟล์ใบเสร็จ',
}) {
  const isImage = cleanText(contentType).startsWith('image/');
  const isPdf = cleanText(contentType) === 'application/pdf';

  return (
    <section className="receipt-inspector-card">
      <div className="receipt-inspector-section-head">
        <div>
          <div className="receipt-inspector-eyebrow">เอกสารต้นฉบับ</div>
          <h3 title={cleanText(fileName)}>{fileName || 'ใบเสร็จ'}</h3>
        </div>
        {previewUrl ? (
          <a
            className="receipt-inspector-open-link"
            href={previewUrl}
            target="_blank"
            rel="noreferrer"
            aria-label="เปิดเอกสาร"
          >
            <ExternalLink size={16} />
          </a>
        ) : null}
      </div>

      {loading ? (
        <div className="receipt-inspector-muted-box">กำลังโหลดลิงก์ไฟล์...</div>
      ) : null}

      {error ? (
        <div className="receipt-inspector-error-box">{error}</div>
      ) : null}

      {!previewUrl && !loading ? (
        <div className="receipt-inspector-muted-box">{emptyMessage}</div>
      ) : null}

      {previewUrl && isImage ? (
        <div className="receipt-inspector-preview-box">
          <img className="receipt-inspector-preview-media" src={previewUrl} alt={fileName || 'ตัวอย่างใบเสร็จ'} />
        </div>
      ) : null}

      {previewUrl && isPdf ? (
        <div className="receipt-inspector-preview-box">
          <iframe
            className="receipt-inspector-preview-media"
            src={previewUrl}
            title={fileName || 'ตัวอย่างใบเสร็จ PDF'}
          />
        </div>
      ) : null}

      {previewUrl && !isImage && !isPdf ? (
        <div className="receipt-inspector-muted-box">ไฟล์นี้ไม่สามารถแสดงตัวอย่างในเบราว์เซอร์ได้</div>
      ) : null}
    </section>
  );
}

function WarningPanel({ warningText }) {
  if (!warningText) return null;

  return (
    <div className="receipt-inspector-warning">
      <TriangleAlert size={18} />
      <div>
        <strong>ตรวจสอบ OCR</strong>
        <span>{warningText}</span>
      </div>
    </div>
  );
}

function LineItemsPreview({ items = [], totalAmount = 0 }) {
  const previewItems = items.slice(0, 4);
  const remainingCount = Math.max(items.length - previewItems.length, 0);

  return (
    <section className="receipt-inspector-card">
      <div className="receipt-inspector-section-head">
        <div>
          <div className="receipt-inspector-eyebrow">รายการที่อ่านได้</div>
          <h3>{items.length.toLocaleString()} รายการ</h3>
        </div>
        <div className="receipt-inspector-total-pill">{formatMoneyValue(totalAmount)}</div>
      </div>

      {previewItems.length ? (
        <div className="receipt-inspector-line-list">
          {previewItems.map((item, index) => (
            <div className="receipt-inspector-line-item" key={`${item.description || item.line_no || index}-${index}`}>
              <span>{item.description || '-'}</span>
              <strong>{formatMoneyValue(item.amount)}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div className="receipt-inspector-muted-box">OCR ไม่พบรายการย่อย</div>
      )}

      {remainingCount ? (
        <div className="receipt-inspector-more-line">
          อีก {remainingCount.toLocaleString()} รายการอยู่ในตารางฝั่งฟอร์ม
        </div>
      ) : null}
    </section>
  );
}

function ReceiptOcrInspector({
  mode = 'extract',
  extractData,
  submitResult,
  warningText = '',
  selectedFile,
  localReceiptPreviewUrl = '',
  submitReceiptPreview,
  submitReceiptPreviewLoading = false,
  submitReceiptPreviewError = '',
  formatEntryTypeLabel = (value) => value || '-',
  formatStatusLabel = (value) => value || '-',
}) {
  const isSubmitted = mode === 'submitted';
  const data = isSubmitted ? submitResult || {} : extractData || {};
  const fileName = isSubmitted
    ? data.receipt_file_name || submitReceiptPreview?.file_name || 'ใบเสร็จที่บันทึก'
    : selectedFile?.name || data.file_name || 'ใบเสร็จที่อัปโหลด';
  const previewUrl = isSubmitted ? submitReceiptPreview?.signed_url : localReceiptPreviewUrl;
  const contentType = isSubmitted
    ? submitReceiptPreview?.content_type || data.receipt_content_type
    : selectedFile?.type || data.content_type;
  const itemSource = isSubmitted ? data.line_items || [] : data.items || [];
  const itemCount = getLineItemCount(isSubmitted ? { line_items: itemSource } : data);
  const lineItemsTotal = isSubmitted
    ? itemSource.reduce((total, item) => total + toFiniteNumber(item?.amount), 0)
    : getOcrLineItemsTotal(data);
  const totalAmount = isSubmitted ? toFiniteNumber(data.amount) : toFiniteNumber(data.total_amount);
  const statusLabel = isSubmitted ? formatStatusLabel(data.status) : data.line_items_complete === false ? 'อาจไม่ครบ' : 'ครบหรือไม่พบข้อจำกัด';

  return (
    <div className="receipt-inspector">
      <section className="receipt-inspector-card receipt-inspector-hero">
        <div className="receipt-inspector-title-row">
          <div className="receipt-inspector-icon">
            {isSubmitted ? <CheckCircle2 size={20} /> : <ReceiptText size={20} />}
          </div>
          <div>
            <div className="receipt-inspector-eyebrow">{isSubmitted ? 'ส่งคำขอแล้ว' : 'ตัวอย่างข้อมูล OCR'}</div>
            <h2>{isSubmitted ? 'สรุปใบเสร็จที่บันทึก' : 'สรุปใบเสร็จที่อ่านได้'}</h2>
          </div>
        </div>

        <WarningPanel warningText={warningText} />

        <div className="receipt-inspector-kpi-grid">
          <Kpi label="ยอดชำระจริง" value={`${formatMoneyValue(totalAmount)} บาท`} tone="primary" />
          <Kpi label="VAT" value={`${formatMoneyValue(data.vat_amount)} บาท`} />
          <Kpi label="จำนวนรายการ" value={`${itemCount.toLocaleString()} รายการ`} />
          <Kpi label={isSubmitted ? 'สถานะ' : 'ความครบถ้วน'} value={statusLabel || '-'} />
        </div>
      </section>

      <ReceiptPreview
        fileName={fileName}
        previewUrl={previewUrl}
        contentType={contentType}
        loading={submitReceiptPreviewLoading}
        error={submitReceiptPreviewError}
        emptyMessage={isSubmitted ? 'คำขอนี้ไม่มีไฟล์ใบเสร็จที่เก็บไว้' : 'ยังไม่มีตัวอย่างไฟล์'}
      />

      <section className="receipt-inspector-card">
        <div className="receipt-inspector-section-head">
          <div>
            <div className="receipt-inspector-eyebrow">ข้อมูลหลัก</div>
            <h3>{data.vendor_name || 'ไม่พบชื่อผู้ขาย'}</h3>
          </div>
          <FileText size={18} />
        </div>

        <div className="receipt-inspector-detail-list">
          {isSubmitted ? (
            <>
              <DetailRow label="เลขคำขอ" value={data.request_id} />
              <DetailRow label="โครงการ" value={data.project_name} />
            </>
          ) : (
            <DetailRow label="ไฟล์" value={fileName} />
          )}
          <DetailRow label="ผู้ขาย / ร้านค้า" value={data.vendor_name} />
          <DetailRow label="เลขผู้เสียภาษีผู้ขาย" value={data.vendor_tax_id} />
          <DetailRow label="สาขาผู้ขาย" value={data.vendor_branch} />
          <DetailRow label="ที่อยู่ผู้ขาย" value={data.vendor_address} />
          <DetailRow label="เลขที่ใบเสร็จ" value={data.receipt_no} />
          <DetailRow label="วันที่เอกสาร" value={data.document_date} />
          <DetailRow label="ประเภทรายการ" value={formatEntryTypeLabel(data.entry_type || data.suggested_entry_type)} />
          <DetailRow label="ประเภทการเบิก" value={data.request_type || data.suggested_request_type} />
          <DetailRow label="รูปแบบ VAT" value={data.accounting_vat_mode || data.suggested_accounting_vat_mode} />
          <DetailRow label="ยอดก่อน VAT" value={`${formatMoneyValue(data.subtotal_amount)} บาท`} />
          <DetailRow label="รวม line items" value={`${formatMoneyValue(lineItemsTotal)} บาท`} strong />
          {!isSubmitted ? <DetailRow label="จำนวนหน้า" value={data.page_count ? data.page_count.toLocaleString() : '-'} /> : null}
        </div>
      </section>

      <LineItemsPreview items={itemSource} totalAmount={lineItemsTotal} />
    </div>
  );
}

export default ReceiptOcrInspector;
