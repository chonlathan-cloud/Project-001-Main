import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, CheckCircle2, ExternalLink, LoaderCircle, Plus, ReceiptText, RotateCcw, TriangleAlert, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Loading from './components/Loading';
import ConstructionAnimation from './components/ConstructionAnimation';
import {
  extractInputReceipt,
  getInputDefaults,
  getInputRequestReceiptUrl,
  getInputProjectOptions,
  submitInputRequest,
  uploadInputReceipt,
} from './api';
import { getStoredAuthUser } from './auth';

const MotionDiv = motion.div;

const ENTRY_TYPE_OPTIONS = [
  { value: 'EXPENSE', label: 'รายจ่าย' },
  { value: 'INCOME', label: 'รายรับ' },
];

const STATUS_LABELS = {
  DRAFT: 'แบบร่าง',
  PENDING: 'รอตรวจสอบ',
  PENDING_ADMIN: 'รอผู้ดูแลตรวจสอบ',
  APPROVED: 'อนุมัติแล้ว',
  PAID: 'จ่ายเงินแล้ว',
  REJECTED: 'ไม่อนุมัติ',
};

const DEFAULT_WORK_TYPE_VALUES = [
  'งานโครงสร้าง',
  'งานสถาปัตย์',
  'งานระบบ',
  'งานบริหารโครงการ',
  'งานตกแต่ง (Build in)',
];

const OTHER_WORK_TYPE_VALUE = '__OTHER_WORK_TYPE__';
const OTHER_WORK_TYPE_LABEL = 'งานอื่นๆ โปรดระบุ';

const OTHER_WORK_TYPE_OPTION = {
  value: OTHER_WORK_TYPE_VALUE,
  label: OTHER_WORK_TYPE_LABEL,
};

const WORK_TYPE_OPTIONS = DEFAULT_WORK_TYPE_VALUES.map((value) => ({ value, label: value }));

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
  if (normalized === OTHER_WORK_TYPE_VALUE || normalized === OTHER_WORK_TYPE_LABEL) return '';
  return normalized;
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
  customWorkType: '',
  requestType: '',
  tags: [],
  note: '',
  vendorName: '',
  receiptNo: '',
  bankName: '',
  accountNo: '',
  accountName: '',
  amount: '',
};

const cleanText = (value) => String(value || '').trim();

const mergeTextValues = (...groups) => {
  const merged = [];
  const seen = new Set();

  groups.flat().forEach((item) => {
    const cleaned = cleanText(item);
    if (!cleaned || cleaned === OTHER_WORK_TYPE_VALUE || cleaned === OTHER_WORK_TYPE_LABEL) return;
    const key = cleaned.toLocaleLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(cleaned);
  });

  return merged;
};

const buildWorkTypeOptions = (values = []) =>
  mergeTextValues(DEFAULT_WORK_TYPE_VALUES, values).map((value) => ({ value, label: value }));

const normalizeTags = (values = []) => mergeTextValues(Array.isArray(values) ? values : []);

const pickFirstText = (...values) =>
  values.map(cleanText).find(Boolean) || '';

const buildCurrentUserDefaults = () => {
  const authUser = getStoredAuthUser() || {};

  return {
    requesterName: pickFirstText(
      authUser.contact_name,
      authUser.contactName,
      authUser.name,
      authUser.display_name,
      authUser.displayName,
      authUser.email
    ),
    phone: pickFirstText(
      authUser.phone,
      authUser.contact_phone,
      authUser.contactPhone,
      authUser.mobile,
      authUser.tel
    ),
  };
};

const resolveInputDefaults = (defaults = {}) => {
  const currentUserDefaults = buildCurrentUserDefaults();

  return {
    requesterName: pickFirstText(defaults.requesterName, currentUserDefaults.requesterName),
    phone: pickFirstText(defaults.phone, currentUserDefaults.phone),
    bankName: pickFirstText(defaults.bankName),
    accountNo: pickFirstText(defaults.accountNo),
    accountName: pickFirstText(defaults.accountName),
  };
};

