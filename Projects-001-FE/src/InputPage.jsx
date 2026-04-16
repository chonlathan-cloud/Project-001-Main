import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, CheckCircle2, ExternalLink, LoaderCircle, ReceiptText, TriangleAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Loading from './components/Loading';
import ConstructionAnimation from './components/ConstructionAnimation';
import {
  extractInputReceipt,
  getInputRequestReceiptUrl,
  getInputProjectOptions,
  submitInputRequest,
  uploadInputReceipt,
} from './api';

const ENTRY_TYPE_OPTIONS = [
  { value: 'EXPENSE', label: 'รายจ่าย' },
  { value: 'INCOME', label: 'รายรับ' },
];

const WORK_TYPE_OPTIONS = [
  { value: 'งานโครงสร้าง', label: 'งานโครงสร้าง' },
  { value: 'งานสถาปัตย์', label: 'งานสถาปัตย์' },
  { value: 'งานระบบ', label: 'งานระบบ' },
  { value: 'งานบริหารโครงการ', label: 'งานบริหารโครงการ' },
];

const REQUEST_TYPE_OPTIONS = [
  { value: 'ค่าวัสดุ', label: 'ค่าวัสดุ' },
  { value: 'ค่าแรง', label: 'ค่าแรง' },
  { value: 'ค่าเบิกล่วงหน้า', label: 'ค่าเบิกล่วงหน้า' },
  { value: 'ค่าใช้จ่ายทั่วไป', label: 'ค่าใช้จ่ายทั่วไป' },
];

const WORK_TYPE_ALIAS_MAP = {
  งานบริหาร: 'งานบริหารโครงการ',
};

const REQUEST_TYPE_ALIAS_MAP = {
  วัสดุ: 'ค่าวัสดุ',
  ค่าใช้จ่าย: 'ค่าใช้จ่ายทั่วไป',
  ทั่วไป: 'ค่าใช้จ่ายทั่วไป',
  แรงงาน: 'ค่าแรง',
  เบิกล่วงหน้า: 'ค่าเบิกล่วงหน้า',
};

const normalizeEntryType = (value) => {
  const normalized = String(value || '')
    .trim()
    .toUpperCase();
  return ENTRY_TYPE_OPTIONS.some((option) => option.value === normalized) ? normalized : '';
};

const normalizeWorkType = (value) => {
  const cleaned = String(value || '').trim();
  const normalized = WORK_TYPE_ALIAS_MAP[cleaned] || cleaned;
  return WORK_TYPE_OPTIONS.some((option) => option.value === normalized) ? normalized : '';
};

const normalizeRequestType = (value) => {
  const cleaned = String(value || '').trim();
  const normalized = REQUEST_TYPE_ALIAS_MAP[cleaned] || cleaned;
  return REQUEST_TYPE_OPTIONS.some((option) => option.value === normalized) ? normalized : '';
};

const normalizeDateInputValue = (value) => {
  const cleaned = String(value || '').trim();
  if (!cleaned) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) return cleaned;

  const match = cleaned.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
  if (match) {
    const [, day, month, year] = match;
    return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  const parsed = new Date(cleaned);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toISOString().slice(0, 10);
};

const initialFormState = {
  entryType: 'EXPENSE',
  projectId: '',
  requesterName: '',
  phone: '',
  requestDate: new Date().toISOString().slice(0, 10),
  documentDate: '',
  workType: '',
  requestType: '',
  note: '',
  vendorName: '',
  receiptNo: '',
  bankName: '',
  accountNo: '',
  accountName: '',
  amount: '',
};

const fieldBaseStyle = {
  width: '100%',
  padding: '12px 16px',
  borderRadius: '12px',
  backgroundColor: '#e6decb',
  border: '1px solid #bba684',
  fontSize: '14px',
  outline: 'none',
  color: '#333',
  transition: 'all 0.3s ease',
};

const InputField = ({
  label,
  placeholder,
  type = 'text',
  style = {},
  value,
  onChange,
  disabled = false,
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>{label}</label>}
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      style={{
        ...fieldBaseStyle,
        textAlign: type === 'date' ? 'left' : 'center',
        opacity: disabled ? 0.65 : 1,
      }}
    />
  </div>
);