const buildDefaultedFormState = (defaults = {}, overrides = {}) => {
  const resolvedDefaults = resolveInputDefaults(defaults);

  return {
    ...initialFormState,
    requesterName: resolvedDefaults.requesterName || initialFormState.requesterName,
    phone: resolvedDefaults.phone || initialFormState.phone,
    bankName: resolvedDefaults.bankName || initialFormState.bankName,
    accountNo: resolvedDefaults.accountNo || initialFormState.accountNo,
    accountName: resolvedDefaults.accountName || initialFormState.accountName,
    ...overrides,
  };
};

const formatOcrItemDetail = (item) => {
  const description = cleanText(item?.description);
  if (!description) return '';

  const qty = Number(item?.qty);
  const price = Number(item?.price);
  const details = [];

  if (Number.isFinite(qty) && qty > 0) details.push(`จำนวน ${qty}`);
  if (Number.isFinite(price) && price > 0) details.push(`${price.toLocaleString()} บาท`);

  return details.length ? `${description} (${details.join(' x ')})` : description;
};

const buildRequestDetailFromOcr = (extracted = {}) => {
  const itemDetails = Array.isArray(extracted.items)
    ? extracted.items.map(formatOcrItemDetail).filter(Boolean)
    : [];

  if (itemDetails.length) return itemDetails.join('\n');

  return [
    extracted.vendor_name,
    extracted.receipt_no,
    extracted.document_date,
  ]
    .map(cleanText)
    .filter(Boolean)
    .join(' | ');
};

const fieldBaseStyle = {
  width: '100%',
  padding: '11px 14px',
  borderRadius: '8px',
  backgroundColor: '#fff',
  border: '1px solid #e2e8f0',
  fontSize: '14px',
  outline: 'none',
  color: 'var(--text-main)',
  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
};

const InputField = ({
  label,
  placeholder,
  type = 'text',
  inputMode,
  style = {},
  value,
  onChange,
  disabled = false,
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-main)' }}>{label}</label>}
    <input
      type={type}
      inputMode={inputMode}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      style={{
        ...fieldBaseStyle,
        textAlign: type === 'number' ? 'right' : 'left',
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
    {label && <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-main)' }}>{label}</label>}
    <div style={{ position: 'relative' }}>
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        style={{
          ...fieldBaseStyle,
          textAlign: 'left',
          appearance: 'none',
          color: value ? 'var(--text-main)' : 'var(--text-muted)',
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

const EntryTypeSegment = ({ value, onChange }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-main)' }}>รายจ่าย / รายรับ</label>
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: '6px',
        padding: '4px',
        borderRadius: '10px',
        backgroundColor: 'var(--bg-primary)',
        border: '1px solid var(--border-color)',
      }}
    >
      {ENTRY_TYPE_OPTIONS.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            style={{
              minHeight: '42px',
              border: active ? '1px solid var(--primary)' : '1px solid transparent',
              borderRadius: '8px',
              backgroundColor: active ? 'var(--primary)' : 'transparent',
              color: active ? '#fff' : 'var(--text-main)',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '700',
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  </div>
);

const TextAreaField = ({ label, placeholder, style = {}, value, onChange }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-main)' }}>{label}</label>}
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

const TagInput = ({
  label,
  required = false,
  selectedTags,
  suggestions,
  draftValue,
  onDraftChange,
  onAddTag,
  onRemoveTag,
}) => {
  const selectedKeys = new Set(selectedTags.map((tag) => tag.toLocaleLowerCase()));
  const availableSuggestions = suggestions.filter(
    (tag) => !selectedKeys.has(tag.toLocaleLowerCase())
  );

  const handleKeyDown = (event) => {
    if (event.key !== 'Enter' && event.key !== ',') return;
    event.preventDefault();
    onAddTag(draftValue);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-main)' }}>
        {label}{required ? ' *' : ''}
      </label>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '8px',
          borderRadius: '8px',
          border: '1px solid #e2e8f0',
          backgroundColor: '#fff',
        }}
      >
        {selectedTags.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => onRemoveTag(tag)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              minHeight: '30px',
              padding: '0 9px',
              borderRadius: '999px',
              border: '1px solid rgba(79, 111, 100, 0.2)',
              backgroundColor: 'rgba(79, 111, 100, 0.08)',
              color: 'var(--primary)',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: '800',
            }}
          >
            {tag}
            <X size={13} />
          </button>
        ))}
        <input
          type="text"
          value={draftValue}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="เพิ่มแท็ก"
          style={{
            flex: '1 1 160px',
            minWidth: '120px',
            minHeight: '32px',
            border: 'none',
            outline: 'none',
            fontSize: '14px',
            color: 'var(--text-main)',
          }}
        />
        <button
          type="button"
          onClick={() => onAddTag(draftValue)}
          style={{
            width: '32px',
            height: '32px',
            display: 'inline-grid',
            placeItems: 'center',
            borderRadius: '8px',
            border: '1px solid var(--primary)',
            backgroundColor: 'var(--primary)',
            color: '#fff',
            cursor: 'pointer',
          }}
          aria-label="เพิ่มแท็ก"
        >
          <Plus size={16} />
        </button>
      </div>
      {availableSuggestions.length ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {availableSuggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => onAddTag(tag)}
              style={{
                minHeight: '30px',
                padding: '0 10px',
                borderRadius: '999px',
                border: '1px solid #e7decd',
                backgroundColor: '#f7f3ef',
                color: 'var(--text-main)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: '750',
              }}
            >
              {tag}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
};

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