const SelectField = ({
  label,
  placeholder,
  options = [],
  style = {},
  value,
  onChange,
  disabled = false,
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>{label}</label>}
    <div style={{ position: 'relative' }}>
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        style={{
          ...fieldBaseStyle,
          textAlign: 'center',
          appearance: 'none',
          color: value ? '#333' : '#666',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.65 : 1,
        }}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  </div>
);

const TextAreaField = ({ label, placeholder, style = {}, value, onChange }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>{label}</label>}
    <textarea
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows={4}
      style={{
        ...fieldBaseStyle,
        resize: 'vertical',
        textAlign: 'left',
        minHeight: '104px',
      }}
    />
  </div>
);

const StatusBanner = ({ tone, text }) => {
  const palette =
    tone === 'error'
      ? { bg: '#fde8e8', border: '#de5b52', color: '#912018', Icon: TriangleAlert }
      : tone === 'warning'
        ? { bg: '#fff4de', border: '#c98c1c', color: '#8b5a00', Icon: TriangleAlert }
      : { bg: '#e6f5ec', border: '#27a57a', color: '#13654b', Icon: CheckCircle2 };
  const Icon = palette.Icon;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 14px',
        borderRadius: '14px',
        backgroundColor: palette.bg,
        border: `1px solid ${palette.border}`,
        color: palette.color,
        fontSize: '14px',
        fontWeight: '600',
      }}
    >
      <Icon size={18} />
      <span>{text}</span>
    </div>
  );
};

const formatEntryTypeLabel = (entryType) =>
  ENTRY_TYPE_OPTIONS.find((option) => option.value === entryType)?.label || '-';

const formatOcrFieldLabel = (fieldName) => {
  const labels = {
    suggested_entry_type: 'ประเภทรายการ',
    vendor_name: 'ผู้ขาย / ร้านค้า',
    receipt_no: 'เลขที่ใบเสร็จ',
    document_date: 'วันที่เอกสาร',
    suggested_request_type: 'ประเภทการเบิก',
    total_amount: 'ยอดรวม',
    items: 'รายการสินค้า/บริการ',
  };
  return labels[fieldName] || fieldName;
};

const InputPage = () => {
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState(initialFormState);
  const [selectedFile, setSelectedFile] = useState(null);
  const [localReceiptPreviewUrl, setLocalReceiptPreviewUrl] = useState('');
  const [extractData, setExtractData] = useState(null);
  const [uploadedReceipt, setUploadedReceipt] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitReceiptPreview, setSubmitReceiptPreview] = useState(null);
  const [submitReceiptPreviewLoading, setSubmitReceiptPreviewLoading] = useState(false);
  const [submitReceiptPreviewError, setSubmitReceiptPreviewError] = useState('');
  const [pageError, setPageError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [flashMessage, setFlashMessage] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        setLoading(true);
        setPageError('');
        const items = await getInputProjectOptions();
        setProjects(items);
      } catch (error) {
        setPageError(error.message || 'Failed to load projects for the input form.');
      } finally {
        setLoading(false);
      }
    };

    loadProjects();
  }, []);

  useEffect(() => {
    let isActive = true;

    const loadSubmitReceiptPreview = async () => {
      if (!submitResult?.request_id || !submitResult?.receipt_storage_key) {
        if (isActive) {
          setSubmitReceiptPreview(null);
          setSubmitReceiptPreviewError('');
          setSubmitReceiptPreviewLoading(false);
        }
        return;
      }

      try {
        if (isActive) {
          setSubmitReceiptPreviewLoading(true);
          setSubmitReceiptPreviewError('');
        }
        const response = await getInputRequestReceiptUrl(submitResult.request_id, {
          cacheToken: submitResult.receipt_storage_key || '',
        });
        if (!isActive) return;
        setSubmitReceiptPreview(response);
      } catch (error) {
        if (!isActive) return;
        setSubmitReceiptPreview(null);
        setSubmitReceiptPreviewError(error.message || 'Failed to load receipt preview.');
      } finally {
        if (isActive) {
          setSubmitReceiptPreviewLoading(false);
        }
      }
    };

    loadSubmitReceiptPreview();

    return () => {
      isActive = false;
    };
  }, [submitResult?.request_id, submitResult?.receipt_storage_key]);

  useEffect(() => {
    if (!selectedFile) {
      setLocalReceiptPreviewUrl('');
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setLocalReceiptPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedFile]);

  const handleFieldChange = (field) => (event) => {
    const nextValue = event.target.value;
    setForm((current) => ({ ...current, [field]: nextValue }));
  };

  const handleEntryTypeChange = (event) => {
    const nextType = event.target.value;
    setForm((current) => ({
      ...current,
      entryType: nextType,
      requestType:
        nextType === 'INCOME' && current.requestType === 'ค่าเบิกล่วงหน้า'
          ? ''
          : current.requestType,
    }));
    setSubmitError('');
    setSubmitResult(null);
  };

  const handlePickFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setSelectedFile(file);
    setExtractData(null);
    setUploadedReceipt(null);
    setSubmitError('');
    setFlashMessage('');

    try {
      setIsExtracting(true);
      const extracted = await extractInputReceipt(file);
      const normalizedExtracted = {
        ...extracted,
        suggested_entry_type:
          normalizeEntryType(extracted.suggested_entry_type) || initialFormState.entryType,
        suggested_request_type: normalizeRequestType(extracted.suggested_request_type),
      };

      setExtractData(normalizedExtracted);
      setForm((current) => ({
        ...current,
        amount: current.amount
          ? current.amount
          : normalizedExtracted.total_amount == null
            ? ''
            : String(normalizedExtracted.total_amount),
        documentDate: current.documentDate || normalizeDateInputValue(normalizedExtracted.document_date),
        requestType: current.requestType || normalizedExtracted.suggested_request_type || '',
        vendorName: current.vendorName || normalizedExtracted.vendor_name || '',
        receiptNo: current.receiptNo || normalizedExtracted.receipt_no || '',
        note:
          current.note ||
          [
            normalizedExtracted.vendor_name,
            normalizedExtracted.receipt_no,
            normalizedExtracted.document_date,
          ]
            .filter(Boolean)
            .join(' | '),
      }));
      setFlashMessage(`อ่านข้อมูลจาก ${file.name} สำเร็จแล้ว`);
    } catch (error) {
      setSubmitError(error.message || 'Failed to extract receipt data.');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    setSubmitResult(null);
    setSubmitReceiptPreview(null);
    setSubmitReceiptPreviewError('');
    setFlashMessage('');

    if (!form.projectId) {
      setSubmitError('กรุณาเลือกโครงการก่อนส่งคำขอ');
      return;
    }
    if (!selectedFile && !uploadedReceipt) {
      setSubmitError('กรุณาอัปโหลดรูปหรือ PDF ของบิล/ใบเสร็จก่อนส่งคำขอ');
      return;
    }
    if (!form.requesterName.trim()) {
      setSubmitError('กรุณากรอกชื่อ - นามสกุล');
      return;
    }
    if (!form.requestDate) {
      setSubmitError('กรุณาระบุวันที่');
      return;
    }
    if (!form.amount || Number(form.amount) <= 0) {
      setSubmitError('กรุณากรอกจำนวนเงินที่มากกว่า 0');
      return;
    }

    const normalizedWorkType = normalizeWorkType(form.workType);
    const normalizedRequestType = normalizeRequestType(form.requestType);
    const normalizedDocumentDate = form.documentDate || form.requestDate;
    const numericAmount = Number(form.amount);

    if (form.workType && !normalizedWorkType) {
      setSubmitError('ประเภทงานไม่ถูกต้อง กรุณาเลือกใหม่');
      return;
    }
    if (form.requestType && !normalizedRequestType) {
      setSubmitError('ประเภทการเบิกไม่ถูกต้อง กรุณาเลือกใหม่');
      return;
    }
    if (normalizedRequestType === 'ค่าเบิกล่วงหน้า' && form.entryType !== 'EXPENSE') {
      setSubmitError('ค่าเบิกล่วงหน้า ใช้ได้เฉพาะรายการรายจ่าย');
      return;
    }
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setSubmitError('จำนวนเงินไม่ถูกต้อง');
      return;
    }

    try {
      setIsSubmitting(true);
      let uploadedReceiptPayload = uploadedReceipt;

      if (selectedFile && !uploadedReceiptPayload) {
        uploadedReceiptPayload = await uploadInputReceipt(selectedFile);
        setUploadedReceipt(uploadedReceiptPayload);
      }

      const response = await submitInputRequest({
        project_id: form.projectId,
        entry_type: form.entryType,
        requester_name: form.requesterName.trim(),
        phone: form.phone.trim() || null,
        request_date: form.requestDate,
        document_date: normalizedDocumentDate,
        work_type: normalizedWorkType || null,
        request_type: normalizedRequestType || null,
        note: form.note.trim() || null,
        vendor_name: form.vendorName.trim() || null,
        receipt_no: form.receiptNo.trim() || null,
        bank_account: {
          bank_name: form.bankName.trim() || null,
          account_no: form.accountNo.trim() || null,
          account_name: form.accountName.trim() || form.requesterName.trim(),
        },
        amount: numericAmount,
        receipt_file_name:
          uploadedReceiptPayload?.file_name || selectedFile?.name || extractData?.file_name || null,
        receipt_content_type:
          uploadedReceiptPayload?.content_type || selectedFile?.type || extractData?.content_type || null,
        receipt_storage_key: uploadedReceiptPayload?.storage_key || null,
        ocr_raw_json: extractData?.ocr_raw_json || null,
        ocr_low_confidence_fields: extractData?.low_confidence_fields || [],
      });

      setSubmitResult(response);
      setFlashMessage('ส่งคำขอเรียบร้อยแล้ว');
      setForm({
        ...initialFormState,
        entryType: form.entryType,
      });
      setSelectedFile(null);
      setExtractData(null);
      setUploadedReceipt(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      setSubmitError(error.message || 'Failed to submit input request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <Loading />;

  if (pageError) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {pageError}
      </div>
    );
  }

  const isIncome = form.entryType === 'INCOME';
  const canPreviewLocalReceipt = Boolean(localReceiptPreviewUrl && selectedFile);
  const isLocalReceiptImage = (selectedFile?.type || '').startsWith('image/');
  const isLocalReceiptPdf = (selectedFile?.type || '') === 'application/pdf';
  const canPreviewSubmittedReceipt = Boolean(submitReceiptPreview?.signed_url);
  const isSubmittedReceiptImage = (submitReceiptPreview?.content_type || '').startsWith('image/');
  const isSubmittedReceiptPdf = (submitReceiptPreview?.content_type || '') === 'application/pdf';
  const projectOptions = projects.map((project) => ({
    value: project.project_id,
    label: project.name,
  }));

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '32px', fontWeight: '700', color: '#1a1a1a' }}>
        Input
      </h1>

      <motion.div
        layout
        style={{
          display: 'flex',
          flexDirection: isIncome ? 'row-reverse' : 'row',
          gap: '32px',
          alignItems: 'start',
        }}
      >
        <motion.div layout style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <form onSubmit={handleSubmit}>
            <div
              className="card"
              style={{
                backgroundColor: 'white',
                padding: '32px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '20px',
                borderRadius: '24px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.05)',
              }}
            >
              <AnimatePresence mode="popLayout">
                {flashMessage ? (
                  <motion.div
                    key="flash-message"
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                  >
                    <StatusBanner tone="success" text={flashMessage} />
                  </motion.div>
                ) : null}
              </AnimatePresence>

              {submitError ? <StatusBanner tone="error" text={submitError} /> : null}

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  padding: '18px',
                  borderRadius: '18px',
                  backgroundColor: '#f8f1e3',
                  border: '1px solid #d6c29f',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#1a1a1a' }}>
                    1. Upload Receipt File
                  </div>
                  <div style={{ fontSize: '13px', color: '#6b6256', lineHeight: 1.5 }}>
                    อัปโหลดรูปหรือ PDF ของบิล/ใบเสร็จก่อน เพื่อให้ระบบอ่านข้อมูลและช่วยกรอกฟอร์มให้
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,application/pdf"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <button
                  type="button"
                  onClick={handlePickFile}
                  style={{
                    width: '100%',
                    height: '140px',
                    backgroundColor: '#e6decb',
                    border: '1px solid #bba684',
                    borderRadius: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    cursor: 'pointer',
                    color: '#1a1a1a',
                  }}
                >
                  {isExtracting ? (
                    <>
                      <LoaderCircle size={18} className="spin" />
                      <span style={{ fontSize: '14px', fontWeight: '600' }}>กำลังอ่านข้อมูลจากบิล...</span>
                    </>
                  ) : (
                    <>
                      <span style={{ fontSize: '14px', fontWeight: '600' }}>
                        {selectedFile ? selectedFile.name : 'Upload Receipt Image / PDF'}
                      </span>
                      <ArrowUp size={16} />
                    </>
                  )}
                </button>
              </div>

              <SelectField
                label="รายจ่าย / รายรับ"
                placeholder="เลือกรายการที่ทำ"
                options={ENTRY_TYPE_OPTIONS}
                value={form.entryType}
                onChange={handleEntryTypeChange}
                style={{ width: '60%' }}
              />

              <SelectField
                label="โครงการ"
                placeholder="กรุณาเลือกโครงการ"
                options={projectOptions}
                value={form.projectId}
                onChange={handleFieldChange('projectId')}
                style={{ width: '60%' }}
              />

              <InputField
                label="ชื่อ - นามสกุล"
                placeholder="กรุณากรอกชื่อ-นามสกุล"
                value={form.requesterName}
                onChange={handleFieldChange('requesterName')}
                style={{ width: '60%' }}
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="เบอร์ติดต่อ"
                  placeholder="กรุณากรอกเบอร์โทรศัพท์"
                  value={form.phone}
                  onChange={handleFieldChange('phone')}
                />
                <InputField
                  label="วัน/เดือน/ปี"
                  type="date"
                  value={form.requestDate}
                  onChange={handleFieldChange('requestDate')}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="เลขที่ใบเสร็จ"
                  placeholder="กรุณากรอกเลขที่ใบเสร็จ"
                  value={form.receiptNo}
                  onChange={handleFieldChange('receiptNo')}
                />
                <InputField
                  label="วันที่เอกสาร"
                  type="date"
                  value={form.documentDate}
                  onChange={handleFieldChange('documentDate')}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <SelectField
                  label="ประเภทงาน"
                  placeholder="กรุณาเลือก"
                  options={WORK_TYPE_OPTIONS}
                  value={form.workType}
                  onChange={handleFieldChange('workType')}
                />
                <SelectField
                  label="ประเภทการเบิก"
                  placeholder="กรุณาเลือก"
                  options={REQUEST_TYPE_OPTIONS}
                  value={form.requestType}
                  onChange={handleFieldChange('requestType')}
                />
              </div>

              <InputField
                label="ผู้ขาย / ร้านค้า"
                placeholder="กรุณากรอกชื่อร้านหรือผู้ขาย"
                value={form.vendorName}
                onChange={handleFieldChange('vendorName')}
                style={{ width: '60%' }}
              />

              <TextAreaField
                label="อื่น ๆ"
                placeholder="ถ้ามี กรุณากรอกรายละเอียด"
                value={form.note}
                onChange={handleFieldChange('note')}
                style={{ width: '100%' }}
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="ธนาคาร"
                  placeholder="กรุณากรอก"
                  value={form.bankName}
                  onChange={handleFieldChange('bankName')}
                />
                <InputField
                  label="จำนวนเงินที่ขอเบิก"
                  placeholder="กรุณากรอก"
                  type="number"
                  value={form.amount}
                  onChange={handleFieldChange('amount')}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="เลขที่บัญชี"
                  placeholder="กรุณากรอก"
                  value={form.accountNo}
                  onChange={handleFieldChange('accountNo')}
                />
                <InputField
                  label="ชื่อบัญชี"
                  placeholder="กรุณากรอก"
                  value={form.accountName}
                  onChange={handleFieldChange('accountName')}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '4px' }}>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    backgroundColor: '#c9a15c',
                    color: 'black',
                    border: 'none',
                    borderRadius: '12px',
                    padding: '12px 48px',
                    fontSize: '20px',
                    fontWeight: '700',
                    cursor: isSubmitting ? 'wait' : 'pointer',
                    width: '160px',
                    boxShadow: '0 4px 15px rgba(201, 161, 92, 0.3)',
                    opacity: isSubmitting ? 0.75 : 1,
                  }}
                >
                  {isSubmitting ? 'กำลังส่ง...' : 'ส่ง'}
                </button>
              </div>
            </div>
          </form>
        </motion.div>

        <motion.div
          layout
          style={{
            flex: 1,
            backgroundColor: '#f9f6f0',
            minHeight: '800px',
            borderRadius: '24px',
            display: 'flex',
            alignItems: 'stretch',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden',
            border: '1px solid #ede4d3',
          }}
        >
          <div style={{ width: '100%', padding: '28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <AnimatePresence mode="wait">
              {submitResult ? (
                <motion.div
                  key="submit-result"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}
                >
                  <StatusBanner
                    tone="success"
                    text={`สร้างคำขอสำเร็จ สถานะ ${submitResult.status || 'PENDING_ADMIN'}`}
                  />
                  {submitResult.is_duplicate_flag ? (
                    <StatusBanner
                      tone="warning"
                      text={submitResult.duplicate_reason || 'พบรายการซ้ำตามกฎ Receipt No. + Date + Amount'}
                    />
                  ) : null}
                  {submitResult.ocr_low_confidence_fields?.length ? (
                    <StatusBanner
                      tone="warning"
                      text={`OCR ยังไม่มั่นใจในบางช่อง: ${submitResult.ocr_low_confidence_fields.map(formatOcrFieldLabel).join(', ')}`}
                    />
                  ) : null}
                  <div className="card" style={{ backgroundColor: 'white', borderRadius: '20px', padding: '24px' }}>
                    <h2 style={{ fontSize: '22px', marginBottom: '16px' }}>Submission Summary</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                      <div><strong>Request ID:</strong> {submitResult.request_id}</div>
                      <div><strong>Project:</strong> {submitResult.project_name}</div>
                      <div><strong>Type:</strong> {formatEntryTypeLabel(submitResult.entry_type)}</div>
                      <div><strong>Requester:</strong> {submitResult.requester_name}</div>
                      <div><strong>Vendor:</strong> {submitResult.vendor_name || '-'}</div>
                      <div><strong>Receipt No:</strong> {submitResult.receipt_no || '-'}</div>
                      <div><strong>Document Date:</strong> {submitResult.document_date || '-'}</div>
                      <div><strong>Amount:</strong> {Number(submitResult.amount || 0).toLocaleString()} THB</div>
                      <div><strong>Status:</strong> {submitResult.status}</div>
                    </div>
                  </div>
                  <div className="card" style={{ backgroundColor: 'white', borderRadius: '20px', padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
                      <div>
                        <h2 style={{ fontSize: '22px', margin: 0 }}>Receipt Preview</h2>
                        <div style={{ color: '#666', marginTop: '6px', fontSize: '13px' }}>
                          {submitResult.receipt_file_name || 'ไม่มีไฟล์แนบ'}
                        </div>
                      </div>
                      {canPreviewSubmittedReceipt ? (
                        <a
                          href={submitReceiptPreview.signed_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '8px',
                            textDecoration: 'none',
                            color: '#1a1a1a',
                            backgroundColor: '#f3eadb',
                            border: '1px solid #d8cfbf',
                            borderRadius: '12px',
                            padding: '10px 12px',
                            fontSize: '13px',
                            fontWeight: '600',
                          }}
                        >
                          <ExternalLink size={16} />
                          <span>Open Receipt</span>
                        </a>
                      ) : null}
                    </div>

                    {submitReceiptPreviewLoading ? (
                      <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                        กำลังโหลดลิงก์ไฟล์จาก GCS...
                      </div>
                    ) : null}

                    {submitReceiptPreviewError ? (
                      <div style={{ color: '#912018', backgroundColor: '#fde8e8', border: '1px solid #de5b52', borderRadius: '12px', padding: '12px 14px' }}>
                        {submitReceiptPreviewError}
                      </div>
                    ) : null}

                    {!submitResult.receipt_storage_key && !submitReceiptPreviewLoading ? (
                      <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                        คำขอนี้ไม่มีไฟล์ receipt ที่เก็บไว้
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && isSubmittedReceiptImage ? (
                      <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                        <img
                          src={submitReceiptPreview.signed_url}
                          alt={submitReceiptPreview.file_name || 'Receipt preview'}
                          style={{
                            width: '100%',
                            maxHeight: '360px',
                            objectFit: 'contain',
                            borderRadius: '12px',
                            display: 'block',
                            backgroundColor: 'white',
                          }}
                        />
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && isSubmittedReceiptPdf ? (
                      <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                        <iframe
                          src={submitReceiptPreview.signed_url}
                          title={submitReceiptPreview.file_name || 'Receipt PDF preview'}
                          style={{
                            width: '100%',
                            height: '520px',
                            border: 'none',
                            borderRadius: '12px',
                            backgroundColor: 'white',
                          }}
                        />
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && !isSubmittedReceiptImage && !isSubmittedReceiptPdf ? (
                      <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                        ไฟล์นี้ไม่ใช่รูปภาพ ใช้ปุ่ม Open Receipt เพื่อเปิดไฟล์ต้นฉบับ
                      </div>
                    ) : null}
                  </div>
                </motion.div>
              ) : extractData ? (
                <motion.div
                  key="extract-result"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}
                >
                  {extractData.low_confidence_fields?.length ? (
                    <StatusBanner
                      tone="warning"
                      text={`OCR ยังไม่มั่นใจในบางช่อง: ${extractData.low_confidence_fields.map(formatOcrFieldLabel).join(', ')} กรุณาตรวจและแก้ไขก่อนส่ง`}
                    />
                  ) : null}
                  <div className="card" style={{ backgroundColor: 'white', borderRadius: '20px', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                      <ReceiptText size={20} />
                      <h2 style={{ fontSize: '22px', margin: 0 }}>OCR Preview</h2>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
                      <strong>Uploaded Receipt</strong>

                      {canPreviewLocalReceipt && isLocalReceiptImage ? (
                        <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                          <img
                            src={localReceiptPreviewUrl}
                            alt={selectedFile?.name || 'Uploaded receipt preview'}
                            style={{
                              width: '100%',
                              maxHeight: '360px',
                              objectFit: 'contain',
                              borderRadius: '12px',
                              display: 'block',
                              backgroundColor: 'white',
                            }}
                          />
                        </div>
                      ) : null}

                      {canPreviewLocalReceipt && isLocalReceiptPdf ? (
                        <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                          <iframe
                            src={localReceiptPreviewUrl}
                            title={selectedFile?.name || 'Uploaded receipt PDF preview'}
                            style={{
                              width: '100%',
                              height: '520px',
                              border: 'none',
                              borderRadius: '12px',
                              backgroundColor: 'white',
                            }}
                          />
                        </div>
                      ) : null}

                      {canPreviewLocalReceipt && !isLocalReceiptImage && !isLocalReceiptPdf ? (
                        <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                          ไฟล์นี้ไม่สามารถ preview ในเบราว์เซอร์ได้ แต่ระบบยังใช้ไฟล์นี้อ่าน OCR ได้
                        </div>
                      ) : null}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '18px' }}>
                      <div><strong>File:</strong> {extractData.file_name}</div>
                      <div><strong>Vendor:</strong> {extractData.vendor_name || '-'}</div>
                      <div><strong>Receipt No:</strong> {extractData.receipt_no || '-'}</div>
                      <div><strong>Date:</strong> {extractData.document_date || '-'}</div>
                      <div><strong>Suggested:</strong> {extractData.suggested_request_type || '-'}</div>
                      <div><strong>Total:</strong> {Number(extractData.total_amount || 0).toLocaleString()} THB</div>
                      <div><strong>Entry Type:</strong> {formatEntryTypeLabel(extractData.suggested_entry_type)}</div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {extractData.items?.map((item, index) => (
                        <div
                          key={`${item.description}-${index}`}
                          style={{
                            backgroundColor: '#f9f6f0',
                            borderRadius: '14px',
                            padding: '12px 14px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '12px',
                          }}
                        >
                          <span>{item.description}</span>
                          <span>{item.qty} x {item.price}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="empty-state"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                >
                  <div>
                    <h2 style={{ fontSize: '24px', marginBottom: '10px', color: '#1a1a1a' }}>
                      Input Workflow Preview
                    </h2>
                    <p style={{ color: '#6b6256', lineHeight: 1.6 }}>
                      เลือกโครงการ อัปโหลดใบเสร็จหรือ PDF เพื่อให้ Gemini ช่วยอ่านข้อมูลและส่งคำขอเข้า backend ใหม่ที่ออกแบบตาม flow
                      ของ subcontractor input และ admin review
                    </p>
                  </div>
                  <ConstructionAnimation />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default InputPage;