const formatStatusLabel = (status) => {
  const normalized = String(status || '').trim().toUpperCase();
  return STATUS_LABELS[normalized] || status || '-';
};

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
  const [workTypeOptions, setWorkTypeOptions] = useState(WORK_TYPE_OPTIONS);
  const [tagOptions, setTagOptions] = useState([]);
  const [inputDefaults, setInputDefaults] = useState(() => buildDefaultedFormState());
  const [form, setForm] = useState(initialFormState);
  const [tagDraft, setTagDraft] = useState('');
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
  const [entryTypeTouched, setEntryTypeTouched] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        setLoading(true);
        setPageError('');
        const [items, defaults] = await Promise.all([
          getInputProjectOptions(),
          getInputDefaults(),
        ]);
        const resolvedDefaults = resolveInputDefaults(defaults);
        setWorkTypeOptions(buildWorkTypeOptions(defaults.workTypes || []));
        setTagOptions(mergeTextValues(defaults.tags || []));
        setProjects(items);
        setInputDefaults(buildDefaultedFormState(resolvedDefaults));
        setForm((current) => {
          const nextProjectId =
            current.projectId || (items.length === 1 ? String(items[0].project_id || '') : '');
          return buildDefaultedFormState(resolvedDefaults, {
            ...current,
            projectId: nextProjectId,
            requesterName: current.requesterName || resolvedDefaults.requesterName || '',
            phone: current.phone || resolvedDefaults.phone || '',
            bankName: current.bankName || resolvedDefaults.bankName || '',
            accountNo: current.accountNo || resolvedDefaults.accountNo || '',
            accountName: current.accountName || resolvedDefaults.accountName || '',
          });
        });
      } catch (error) {
        setPageError(error.message || 'โหลดข้อมูลโครงการสำหรับฟอร์มไม่สำเร็จ');
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
        setSubmitReceiptPreviewError(error.message || 'โหลดตัวอย่างใบเสร็จไม่สำเร็จ');
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

  const handleAddTag = (rawValue) => {
    const [cleaned] = mergeTextValues([rawValue]);
    if (!cleaned) return;
    setForm((current) => ({
      ...current,
      tags: mergeTextValues(current.tags, [cleaned]),
    }));
    setTagDraft('');
  };

  const handleRemoveTag = (tagToRemove) => {
    const removeKey = cleanText(tagToRemove).toLocaleLowerCase();
    setForm((current) => ({
      ...current,
      tags: normalizeTags(current.tags).filter(
        (tag) => tag.toLocaleLowerCase() !== removeKey
      ),
    }));
  };

  const handleEntryTypeChange = (nextType) => {
    setEntryTypeTouched(true);
    setForm((current) => ({
      ...current,
      entryType: nextType,
      workType: nextType === 'INCOME' ? '' : current.workType,
      customWorkType: nextType === 'INCOME' ? '' : current.customWorkType,
      requestType: nextType === 'INCOME' ? '' : current.requestType,
    }));
    setSubmitError('');
    setSubmitResult(null);
  };

  const handleClearDraft = () => {
    setForm(buildDefaultedFormState(inputDefaults, {
      projectId:
        projects.length === 1
          ? String(projects[0]?.project_id || '')
          : '',
    }));
    setSelectedFile(null);
    setLocalReceiptPreviewUrl('');
    setExtractData(null);
    setUploadedReceipt(null);
    setSubmitResult(null);
    setSubmitReceiptPreview(null);
    setSubmitReceiptPreviewError('');
    setSubmitError('');
    setFlashMessage('');
    setTagDraft('');
    setEntryTypeTouched(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePickFile = () => {
    if (isExtracting || isSubmitting) return;
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
    setSubmitResult(null);
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
      setForm((current) => {
        const nextEntryType =
          !entryTypeTouched && normalizedExtracted.suggested_entry_type
            ? normalizedExtracted.suggested_entry_type
            : current.entryType;
        const nextRequestType = current.requestType || normalizedExtracted.suggested_request_type || '';
        const nextRequestDetail = current.note || buildRequestDetailFromOcr(normalizedExtracted);

        return {
          ...current,
          entryType: nextEntryType,
          amount: current.amount
            ? current.amount
            : normalizedExtracted.total_amount == null
              ? ''
              : String(normalizedExtracted.total_amount),
          documentDate: current.documentDate || normalizeDateInputValue(normalizedExtracted.document_date),
          workType: nextEntryType === 'INCOME' ? '' : current.workType,
          customWorkType: nextEntryType === 'INCOME' ? '' : current.customWorkType,
          requestType: nextEntryType === 'INCOME' ? '' : nextRequestType,
          vendorName: current.vendorName || normalizedExtracted.vendor_name || '',
          receiptNo: current.receiptNo || normalizedExtracted.receipt_no || '',
          note: nextRequestDetail,
        };
      });
      setFlashMessage(`อ่านข้อมูลจาก ${file.name} สำเร็จแล้ว`);
    } catch (error) {
      setSubmitError(error.message || 'อ่านข้อมูลจากใบเสร็จไม่สำเร็จ');
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

    const isIncomeRequest = form.entryType === 'INCOME';
    const normalizedTags = normalizeTags(form.tags);
    const normalizedWorkType = isIncomeRequest
      ? ''
      : form.workType === OTHER_WORK_TYPE_VALUE
        ? normalizeWorkType(form.customWorkType)
        : normalizeWorkType(form.workType);
    const normalizedRequestType = isIncomeRequest ? '' : normalizeRequestType(form.requestType);
    const normalizedDocumentDate = form.documentDate || form.requestDate;
    const numericAmount = Number(form.amount);

    if (isIncomeRequest && normalizedTags.length === 0) {
      setSubmitError('รายการรายรับต้องมีแท็กอย่างน้อย 1 รายการ');
      return;
    }
    if (!isIncomeRequest && form.workType === OTHER_WORK_TYPE_VALUE && !normalizedWorkType) {
      setSubmitError('กรุณาระบุประเภทงานอื่นๆ');
      return;
    }
    if (!isIncomeRequest && form.requestType && !normalizedRequestType) {
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
        work_type: isIncomeRequest ? null : normalizedWorkType || null,
        request_type: isIncomeRequest ? null : normalizedRequestType || null,
        tags: normalizedTags,
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
      if (normalizedWorkType) {
        setWorkTypeOptions((current) =>
          buildWorkTypeOptions([...current.map((option) => option.value), normalizedWorkType])
        );
      }
      setTagOptions((current) => mergeTextValues(current, response?.tags || normalizedTags));
      setFlashMessage('ส่งคำขอเรียบร้อยแล้ว');
      setForm(
        buildDefaultedFormState(inputDefaults, {
          entryType: form.entryType,
          projectId:
            projects.length === 1
              ? String(projects[0]?.project_id || '')
              : '',
        })
      );
      setSelectedFile(null);
      setExtractData(null);
      setUploadedReceipt(null);
      setTagDraft('');
      setEntryTypeTouched(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      setSubmitError(error.message || 'ส่งคำขอไม่สำเร็จ');
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
  const hasAssignedProjects = projectOptions.length > 0;
  const workTypeSelectOptions = [...workTypeOptions, OTHER_WORK_TYPE_OPTION];
  const selectedTags = normalizeTags(form.tags);
  const numericFormAmount = Number(form.amount);
  const isSubmitDisabled =
    isSubmitting ||
    isExtracting ||
    !hasAssignedProjects ||
    !form.projectId ||
    !form.requesterName.trim() ||
    !form.requestDate ||
    !form.amount ||
    !Number.isFinite(numericFormAmount) ||
    numericFormAmount <= 0 ||
    (isIncome && selectedTags.length === 0) ||
    (!isIncome && form.workType === OTHER_WORK_TYPE_VALUE && !form.customWorkType.trim()) ||
    (!selectedFile && !uploadedReceipt);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          gap: '16px',
          marginBottom: '28px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '32px', marginBottom: '8px', fontWeight: '700', color: 'var(--text-main)' }}>
            ส่งคำขอ
          </h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            อัปโหลดใบเสร็จ ตรวจข้อมูลที่ระบบอ่านได้ แล้วส่งให้ผู้ดูแลตรวจสอบ
          </p>
        </div>
        <button
          type="button"
          onClick={handleClearDraft}
          disabled={isExtracting || isSubmitting}
          style={{
            minHeight: '42px',
            padding: '0 14px',
            borderRadius: '8px',
            border: '1px solid var(--secondary)',
            backgroundColor: 'var(--card-bg)',
            color: 'var(--secondary)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            cursor: isExtracting || isSubmitting ? 'wait' : 'pointer',
            fontWeight: '700',
          }}
        >
          <RotateCcw size={16} />
          ล้างแบบร่าง
        </button>
      </div>

      <MotionDiv
        className="input-workflow-layout"
        layout
        style={{
          display: 'flex',
          flexDirection: 'row',
          gap: '32px',
          alignItems: 'start',
        }}
      >
        <MotionDiv layout style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <form onSubmit={handleSubmit}>
            <div
              className="card"
              style={{
                backgroundColor: 'var(--card-bg)',
                padding: '32px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '20px',
                borderRadius: '12px',
                border: '1px solid var(--border-color)',
                boxShadow: 'none',
              }}
            >
              <AnimatePresence mode="popLayout">
                {flashMessage ? (
                  <MotionDiv
                    key="flash-message"
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                  >
                    <StatusBanner tone="success" text={flashMessage} />
                  </MotionDiv>
                ) : null}
              </AnimatePresence>

              {submitError ? <StatusBanner tone="error" text={submitError} /> : null}

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  padding: '18px',
                  borderRadius: '12px',
                  backgroundColor: 'var(--bg-primary)',
                  border: '2px dashed #c1c8c4',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
                    1. อัปโหลดไฟล์ใบเสร็จ
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
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
                  disabled={isExtracting || isSubmitting}
                  style={{
                    width: '100%',
                    height: '140px',
                    backgroundColor: 'var(--card-bg)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    cursor: isExtracting || isSubmitting ? 'wait' : 'pointer',
                    color: 'var(--text-main)',
                    opacity: isSubmitting ? 0.7 : 1,
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
                        {selectedFile ? selectedFile.name : 'อัปโหลดรูปใบเสร็จ / PDF'}
                      </span>
                      <ArrowUp size={16} />
                    </>
                  )}
                </button>
              </div>

              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
                2. รายละเอียดคำขอ
              </div>

              <EntryTypeSegment value={form.entryType} onChange={handleEntryTypeChange} />

              <SelectField
                label="โครงการ"
                placeholder="กรุณาเลือกโครงการ"
                options={projectOptions}
                value={form.projectId}
                onChange={handleFieldChange('projectId')}
                disabled={!hasAssignedProjects}
              />

              {!hasAssignedProjects ? (
                <StatusBanner
                  tone="warning"
                  text="บัญชีนี้ยังไม่มีโครงการที่ได้รับมอบหมาย กรุณาติดต่อผู้ดูแลระบบให้ตั้งค่าโครงการให้ก่อน"
                />
              ) : null}

              <InputField
                label="ชื่อ - นามสกุล"
                placeholder="กรุณากรอกชื่อ-นามสกุล"
                value={form.requesterName}
                onChange={handleFieldChange('requesterName')}
              />

              <div className="subcon-field-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="เบอร์ติดต่อ"
                  placeholder="กรุณากรอกเบอร์โทรศัพท์"
                  inputMode="tel"
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

              <div className="subcon-field-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
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

              {!isIncome ? (
                <>
                  <div className="subcon-field-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <SelectField
                      label="ประเภทงาน"
                      placeholder="กรุณาเลือก"
                      options={workTypeSelectOptions}
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

                  {form.workType === OTHER_WORK_TYPE_VALUE ? (
                    <InputField
                      label="ระบุประเภทงาน"
                      placeholder="กรุณาระบุประเภทงาน"
                      value={form.customWorkType}
                      onChange={handleFieldChange('customWorkType')}
                    />
                  ) : null}
                </>
              ) : null}

              <TagInput
                label="แท็ก"
                required={isIncome}
                selectedTags={selectedTags}
                suggestions={tagOptions}
                draftValue={tagDraft}
                onDraftChange={setTagDraft}
                onAddTag={handleAddTag}
                onRemoveTag={handleRemoveTag}
              />

              <TextAreaField
                label="รายการ / ค่าอะไร"
                placeholder="กรุณากรอกรายการหรือรายละเอียดค่าใช้จ่าย"
                value={form.note}
                onChange={handleFieldChange('note')}
                style={{ width: '100%' }}
              />

              <InputField
                label="ผู้ขาย / ร้านค้า"
                placeholder="กรุณากรอกชื่อร้านหรือผู้ขาย"
                value={form.vendorName}
                onChange={handleFieldChange('vendorName')}
              />

              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
                3. บัญชีรับเงิน
              </div>

              <div className="subcon-field-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
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
                  inputMode="decimal"
                  value={form.amount}
                  onChange={handleFieldChange('amount')}
                />
              </div>

              <div className="subcon-field-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <InputField
                  label="เลขที่บัญชี"
                  placeholder="กรุณากรอก"
                  inputMode="numeric"
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

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={handleClearDraft}
                  disabled={isExtracting || isSubmitting}
                  style={{
                    backgroundColor: 'var(--card-bg)',
                    color: 'var(--secondary)',
                    border: '1px solid var(--secondary)',
                    borderRadius: '8px',
                    padding: '12px 18px',
                    fontSize: '14px',
                    fontWeight: '700',
                    cursor: isExtracting || isSubmitting ? 'wait' : 'pointer',
                  }}
                >
                  ล้างข้อมูล
                </button>
                <button
                  type="submit"
                  disabled={isSubmitDisabled}
                  style={{
                    backgroundColor: 'var(--primary)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '12px 24px',
                    fontSize: '15px',
                    fontWeight: '700',
                    cursor: isSubmitDisabled ? 'not-allowed' : 'pointer',
                    minWidth: '220px',
                    boxShadow: 'none',
                    opacity: isSubmitDisabled ? 0.65 : 1,
                  }}
                >
                  {isSubmitting ? 'กำลังส่ง...' : 'ส่งให้ผู้ดูแลตรวจสอบ'}
                </button>
              </div>
            </div>
          </form>
        </MotionDiv>

        <MotionDiv
          className="input-preview-panel"
          layout
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-primary)',
            minHeight: '760px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'stretch',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
          }}
        >
          <div style={{ width: '100%', padding: '28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <AnimatePresence mode="wait">
              {submitResult ? (
                <MotionDiv
                  key="submit-result"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}
                >
                  <StatusBanner
                    tone="success"
                    text={`สร้างคำขอสำเร็จ สถานะ ${formatStatusLabel(submitResult.status || 'PENDING_ADMIN')}`}
                  />
                  {submitResult.is_duplicate_flag ? (
                    <StatusBanner
                      tone="warning"
                      text={submitResult.duplicate_reason || 'พบรายการซ้ำตามกฎเลขที่ใบเสร็จ + วันที่ + จำนวนเงิน'}
                    />
                  ) : null}
                  {submitResult.ocr_low_confidence_fields?.length ? (
                    <StatusBanner
                      tone="warning"
                      text={`OCR ยังไม่มั่นใจในบางช่อง: ${submitResult.ocr_low_confidence_fields.map(formatOcrFieldLabel).join(', ')}`}
                    />
                  ) : null}
                  <div className="card" style={{ backgroundColor: 'var(--card-bg)', borderRadius: '12px', padding: '24px' }}>
                    <h2 style={{ fontSize: '22px', marginBottom: '16px' }}>สรุปคำขอ</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                      <div><strong>เลขคำขอ:</strong> {submitResult.request_id}</div>
                      <div><strong>โครงการ:</strong> {submitResult.project_name}</div>
                      <div><strong>ประเภทรายการ:</strong> {formatEntryTypeLabel(submitResult.entry_type)}</div>
                      <div><strong>ผู้ส่งคำขอ:</strong> {submitResult.requester_name}</div>
                      <div><strong>ผู้ขาย / ร้านค้า:</strong> {submitResult.vendor_name || '-'}</div>
                      <div><strong>เลขที่ใบเสร็จ:</strong> {submitResult.receipt_no || '-'}</div>
                      <div><strong>ประเภทงาน:</strong> {submitResult.work_type || '-'}</div>
                      <div><strong>ประเภทการเบิก:</strong> {submitResult.request_type || '-'}</div>
                      <div><strong>วันที่เอกสาร:</strong> {submitResult.document_date || '-'}</div>
                      <div><strong>จำนวนเงิน:</strong> {Number(submitResult.amount || 0).toLocaleString()} บาท</div>
                      <div><strong>แท็ก:</strong> {normalizeTags(submitResult.tags).join(', ') || '-'}</div>
                      <div><strong>สถานะ:</strong> {formatStatusLabel(submitResult.status)}</div>
                    </div>
                  </div>
                  <div className="card" style={{ backgroundColor: 'var(--card-bg)', borderRadius: '12px', padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
                      <div>
                        <h2 style={{ fontSize: '22px', margin: 0 }}>ตัวอย่างใบเสร็จ</h2>
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
                            color: 'var(--secondary)',
                            backgroundColor: 'var(--card-bg)',
                            border: '1px solid var(--secondary)',
                            borderRadius: '8px',
                            padding: '10px 12px',
                            fontSize: '13px',
                            fontWeight: '600',
                          }}
                        >
                          <ExternalLink size={16} />
                          <span>เปิดใบเสร็จ</span>
                        </a>
                      ) : null}
                    </div>

                    {submitReceiptPreviewLoading ? (
                      <div style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 16px' }}>
                        กำลังโหลดลิงก์ไฟล์...
                      </div>
                    ) : null}

                    {submitReceiptPreviewError ? (
                      <div style={{ color: '#912018', backgroundColor: '#fde8e8', border: '1px solid #de5b52', borderRadius: '12px', padding: '12px 14px' }}>
                        {submitReceiptPreviewError}
                      </div>
                    ) : null}

                    {!submitResult.receipt_storage_key && !submitReceiptPreviewLoading ? (
                      <div style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 16px' }}>
                        คำขอนี้ไม่มีไฟล์ใบเสร็จที่เก็บไว้
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && isSubmittedReceiptImage ? (
                      <div style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '12px' }}>
                        <img
                          src={submitReceiptPreview.signed_url}
                          alt={submitReceiptPreview.file_name || 'ตัวอย่างใบเสร็จ'}
                          style={{
                            width: '100%',
                            maxHeight: '360px',
                            objectFit: 'contain',
                            borderRadius: '12px',
                            display: 'block',
                            backgroundColor: 'var(--card-bg)',
                          }}
                        />
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && isSubmittedReceiptPdf ? (
                      <div style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '12px' }}>
                        <iframe
                          src={submitReceiptPreview.signed_url}
                          title={submitReceiptPreview.file_name || 'ตัวอย่างใบเสร็จ PDF'}
                          style={{
                            width: '100%',
                            height: '520px',
                            border: 'none',
                            borderRadius: '12px',
                            backgroundColor: 'var(--card-bg)',
                          }}
                        />
                      </div>
                    ) : null}

                    {canPreviewSubmittedReceipt && !isSubmittedReceiptImage && !isSubmittedReceiptPdf ? (
                      <div style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 16px' }}>
                        ไฟล์นี้ไม่ใช่รูปภาพ ใช้ปุ่มเปิดใบเสร็จเพื่อเปิดไฟล์ต้นฉบับ
                      </div>
                    ) : null}
                  </div>
                </MotionDiv>
              ) : extractData ? (
                <MotionDiv
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
                  <div className="card" style={{ backgroundColor: 'var(--card-bg)', borderRadius: '12px', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                      <ReceiptText size={20} />
                      <h2 style={{ fontSize: '22px', margin: 0 }}>ตัวอย่างข้อมูล OCR</h2>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
                      <strong>ใบเสร็จที่อัปโหลด</strong>

                      {canPreviewLocalReceipt && isLocalReceiptImage ? (
                        <div style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '12px' }}>
                          <img
                            src={localReceiptPreviewUrl}
                            alt={selectedFile?.name || 'ตัวอย่างใบเสร็จที่อัปโหลด'}
                            style={{
                              width: '100%',
                              maxHeight: '360px',
                              objectFit: 'contain',
                              borderRadius: '12px',
                              display: 'block',
                              backgroundColor: 'var(--card-bg)',
                            }}
                          />
                        </div>
                      ) : null}

                      {canPreviewLocalReceipt && isLocalReceiptPdf ? (
                        <div style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '12px' }}>
                          <iframe
                            src={localReceiptPreviewUrl}
                            title={selectedFile?.name || 'ตัวอย่างใบเสร็จ PDF ที่อัปโหลด'}
                            style={{
                              width: '100%',
                              height: '520px',
                              border: 'none',
                              borderRadius: '12px',
                              backgroundColor: 'var(--card-bg)',
                            }}
                          />
                        </div>
                      ) : null}

                      {canPreviewLocalReceipt && !isLocalReceiptImage && !isLocalReceiptPdf ? (
                        <div style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 16px' }}>
                          ไฟล์นี้ไม่สามารถแสดงตัวอย่างในเบราว์เซอร์ได้ แต่ระบบยังใช้ไฟล์นี้อ่าน OCR ได้
                        </div>
                      ) : null}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '18px' }}>
                      <div><strong>ไฟล์:</strong> {extractData.file_name}</div>
                      <div><strong>ผู้ขาย / ร้านค้า:</strong> {extractData.vendor_name || '-'}</div>
                      <div><strong>เลขที่ใบเสร็จ:</strong> {extractData.receipt_no || '-'}</div>
                      <div><strong>วันที่:</strong> {extractData.document_date || '-'}</div>
                      <div><strong>ประเภทที่ระบบแนะนำ:</strong> {extractData.suggested_request_type || '-'}</div>
                      <div><strong>ยอดรวม:</strong> {Number(extractData.total_amount || 0).toLocaleString()} บาท</div>
                      <div><strong>ประเภทรายการ:</strong> {formatEntryTypeLabel(extractData.suggested_entry_type)}</div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {extractData.items?.map((item, index) => (
                        <div
                          key={`${item.description}-${index}`}
                          style={{
                            backgroundColor: 'var(--bg-primary)',
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
                </MotionDiv>
              ) : (
                <MotionDiv
                  key="empty-state"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                >
                  <div>
                    <h2 style={{ fontSize: '24px', marginBottom: '10px', color: 'var(--text-main)' }}>
                      ตัวอย่างใบเสร็จ
                    </h2>
                    <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>
                      เลือกโครงการและอัปโหลดใบเสร็จหรือ PDF เพื่อให้ระบบช่วยอ่านข้อมูล แล้วส่งคำขอให้ผู้ดูแลตรวจสอบ
                    </p>
                  </div>
                  <ConstructionAnimation />
                </MotionDiv>
              )}
            </AnimatePresence>
          </div>
        </MotionDiv>
      </MotionDiv>
    </div>
  );
};

export default InputPage;
