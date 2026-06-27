import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CheckCheck, CircleDollarSign, OctagonX, Save, X } from 'lucide-react';
import Loading from './components/Loading';
import {
  approveAdminInputRequest,
  getAdminInputReceiptUrl,
  getAdminInputRequests,
  getInputRequestAccountingReadiness,
  getInputProjectOptions,
  linkInputRequestFlowAccountDocument,
  markPaidAdminInputRequest,
  rejectAdminInputRequest,
  retryInputRequestFlowAccountAttachment,
  retryInputRequestFlowAccountSupplierInvoice,
  syncInputRequestFlowAccount,
  updateAdminInputRequest,
} from './api';
import { canMutateAdminData, getStoredAuthUser } from './auth';
import {
  ApprovalActionBar,
  ApprovalAlertStack,
  ApprovalEvidencePanel,
  ApprovalField,
  ApprovalFlowAccountChecklist,
  ApprovalFormSection,
  ApprovalQueuePanel,
  ApprovalRequestHeader,
  ApprovalSummaryStrip,
} from './components/ApprovalWorkspace';
import InputLineItemsEditor from './components/InputLineItemsEditor';
import { createEmptyLineItem, sumLineItems } from './components/inputLineItemsUtils';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'PENDING_ADMIN', label: 'Pending Admin' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'PAID', label: 'Paid' },
  { value: 'REJECTED', label: 'Rejected' },
];

const ENTRY_TYPE_OPTIONS = [
  { value: '', label: 'ทุกประเภท' },
  { value: 'EXPENSE', label: 'รายจ่าย' },
  { value: 'INCOME', label: 'รายรับ' },
];

const REQUEST_TYPE_OPTIONS = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'ค่าวัสดุ', label: 'ค่าวัสดุ' },
  { value: 'ค่าแรง', label: 'ค่าแรง' },
  { value: 'ค่าเบิกล่วงหน้า', label: 'ค่าเบิกล่วงหน้า' },
  { value: 'ค่าใช้จ่ายทั่วไป', label: 'ค่าใช้จ่ายทั่วไป' },
];

const VAT_MODE_OPTIONS = [
  { value: '', label: 'เลือก VAT mode' },
  { value: 'no_vat', label: 'No VAT' },
  { value: 'vat_inclusive', label: 'VAT Inclusive' },
  { value: 'vat_exclusive', label: 'VAT Exclusive' },
];

const WORK_TYPE_OPTIONS = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'งานโครงสร้าง', label: 'งานโครงสร้าง' },
  { value: 'งานสถาปัตย์', label: 'งานสถาปัตย์' },
  { value: 'งานระบบ', label: 'งานระบบ' },
  { value: 'งานบริหารโครงการ', label: 'งานบริหารโครงการ' },
];

const REJECT_REASON_OPTIONS = [
  'ข้อมูลไม่ครบ',
  'ยอดเงินไม่ตรง',
  'เอกสารไม่ชัดเจน',
  'โปรเจ็คไม่ถูกต้อง',
  'ข้อมูลภาษีไม่ครบ',
];

const approvalActionIcons = {
  save: Save,
  approve: CheckCheck,
  reject: OctagonX,
  paid: CircleDollarSign,
};

const emptyEditor = {
  requester_name: '',
  phone: '',
  request_date: '',
  document_date: '',
  work_type: '',
  request_type: '',
  note: '',
  vendor_name: '',
  vendor_tax_id: '',
  vendor_branch: '',
  vendor_address: '',
  accounting_vat_mode: '',
  accounting_wht_rate: '',
  bank_name: '',
  account_no: '',
  account_name: '',
  receipt_no: '',
  amount: '',
  line_items: [createEmptyLineItem()],
  review_note: '',
  payment_reference: '',
  payment_date: new Date().toISOString().slice(0, 10),
};

const formatEntryType = (value) => (value === 'INCOME' ? 'รายรับ' : 'รายจ่าย');
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
const isReviewableStatus = (value) => ['DRAFT', 'PENDING_ADMIN', 'REJECTED'].includes(value);
const isEditableStatus = (value) => ['DRAFT', 'PENDING_ADMIN', 'REJECTED', 'APPROVED'].includes(value);
const matchesFilters = (item, filters) =>
  (!filters.status || item.status === filters.status) &&
  (!filters.entryType || item.entry_type === filters.entryType) &&
  (!filters.projectId || item.project_id === filters.projectId);
const cleanText = (value) => String(value || '').trim();
const toNumber = (value, fallback = 0) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};
const formatDialogAmount = (value) =>
  `${Number(value || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} THB`;
const normalizeEditorLineItems = (items = [], fallbackRequest = null) => {
  const sourceItems = Array.isArray(items) && items.length ? items : [];
  if (!sourceItems.length && fallbackRequest) {
    const fallbackAmount = toNumber(fallbackRequest.approved_amount ?? fallbackRequest.amount);
    return [
      createEmptyLineItem({
        description: cleanText(fallbackRequest.note || fallbackRequest.request_type || fallbackRequest.vendor_name || 'รายการคำขอ'),
        qty: 1,
        unit_price: fallbackAmount,
        amount: fallbackAmount,
        work_type: fallbackRequest.work_type || '',
        request_type: fallbackRequest.request_type || '',
      }),
    ];
  }

  return (sourceItems.length ? sourceItems : [createEmptyLineItem()]).map((item) => {
    const qty = toNumber(item?.qty, 1) || 1;
    const unitPrice = toNumber(item?.unit_price ?? item?.price);
    const amount = item?.amount == null ? Number((qty * unitPrice).toFixed(2)) : toNumber(item.amount);
    return createEmptyLineItem({
      id: item?.id || '',
      description: cleanText(item?.description),
      qty,
      unit_price: unitPrice,
      amount,
      work_type: item?.work_type || '',
      request_type: item?.request_type || '',
    });
  });
};
const normalizeLineItemsForSave = (items = [], selectedRequest = null) =>
  normalizeEditorLineItems(items, selectedRequest)
    .filter((item) => cleanText(item.description))
    .map((item) => ({
      id: item.id || null,
      description: cleanText(item.description),
      qty: toNumber(item.qty, 1) || 1,
      unit_price: toNumber(item.unit_price),
      amount: toNumber(item.amount),
      work_type: selectedRequest?.entry_type === 'INCOME' ? null : cleanText(item.work_type) || null,
      request_type: selectedRequest?.entry_type === 'INCOME' ? null : cleanText(item.request_type) || null,
    }));

function ApprovalPage() {
  const location = useLocation();
  const deepLinkParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const deepLinkRequestId = deepLinkParams.get('request_id') || '';
  const deepLinkProjectId = deepLinkParams.get('project_id') || '';
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [requests, setRequests] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState('');
  const [editor, setEditor] = useState(emptyEditor);
  const [filters, setFilters] = useState({
    status: deepLinkRequestId ? '' : 'PENDING_ADMIN',
    entryType: '',
    projectId: deepLinkProjectId,
  });
  const [pageError, setPageError] = useState('');
  const [actionError, setActionError] = useState('');
  const [flashMessage, setFlashMessage] = useState('');
  const [busyAction, setBusyAction] = useState('');
  const [receiptPreview, setReceiptPreview] = useState(null);
  const [receiptPreviewLoading, setReceiptPreviewLoading] = useState(false);
  const [receiptPreviewError, setReceiptPreviewError] = useState('');
  const [technicalDetailsOpen, setTechnicalDetailsOpen] = useState(false);
  const [accountingReadiness, setAccountingReadiness] = useState(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectDialogError, setRejectDialogError] = useState('');
  const [confirmDialog, setConfirmDialog] = useState(null);

  const selectedRequest = useMemo(
    () => requests.find((item) => item.request_id === selectedRequestId) || null,
    [requests, selectedRequestId]
  );

  const refreshReceiptPreview = async (request = null) => {
    const targetRequest = request || selectedRequest;

    if (!targetRequest?.receipt_storage_key) {
      setReceiptPreview(null);
      setReceiptPreviewError('');
      setReceiptPreviewLoading(false);
      return;
    }

    try {
      setReceiptPreviewLoading(true);
      setReceiptPreviewError('');
      const response = await getAdminInputReceiptUrl(targetRequest.request_id, {
        cacheToken: targetRequest.receipt_storage_key || '',
        forceRefresh: true,
      });
      setReceiptPreview(response);
    } catch (error) {
      setReceiptPreview(null);
      setReceiptPreviewError(error.message || 'Failed to load receipt preview.');
    } finally {
      setReceiptPreviewLoading(false);
    }
  };

  const syncEditorWithRequest = (request) => {
    if (!request) {
      setEditor(emptyEditor);
      return;
    }
    const lineItems = normalizeEditorLineItems(request.line_items, request);
    const lineItemTotal = sumLineItems(lineItems);

    setEditor({
      requester_name: request.requester_name || '',
      phone: request.phone || '',
      request_date: request.request_date || '',
      document_date: request.document_date || '',
      work_type: request.work_type || '',
      request_type: request.request_type || '',
      note: request.note || '',
      vendor_name: request.vendor_name || '',
      vendor_tax_id: request.vendor_tax_id || '',
      vendor_branch: request.vendor_branch || '',
      vendor_address: request.vendor_address || '',
      accounting_vat_mode: request.accounting_vat_mode || '',
      accounting_wht_rate: request.accounting_wht_rate ?? (request.request_type === 'ค่าแรง' ? 3 : ''),
      bank_name: request.bank_name || request.bank_account?.bank_name || '',
      account_no: request.account_no || request.bank_account?.account_no || '',
      account_name: request.account_name || request.bank_account?.account_name || '',
      receipt_no: request.receipt_no || '',
      amount: lineItemTotal || (request.approved_amount ?? request.amount ?? ''),
      line_items: lineItems,
      review_note: request.review_note || '',
      payment_reference: request.payment_reference || '',
      payment_date: request.paid_at ? String(request.paid_at).slice(0, 10) : new Date().toISOString().slice(0, 10),
    });
  };

  const loadData = async ({ keepSelection = true } = {}) => {
    const isInitial = !keepSelection && !requests.length;
    try {
      if (isInitial) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setPageError('');

      const [projectOptions, reviewQueue] = await Promise.all([
        getInputProjectOptions(),
        getAdminInputRequests(filters),
      ]);

      setProjects(projectOptions);
      setRequests(reviewQueue);

      if (reviewQueue.length === 0) {
        setSelectedRequestId('');
        setEditor(emptyEditor);
        return;
      }

      const nextSelectedId =
        keepSelection && reviewQueue.some((item) => item.request_id === selectedRequestId)
          ? selectedRequestId
          : deepLinkRequestId && reviewQueue.some((item) => item.request_id === deepLinkRequestId)
            ? deepLinkRequestId
            : reviewQueue[0].request_id;
      setSelectedRequestId(nextSelectedId);
      syncEditorWithRequest(reviewQueue.find((item) => item.request_id === nextSelectedId));
    } catch (error) {
      setPageError(error.message || 'Failed to load admin review queue.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData({ keepSelection: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!deepLinkRequestId && !deepLinkProjectId) return;
    setFilters((current) => ({
      ...current,
      status: deepLinkRequestId ? '' : current.status,
      projectId: deepLinkProjectId || current.projectId,
    }));
    if (deepLinkRequestId) {
      setSelectedRequestId(deepLinkRequestId);
    }
  }, [deepLinkProjectId, deepLinkRequestId]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.entryType, filters.projectId]);

  useEffect(() => {
    syncEditorWithRequest(selectedRequest);
  }, [selectedRequest]);

  useEffect(() => {
    setTechnicalDetailsOpen(false);
    setRejectDialogOpen(false);
    setRejectReason('');
    setRejectDialogError('');
  }, [selectedRequestId]);

  useEffect(() => {
    let isActive = true;

    const loadAccountingReadiness = async () => {
      if (!selectedRequest?.request_id) {
        setAccountingReadiness(null);
        return;
      }

      try {
        const response = await getInputRequestAccountingReadiness(selectedRequest.request_id);
        if (isActive) {
          setAccountingReadiness(response);
        }
      } catch (error) {
        if (isActive) {
          setAccountingReadiness({
            enabled: false,
            ready: false,
            can_sync_expense: false,
            can_sync_attachment: false,
            can_sync_supplier_invoice: false,
            can_mark_paid: false,
            missing_fields: [],
            errors: [error.message || 'Failed to load accounting readiness.'],
            external_document_id: selectedRequest.flowaccount_external_document_id || '',
          });
        }
      }
    };

    loadAccountingReadiness();

    return () => {
      isActive = false;
    };
  }, [
    selectedRequest?.request_id,
    selectedRequest?.status,
    selectedRequest?.flowaccount_sync_status,
    selectedRequest?.flowaccount_external_document_id,
  ]);

  useEffect(() => {
    let isActive = true;

    const loadReceiptPreview = async () => {
      if (!selectedRequest?.receipt_storage_key) {
        if (isActive) {
          setReceiptPreview(null);
          setReceiptPreviewError('');
          setReceiptPreviewLoading(false);
        }
        return;
      }

      try {
        if (isActive) {
          setReceiptPreviewLoading(true);
          setReceiptPreviewError('');
        }
        const response = await getAdminInputReceiptUrl(selectedRequest.request_id, {
          cacheToken: selectedRequest.receipt_storage_key || '',
        });
        if (!isActive) return;
        setReceiptPreview(response);
      } catch (error) {
        if (!isActive) return;
        setReceiptPreview(null);
        setReceiptPreviewError(error.message || 'Failed to load receipt preview.');
      } finally {
        if (isActive) {
          setReceiptPreviewLoading(false);
        }
      }
    };

    loadReceiptPreview();

    return () => {
      isActive = false;
    };
  }, [selectedRequest?.request_id, selectedRequest?.receipt_storage_key]);

  const handleEditorChange = (field) => (event) => {
    setEditor((current) => ({ ...current, [field]: event.target.value }));
    setActionError('');
    setFlashMessage('');
  };

  const handleEditorLineItemsChange = (nextLineItems) => {
    const normalizedLineItems = normalizeEditorLineItems(nextLineItems, selectedRequest);
    const totalAmount = sumLineItems(normalizedLineItems);
    setEditor((current) => ({
      ...current,
      line_items: normalizedLineItems,
      amount: totalAmount ? String(Number(totalAmount.toFixed(2))) : '',
    }));
    setActionError('');
    setFlashMessage('');
  };

  const replaceRequest = (nextItem) => {
    setRequests((current) => current.map((item) => (item.request_id === nextItem.request_id ? nextItem : item)));
    setSelectedRequestId(nextItem.request_id);
    syncEditorWithRequest(nextItem);
  };

  const handleSave = async () => {
    if (!selectedRequest) return;

    if (!canSaveChanges) {
      setActionError('รายการนี้ไม่สามารถบันทึกการแก้ไขได้');
      return;
    }

    try {
      setBusyAction('save');
      setActionError('');
      const savePayload = {
        review_note: editor.review_note.trim() || null,
        payment_reference: editor.payment_reference.trim() || null,
      };

      if (canEdit) {
        const lineItemsForSave = normalizeLineItemsForSave(editor.line_items, selectedRequest);
        const lineItemTotal = sumLineItems(lineItemsForSave);

        if (!lineItemsForSave.length) {
          setActionError('กรุณาเพิ่มรายการอย่างน้อย 1 รายการ');
          return;
        }
        if (lineItemTotal <= 0) {
          setActionError('ยอดรวมรายการต้องมากกว่า 0');
          return;
        }

        Object.assign(savePayload, {
          requester_name: editor.requester_name.trim(),
          phone: editor.phone.trim() || null,
          request_date: editor.request_date,
          document_date: editor.document_date || null,
          work_type: editor.work_type || null,
          request_type: editor.request_type || null,
          note: editor.note.trim() || null,
          vendor_name: editor.vendor_name.trim() || null,
          vendor_tax_id: editor.vendor_tax_id.trim() || null,
          vendor_branch: editor.vendor_branch.trim() || null,
          vendor_address: editor.vendor_address.trim() || null,
          accounting_vat_mode: editor.accounting_vat_mode || null,
          accounting_wht_rate: editor.accounting_wht_rate === '' ? null : Number(editor.accounting_wht_rate),
          bank_account: {
            bank_name: editor.bank_name.trim() || null,
            account_no: editor.account_no.trim() || null,
            account_name: editor.account_name.trim() || null,
          },
          receipt_no: editor.receipt_no.trim() || null,
          amount: Number(lineItemTotal.toFixed(2)),
          line_items: lineItemsForSave,
        });
      }

      if (canEditTaxFilingFields) {
        Object.assign(savePayload, {
          vendor_tax_id: editor.vendor_tax_id.trim() || null,
          vendor_branch: editor.vendor_branch.trim() || null,
          vendor_address: editor.vendor_address.trim() || null,
          receipt_no: editor.receipt_no.trim() || null,
        });
      }

      const updated = await updateAdminInputRequest(selectedRequest.request_id, savePayload);
      replaceRequest(updated);
      await refreshReceiptPreview(updated);
      setFlashMessage('บันทึกการแก้ไขเรียบร้อย');
    } catch (error) {
      setActionError(error.message || 'Failed to save review changes.');
    } finally {
      setBusyAction('');
    }
  };

  const handleApprove = async () => {
    if (!selectedRequest) return;
    const lineItemsForApprove = normalizeLineItemsForSave(editor.line_items, selectedRequest);
    const approvedLineItemTotal = sumLineItems(lineItemsForApprove);

    try {
      setBusyAction('approve');
      setActionError('');
      const approved = await approveAdminInputRequest(selectedRequest.request_id, {
        approved_amount: Number((approvedLineItemTotal || Number(editor.amount || 0)).toFixed(2)),
        line_items: lineItemsForApprove,
        review_note: editor.review_note.trim() || null,
      });
      if (matchesFilters(approved, filters)) {
        replaceRequest(approved);
        await refreshReceiptPreview(approved);
      } else {
        await loadData({ keepSelection: false });
      }
      setFlashMessage('อนุมัติคำขอเรียบร้อย');
    } catch (error) {
      setActionError(error.message || 'Failed to approve request.');
    } finally {
      setBusyAction('');
    }
  };

  const openRejectDialog = () => {
    if (!selectedRequest) return;
    if (!canReject) {
      setActionError('รายการนี้ไม่สามารถ reject ได้');
      return;
    }
    setRejectReason(editor.review_note.trim());
    setRejectDialogError('');
    setActionError('');
    setFlashMessage('');
    setRejectDialogOpen(true);
  };

  const closeRejectDialog = () => {
    if (busyAction === 'reject') return;
    setRejectDialogOpen(false);
    setRejectDialogError('');
  };

  const applyRejectReasonOption = (reason) => {
    setRejectReason((current) => {
      const trimmed = current.trim();
      if (!trimmed) return reason;
      if (trimmed.includes(reason)) return trimmed;
      return `${trimmed}\n${reason}`;
    });
    setRejectDialogError('');
  };

  const closeConfirmDialog = () => {
    if (confirmDialog?.busyAction && busyAction === confirmDialog.busyAction) return;
    setConfirmDialog(null);
  };

  const requestSummary = (request = selectedRequest) => [
    { label: 'Project', value: request?.project_name || '-' },
    { label: 'Vendor', value: request?.vendor_name || request?.requester_name || '-' },
    { label: 'Amount', value: formatDialogAmount(request?.approved_amount ?? request?.amount) },
    { label: 'Receipt No.', value: request?.receipt_no || '-' },
  ];

  const openSaveDialog = () => {
    if (!selectedRequest) return;
    setActionError('');
    setFlashMessage('');
    setConfirmDialog({
      type: 'save',
      busyAction: 'save',
      icon: Save,
      tone: hasFlowAccountDocument ? 'warning' : 'neutral',
      kicker: 'Save Changes',
      title: 'Confirm request changes',
      description: hasFlowAccountDocument
        ? 'This request is already linked to FlowAccount. Only safe metadata and payment reference changes should be saved.'
        : 'Review the current edits before saving them to this request.',
      confirmLabel: 'Confirm Save',
      busyLabel: 'Saving...',
      summary: requestSummary(),
    });
  };

  const openApproveDialog = () => {
    if (!selectedRequest) return;
    const approvedLineItems = normalizeLineItemsForSave(editor.line_items, selectedRequest);
    const approvedAmount = sumLineItems(approvedLineItems) || Number(editor.amount || selectedRequest.amount || 0);
    setActionError('');
    setFlashMessage('');
    setConfirmDialog({
      type: 'approve',
      busyAction: 'approve',
      icon: CheckCheck,
      tone: 'success',
      kicker: 'Approve Request',
      title: 'Confirm approval',
      description: 'This will move the request to APPROVED and make it ready for FlowAccount sync or payment.',
      confirmLabel: 'Confirm Approve',
      busyLabel: 'Approving...',
      summary: [
        ...requestSummary(),
        { label: 'Approved Amount', value: formatDialogAmount(approvedAmount) },
        { label: 'Line Items', value: `${approvedLineItems.length || 0}` },
      ],
    });
  };

  const openSyncFlowAccountDialog = () => {
    if (!selectedRequest) return;
    setActionError('');
    setFlashMessage('');
    setConfirmDialog({
      type: 'sync-flowaccount',
      busyAction: 'sync-flowaccount',
      icon: CircleDollarSign,
      tone: selectedRequest.is_duplicate_flag ? 'warning' : 'neutral',
      kicker: 'Sync FlowAccount',
      title: selectedRequest.is_duplicate_flag ? 'Confirm duplicate FlowAccount sync' : 'Confirm FlowAccount sync',
      description: selectedRequest.is_duplicate_flag
        ? 'This request is flagged as duplicate. Confirming will sync it to FlowAccount anyway.'
        : 'This will create or update the expense document and related accounting lifecycle in FlowAccount.',
      confirmLabel: 'Confirm Sync',
      busyLabel: 'Syncing...',
      summary: [
        ...requestSummary(),
        { label: 'External ID', value: selectedRequest.flowaccount_external_document_id || '-' },
        { label: 'Document', value: selectedRequest.flowaccount_document_no || selectedRequest.flowaccount_expense_id || 'Not linked yet' },
      ],
    });
  };

  const openMarkPaidDialog = () => {
    if (!selectedRequest) return;
    setActionError('');
    setFlashMessage('');
    setConfirmDialog({
      type: 'mark-paid',
      busyAction: 'mark-paid',
      icon: CircleDollarSign,
      tone: 'warning',
      kicker: 'Mark Paid',
      title: 'Confirm payment completion',
      description: 'Confirm that the payment has been completed. When FlowAccount is enabled, payment sync must succeed before this request becomes PAID.',
      confirmLabel: 'Confirm Paid',
      busyLabel: 'Marking paid...',
      summary: [
        ...requestSummary(),
        { label: 'Payment Reference', value: editor.payment_reference || '-' },
        { label: 'Payment Date', value: editor.payment_date || '-' },
      ],
    });
  };

  const handleConfirmDialogAction = async () => {
    if (!confirmDialog) return;
    const actionType = confirmDialog.type;
    if (actionType === 'save') {
      await handleSave();
    } else if (actionType === 'approve') {
      await handleApprove();
    } else if (actionType === 'sync-flowaccount') {
      await handleSyncFlowAccount(Boolean(selectedRequest?.is_duplicate_flag));
    } else if (actionType === 'mark-paid') {
      await handleMarkPaid();
    }
    setConfirmDialog(null);
  };

  const handleReject = async () => {
    if (!selectedRequest) return;
    const trimmedReason = rejectReason.trim();
    if (!trimmedReason) {
      setRejectDialogError('กรุณาระบุเหตุผลก่อน reject');
      return;
    }

    try {
      setBusyAction('reject');
      setActionError('');
      setRejectDialogError('');
      const rejected = await rejectAdminInputRequest(selectedRequest.request_id, {
        review_note: trimmedReason,
      });
      setRejectDialogOpen(false);
      if (matchesFilters(rejected, filters)) {
        replaceRequest(rejected);
        await refreshReceiptPreview(rejected);
      } else {
        await loadData({ keepSelection: false });
      }
      setFlashMessage('ปฏิเสธคำขอเรียบร้อย');
    } catch (error) {
      setActionError(error.message || 'Failed to reject request.');
    } finally {
      setBusyAction('');
    }
  };

  const handleMarkPaid = async () => {
    if (!selectedRequest) return;

    try {
      setBusyAction('mark-paid');
      setActionError('');
      const paid = await markPaidAdminInputRequest(selectedRequest.request_id, {
        payment_reference: editor.payment_reference.trim() || null,
        payment_date: editor.payment_date || null,
        review_note: editor.review_note.trim() || null,
      });
      if (matchesFilters(paid, filters)) {
        replaceRequest(paid);
        await refreshReceiptPreview(paid);
      } else {
        await loadData({ keepSelection: false });
      }
      setFlashMessage('อัปเดตสถานะเป็น PAID เรียบร้อย');
    } catch (error) {
      setActionError(error.message || 'Failed to mark request as paid.');
    } finally {
      setBusyAction('');
    }
  };

  const handleSyncFlowAccount = async (overrideDuplicate = false) => {
    if (!selectedRequest) return;

    try {
      setBusyAction('sync-flowaccount');
      setActionError('');
      const synced = await syncInputRequestFlowAccount(selectedRequest.request_id, {
        override_duplicate: overrideDuplicate,
        override_reason: overrideDuplicate ? 'Owner confirmed duplicate FlowAccount sync in Approval UI.' : null,
      });
      replaceRequest(synced);
      setFlashMessage('FlowAccount sync updated.');
    } catch (error) {
      setActionError(error.message || 'Failed to sync FlowAccount.');
    } finally {
      setBusyAction('');
    }
  };

  const handleRetryAttachment = async () => {
    if (!selectedRequest) return;
    try {
      setBusyAction('retry-attachment');
      setActionError('');
      const updated = await retryInputRequestFlowAccountAttachment(selectedRequest.request_id);
      replaceRequest(updated);
      setFlashMessage('FlowAccount attachment retry finished.');
    } catch (error) {
      setActionError(error.message || 'Failed to retry FlowAccount attachment.');
    } finally {
      setBusyAction('');
    }
  };

  const handleRetrySupplierInvoice = async () => {
    if (!selectedRequest) return;
    try {
      setBusyAction('retry-supplier-invoice');
      setActionError('');
      const updated = await retryInputRequestFlowAccountSupplierInvoice(selectedRequest.request_id);
      replaceRequest(updated);
      setFlashMessage('FlowAccount Supplier Invoice retry finished.');
    } catch (error) {
      setActionError(error.message || 'Failed to retry Supplier Invoice.');
    } finally {
      setBusyAction('');
    }
  };

  const handleLinkFlowAccountDocument = async () => {
    if (!selectedRequest) return;
    const expenseId = window.prompt('FlowAccount Expense recordId/documentId');
    if (!expenseId?.trim()) return;
    const documentNo = window.prompt('FlowAccount document number (optional)') || '';

    try {
      setBusyAction('link-flowaccount');
      setActionError('');
      const linked = await linkInputRequestFlowAccountDocument(selectedRequest.request_id, {
        expense_id: expenseId.trim(),
        document_no: documentNo.trim() || null,
        external_document_id: selectedRequest.flowaccount_external_document_id || null,
        note: editor.review_note.trim() || null,
      });
      replaceRequest(linked);
      setFlashMessage('Linked existing FlowAccount document.');
    } catch (error) {
      setActionError(error.message || 'Failed to link FlowAccount document.');
    } finally {
      setBusyAction('');
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

  const projectOptions = [{ project_id: '', name: 'ทุกโครงการ' }, ...projects];
  const canMutateApprovals = canMutateAdminData(getStoredAuthUser());
  const hasFlowAccountDocument = Boolean(selectedRequest?.flowaccount_expense_id);
  const canEdit = canMutateApprovals && selectedRequest ? isEditableStatus(selectedRequest.status) && !hasFlowAccountDocument : false;
  const canEditTaxFilingFields =
    canMutateApprovals &&
    selectedRequest &&
    selectedRequest.status === 'APPROVED' &&
    hasFlowAccountDocument &&
    selectedRequest.flowaccount_payment_status !== 'PAYMENT_SYNCED';
  const canSaveMetadata =
    canMutateApprovals &&
    selectedRequest &&
    isEditableStatus(selectedRequest.status) &&
    selectedRequest.flowaccount_payment_status !== 'PAYMENT_SYNCED';
  const canSaveChanges = canEdit || canSaveMetadata;
  const canApprove = canMutateApprovals && selectedRequest ? isReviewableStatus(selectedRequest.status) : false;
  const canReject = canApprove;
  const flowAccountEnabled = Boolean(accountingReadiness?.enabled);
  const canSyncFlowAccount =
    canMutateApprovals &&
    selectedRequest?.status === 'APPROVED' &&
    selectedRequest?.entry_type === 'EXPENSE' &&
    (accountingReadiness?.can_sync_expense || hasFlowAccountDocument);
  const canRetryAttachment =
    canMutateApprovals &&
    hasFlowAccountDocument &&
    selectedRequest?.flowaccount_attachment_status === 'FAILED';
  const canRetrySupplierInvoice =
    canMutateApprovals &&
    hasFlowAccountDocument &&
    selectedRequest?.accounting_vat_mode !== 'no_vat' &&
    selectedRequest?.flowaccount_supplier_invoice_status !== 'SYNCED' &&
    accountingReadiness?.can_sync_supplier_invoice;
  const canLinkFlowAccount =
    canMutateApprovals &&
    selectedRequest?.status === 'APPROVED' &&
    selectedRequest?.entry_type === 'EXPENSE' &&
    !hasFlowAccountDocument;
  const readinessIssues = [
    ...(accountingReadiness?.missing_fields || []),
    ...(accountingReadiness?.errors || []),
  ].map((item) => String(item || ''));
  const hasPaymentConfigBlocker = readinessIssues.some((item) =>
    item === 'FLOWACCOUNT_CLIENT_ID' ||
    item === 'FLOWACCOUNT_CLIENT_SECRET' ||
    item === 'FLOWACCOUNT_DEFAULT_PAYMENT_METHOD=transfer' ||
    item === 'FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID' ||
    item === 'FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID numeric value'
  );
  const hasDraftPaymentInputs = Boolean(cleanText(editor.payment_reference)) && Boolean(cleanText(editor.payment_date));
  const canMarkPaidWithDraftPayment =
    flowAccountEnabled &&
    Boolean(accountingReadiness) &&
    hasFlowAccountDocument &&
    hasDraftPaymentInputs &&
    !hasPaymentConfigBlocker;
  const canMarkPaid =
    canMutateApprovals &&
    selectedRequest?.status === 'APPROVED' &&
    (!flowAccountEnabled || accountingReadiness?.can_mark_paid || canMarkPaidWithDraftPayment);
  const inputVatNotReady =
    selectedRequest?.accounting_vat_mode &&
    selectedRequest.accounting_vat_mode !== 'no_vat' &&
    hasFlowAccountDocument &&
    selectedRequest?.flowaccount_supplier_invoice_status !== 'SYNCED' &&
    !accountingReadiness?.can_sync_supplier_invoice;
  const attachmentSandboxNote =
    selectedRequest?.flowaccount_attachment_status === 'SYNCED';
  const canPreviewReceipt = Boolean(receiptPreview?.signed_url);
  const isPreviewImage = (receiptPreview?.content_type || '').startsWith('image/');
  const isPreviewPdf = (receiptPreview?.content_type || '') === 'application/pdf';
  const isDeepLinkedRequest = Boolean(deepLinkRequestId) && selectedRequest?.request_id === deepLinkRequestId;
  const isPaidRequest = selectedRequest?.status === 'PAID';
  const flowAccountErrors = [
    selectedRequest?.flowaccount_sync_error,
    selectedRequest?.flowaccount_attachment_error,
    selectedRequest?.flowaccount_supplier_invoice_error,
    selectedRequest?.flowaccount_payment_error,
  ].filter(Boolean);
  const flowAccountStatusValues = [
    selectedRequest?.flowaccount_sync_status,
    selectedRequest?.flowaccount_attachment_status,
    selectedRequest?.flowaccount_supplier_invoice_status,
    selectedRequest?.flowaccount_payment_status,
  ].map((value) => String(value || '').trim().toUpperCase());
  const hasFlowAccountLifecycleState = flowAccountStatusValues.some((value) =>
    value && !['NOT_READY', 'READY'].includes(value)
  );
  const hasFlowAccountHistory = Boolean(
    hasFlowAccountDocument ||
    selectedRequest?.flowaccount_linked_manually ||
    flowAccountErrors.length ||
    hasFlowAccountLifecycleState
  );
  const shouldShowFlowAccountPanel = Boolean(
    selectedRequest?.entry_type === 'EXPENSE' &&
    (['APPROVED', 'PAID'].includes(selectedRequest?.status) || hasFlowAccountHistory)
  );
  const requestAlerts = selectedRequest ? [
    flashMessage ? {
      tone: 'success',
      title: 'Action completed',
      message: flashMessage,
    } : null,
    actionError ? {
      tone: 'critical',
      title: 'Action failed',
      message: actionError,
    } : null,
    selectedRequest.is_duplicate_flag ? {
      tone: 'warning',
      title: 'Duplicate red flag',
      message: selectedRequest.duplicate_reason || 'พบรายการซ้ำตามกฎ Receipt No. + Date + Amount',
    } : null,
    selectedRequest.ocr_low_confidence_fields?.length ? {
      tone: 'warning',
      title: 'OCR low confidence',
      message: selectedRequest.ocr_low_confidence_fields.map(formatOcrFieldLabel).join(', '),
    } : null,
    shouldShowFlowAccountPanel && readinessIssues.length ? {
      tone: accountingReadiness?.errors?.length ? 'critical' : 'warning',
      title: 'Accounting readiness',
      message: readinessIssues.join(' | '),
    } : null,
    shouldShowFlowAccountPanel && inputVatNotReady ? {
      tone: 'warning',
      title: 'Input VAT not ready',
      message: 'Expense can stay synced. Supplier Invoice needs vendor tax ID, branch, address, and receipt number.',
    } : null,
    shouldShowFlowAccountPanel && attachmentSandboxNote ? {
      tone: 'info',
      title: 'Attachment synced',
      message: 'Receipt was uploaded to FlowAccount. Sandbox preview can still fail even when upload succeeded.',
    } : null,
    shouldShowFlowAccountPanel && flowAccountErrors.length ? {
      tone: 'critical',
      title: 'FlowAccount error',
      message: flowAccountErrors.join(' | '),
    } : null,
    receiptPreviewError ? {
      tone: 'warning',
      title: 'Receipt preview issue',
      message: receiptPreviewError,
    } : null,
    !selectedRequest.receipt_storage_key ? {
      tone: 'info',
      title: 'No receipt file',
      message: 'รายการนี้ยังไม่มีไฟล์ receipt ที่เก็บไว้',
    } : null,
    !canMutateApprovals ? {
      tone: 'info',
      title: 'Read-only access',
      message: 'Owner permission is required to edit, approve, reject, or mark requests as paid.',
    } : null,
  ].filter(Boolean) : [];
  const flowAccountSteps = selectedRequest ? [
    {
      label: 'Expense document',
      status: selectedRequest.flowaccount_sync_status || (selectedRequest.flowaccount_expense_id ? 'SYNCED' : 'NOT_READY'),
      detail: selectedRequest.flowaccount_document_no || selectedRequest.flowaccount_expense_id || 'No FlowAccount document linked',
    },
    {
      label: 'Receipt attachment',
      status: selectedRequest.flowaccount_attachment_status || 'NOT_READY',
      detail: selectedRequest.receipt_file_name || 'No receipt file',
    },
    {
      label: 'Supplier invoice',
      status: selectedRequest.flowaccount_supplier_invoice_status || 'NOT_READY',
      detail: selectedRequest.accounting_vat_mode || 'VAT mode not selected',
    },
    {
      label: 'Payment',
      status: selectedRequest.flowaccount_payment_status || 'NOT_READY',
      detail: selectedRequest.payment_reference || 'Payment reference not recorded',
    },
  ] : [];
  const flowAccountMessages = shouldShowFlowAccountPanel ? [
    !flowAccountEnabled ? {
      tone: 'info',
      text: 'FlowAccount integration is disabled in backend config.',
    } : null,
    !isPaidRequest && readinessIssues.length ? {
      tone: accountingReadiness?.errors?.length ? 'critical' : 'warning',
      text: readinessIssues.join(' | '),
    } : null,
    !isPaidRequest && inputVatNotReady ? {
      tone: 'warning',
      text: 'Input VAT / Supplier Invoice is blocked until tax fields and receipt number are complete.',
    } : null,
    !isPaidRequest && attachmentSandboxNote ? {
      tone: 'info',
      text: 'Attachment upload succeeded. FlowAccount sandbox preview may still fail.',
    } : null,
    flowAccountErrors.length ? {
      tone: 'critical',
      text: flowAccountErrors.join(' | '),
    } : null,
  ].filter(Boolean) : [];
  const paidFlowAccountActions = [
    canRetryAttachment ? {
      label: 'Retry Attachment',
      onClick: handleRetryAttachment,
      disabled: !!busyAction,
      disabledReason: 'Only failed FlowAccount attachments can be retried.',
    } : null,
    canRetrySupplierInvoice ? {
      label: selectedRequest?.flowaccount_supplier_invoice_status === 'FAILED' ? 'Retry Supplier Invoice' : 'Sync Supplier Invoice',
      onClick: handleRetrySupplierInvoice,
      disabled: !!busyAction,
      disabledReason: 'Supplier Invoice sync needs VAT details and a linked expense document.',
    } : null,
  ].filter(Boolean);
  const reviewFlowAccountActions = [
    {
      label: busyAction === 'sync-flowaccount' ? 'Syncing...' : 'Sync FlowAccount',
      onClick: openSyncFlowAccountDialog,
      disabled: !!busyAction || !canSyncFlowAccount,
      disabledReason: 'Available for approved expense requests that are ready to sync.',
      variant: 'primary',
    },
    {
      label: 'Retry Attachment',
      onClick: handleRetryAttachment,
      disabled: !!busyAction || !canRetryAttachment,
      disabledReason: 'Only failed FlowAccount attachments can be retried.',
    },
    {
      label: selectedRequest?.flowaccount_supplier_invoice_status === 'FAILED' ? 'Retry Supplier Invoice' : 'Sync Supplier Invoice',
      onClick: handleRetrySupplierInvoice,
      disabled: !!busyAction || !canRetrySupplierInvoice,
      disabledReason: 'Supplier Invoice sync needs VAT details and a linked expense document.',
    },
    {
      label: 'Link Existing',
      onClick: handleLinkFlowAccountDocument,
      disabled: !!busyAction || !canLinkFlowAccount,
      disabledReason: 'Available for approved expense requests without a FlowAccount document.',
    },
  ];
  const flowAccountActions = canMutateApprovals && selectedRequest && shouldShowFlowAccountPanel
    ? (isPaidRequest ? paidFlowAccountActions : reviewFlowAccountActions)
    : [];
  const flowAccountPanelReady = isPaidRequest
    ? selectedRequest?.flowaccount_payment_status === 'PAYMENT_SYNCED'
    : Boolean(accountingReadiness?.ready);
  const flowAccountPanelTitle = isPaidRequest ? 'Paid sync summary' : undefined;
  const flowAccountPanelStatusLabel = isPaidRequest
    ? (selectedRequest?.flowaccount_payment_status === 'PAYMENT_SYNCED' ? 'PAID' : 'CHECK')
    : undefined;
  const shouldShowFieldRequirements = Boolean(selectedRequest && selectedRequest.status !== 'PAID');
  const isExpenseRequest = selectedRequest?.entry_type === 'EXPENSE';
  const vatModeForRequirements = editor.accounting_vat_mode || selectedRequest?.accounting_vat_mode || '';
  const needsVatFields =
    shouldShowFieldRequirements &&
    isExpenseRequest &&
    ['vat_inclusive', 'vat_exclusive'].includes(vatModeForRequirements);
  const whtRateText = cleanText(editor.accounting_wht_rate);
  const whtRateNumber = Number(whtRateText || 0);
  const hasNumericWhtRate = Number.isFinite(whtRateNumber);
  const needsWhtFields =
    shouldShowFieldRequirements &&
    isExpenseRequest &&
    (editor.request_type === 'ค่าแรง' || (whtRateText && hasNumericWhtRate && whtRateNumber > 0));
  const needsTaxFields = needsVatFields || needsWhtFields;
  const needsPaymentFields =
    shouldShowFieldRequirements &&
    selectedRequest?.status === 'APPROVED' &&
    hasFlowAccountDocument;
  const taxFieldHint = needsVatFields && needsWhtFields
    ? 'จำเป็นสำหรับ VAT และหัก ณ ที่จ่าย'
    : needsVatFields
      ? 'จำเป็นสำหรับ Supplier Invoice'
      : needsWhtFields
        ? 'จำเป็นสำหรับหัก ณ ที่จ่าย'
        : '';
  const isMissing = (value) => !cleanText(value);
  const requiredField = (required, value, hint) => ({
    required: Boolean(required),
    hint: required ? hint : '',
    error: required && isMissing(value) ? 'กรุณากรอกข้อมูลนี้' : '',
  });
  const taxIdText = cleanText(editor.vendor_tax_id);
  const whtRateError = (() => {
    if (!shouldShowFieldRequirements || !whtRateText) return '';
    if (!hasNumericWhtRate || whtRateNumber < 0 || whtRateNumber >= 100) {
      return 'อัตราหัก ณ ที่จ่ายต้องอยู่ระหว่าง 0-99';
    }
    if (!Number.isInteger(whtRateNumber)) {
      return 'FlowAccount รับค่า WHT เป็นเลขเต็ม เช่น 0 หรือ 3';
    }
    return '';
  })();
  const approvalFieldRequirements = {
    requesterName: requiredField(shouldShowFieldRequirements, editor.requester_name, 'จำเป็นสำหรับคำขอ'),
    requestDate: requiredField(shouldShowFieldRequirements, editor.request_date, 'จำเป็นสำหรับคำขอ'),
    approvedAmount: {
      required: shouldShowFieldRequirements,
      hint: shouldShowFieldRequirements ? 'ยอดรวมต้องมากกว่า 0' : '',
      error: shouldShowFieldRequirements && Number(editor.amount || 0) <= 0 ? 'ยอดเงินต้องมากกว่า 0' : '',
    },
    requestType: requiredField(
      shouldShowFieldRequirements && isExpenseRequest,
      editor.request_type,
      'จำเป็นสำหรับการ map บัญชี'
    ),
    vendorName: requiredField(
      shouldShowFieldRequirements && isExpenseRequest,
      editor.vendor_name,
      'จำเป็นสำหรับ FlowAccount'
    ),
    receiptNo: requiredField(needsVatFields, editor.receipt_no, 'จำเป็นเมื่อมี VAT'),
    documentDate: requiredField(
      shouldShowFieldRequirements && isExpenseRequest,
      editor.document_date,
      'วันที่บนเอกสาร'
    ),
    vatMode: requiredField(
      shouldShowFieldRequirements && isExpenseRequest,
      editor.accounting_vat_mode,
      'เลือกก่อน sync'
    ),
    vendorTaxId: {
      required: needsTaxFields,
      hint: needsTaxFields ? taxFieldHint : '',
      error: needsTaxFields && isMissing(editor.vendor_tax_id)
        ? 'กรุณากรอกเลขผู้เสียภาษี 13 หลัก'
        : taxIdText && taxIdText.length !== 13
          ? 'เลขผู้เสียภาษีต้องมี 13 หลัก'
          : '',
    },
    vendorBranch: requiredField(needsTaxFields, editor.vendor_branch, taxFieldHint),
    vendorAddress: requiredField(needsTaxFields, editor.vendor_address, taxFieldHint),
    whtRate: {
      required: needsWhtFields,
      hint: needsWhtFields ? 'ต้องเป็นเลขเต็ม เช่น 0 หรือ 3' : 'ถ้าไม่หัก ณ ที่จ่ายให้ใส่ 0',
      error: needsWhtFields && isMissing(editor.accounting_wht_rate)
        ? 'กรุณากรอกอัตราหัก ณ ที่จ่าย'
        : whtRateError,
    },
    paymentReference: requiredField(needsPaymentFields, editor.payment_reference, 'จำเป็นก่อน Mark Paid'),
    paymentDate: requiredField(needsPaymentFields && flowAccountEnabled, editor.payment_date, 'จำเป็นก่อน Mark Paid'),
  };
  const primaryActions = [
    {
      label: busyAction === 'save' ? 'Saving...' : 'Save Changes',
      onClick: openSaveDialog,
      disabled: !!busyAction || !canSaveChanges,
      disabledReason: 'No editable fields are available for this request status.',
      icon: approvalActionIcons.save,
    },
    {
      label: busyAction === 'approve' ? 'Approving...' : 'Approve',
      onClick: openApproveDialog,
      disabled: !!busyAction || !canApprove,
      disabledReason: 'Only draft, pending, or rejected requests can be approved.',
      icon: approvalActionIcons.approve,
      variant: 'success',
    },
    {
      label: busyAction === 'reject' ? 'Rejecting...' : 'Reject',
      onClick: openRejectDialog,
      disabled: !!busyAction || !canReject,
      disabledReason: 'Only draft, pending, or rejected requests can be rejected.',
      icon: approvalActionIcons.reject,
      variant: 'danger',
    },
    {
      label: busyAction === 'mark-paid' ? 'Marking Paid...' : 'Mark Paid',
      onClick: openMarkPaidDialog,
      disabled: !!busyAction || !canMarkPaid,
      disabledReason: 'Payment can be marked after approval and payment details are ready.',
      icon: approvalActionIcons.paid,
      variant: 'primary',
    },
  ];
  const ConfirmIcon = confirmDialog?.icon || Save;
  const confirmDialogBusy = Boolean(confirmDialog?.busyAction && busyAction === confirmDialog.busyAction);

  return (
    <>
      <ApprovalSummaryStrip
        requests={requests}
        refreshing={refreshing}
        isDeepLinkedRequest={isDeepLinkedRequest}
        deepLinkRequestId={deepLinkRequestId}
      />

      <div className="approval-workspace-grid">
        <ApprovalQueuePanel
          filters={filters}
          onFilterChange={setFilters}
          statusOptions={STATUS_OPTIONS}
          entryTypeOptions={ENTRY_TYPE_OPTIONS}
          projectOptions={projectOptions}
          requests={requests}
          selectedRequestId={selectedRequestId}
          onSelectRequest={setSelectedRequestId}
          formatEntryType={formatEntryType}
        />

        <div className="approval-review-panel">
          {!selectedRequest ? (
            <div style={{ color: '#666' }}>เลือกรายการจากคิวด้านซ้ายเพื่อเริ่ม review</div>
          ) : (
            <>
              <ApprovalRequestHeader
                request={selectedRequest}
                formatEntryType={formatEntryType}
                alertCount={requestAlerts.length}
              />

              <div className="approval-review-layout">
                <div className="approval-review-main">
                  <ApprovalAlertStack alerts={requestAlerts} />

                  {shouldShowFlowAccountPanel ? (
                    <ApprovalFlowAccountChecklist
                      enabled={flowAccountEnabled}
                      ready={flowAccountPanelReady}
                      steps={flowAccountSteps}
                      messages={flowAccountMessages}
                      actions={flowAccountActions}
                      compact={isPaidRequest}
                      title={flowAccountPanelTitle}
                      statusLabel={flowAccountPanelStatusLabel}
                    />
                  ) : null}

              {selectedRequest.ocr_raw_json ? (
                <div
                  style={{
                    border: '1px solid #e7decd',
                    borderRadius: '16px',
                    backgroundColor: '#faf7f1',
                    overflow: 'hidden',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setTechnicalDetailsOpen((current) => !current)}
                    style={{
                      width: '100%',
                      border: 'none',
                      background: 'transparent',
                      padding: '14px 16px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <strong style={{ display: 'block' }}>Technical details</strong>
                      <span style={{ fontSize: '12px', color: '#6b7280' }}>
                        ข้อมูล OCR debug สำหรับเปิดดูเมื่อจำเป็น
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: '#8b7355' }}>
                      {technicalDetailsOpen ? 'Hide' : 'Show'}
                    </span>
                  </button>

                  {technicalDetailsOpen ? (
                    <div
                      style={{
                        borderTop: '1px solid #e7decd',
                        padding: '14px 16px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                      }}
                    >
                      <strong style={{ display: 'block', fontSize: '13px' }}>OCR Debug JSON</strong>
                      <pre
                        style={{
                          margin: 0,
                          padding: '14px 16px',
                          borderRadius: '14px',
                          backgroundColor: '#1f1f1f',
                          color: '#f5f5f5',
                          overflowX: 'auto',
                          fontSize: '12px',
                          lineHeight: 1.6,
                        }}
                      >
                        {JSON.stringify(selectedRequest.ocr_raw_json, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                </div>
              ) : null}

                  <ApprovalFormSection title="Request details" description="Core request metadata used for review and approval.">
                    <div className="approval-form-grid">
                      <ApprovalField label="ผู้ขอ" {...approvalFieldRequirements.requesterName}>
                        <input className="approval-input" value={editor.requester_name} onChange={handleEditorChange('requester_name')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="เบอร์โทร">
                        <input className="approval-input" value={editor.phone} onChange={handleEditorChange('phone')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="วันที่ขอ" {...approvalFieldRequirements.requestDate}>
                        <input className="approval-input" type="date" value={editor.request_date} onChange={handleEditorChange('request_date')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="ยอดอนุมัติ" {...approvalFieldRequirements.approvedAmount}>
                        <input className="approval-input amount" type="number" value={editor.amount} onChange={handleEditorChange('amount')} disabled />
                      </ApprovalField>
                      <ApprovalField label="ประเภทงาน">
                        <select className="approval-input" value={editor.work_type} onChange={handleEditorChange('work_type')} disabled={!canEdit}>
                          {WORK_TYPE_OPTIONS.map((option) => (
                            <option key={option.value || 'empty-work'} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </ApprovalField>
                      <ApprovalField label="ประเภทรายการ" {...approvalFieldRequirements.requestType}>
                        <select className="approval-input" value={editor.request_type} onChange={handleEditorChange('request_type')} disabled={!canEdit}>
                          {REQUEST_TYPE_OPTIONS.map((option) => (
                            <option key={option.value || 'empty-request'} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </ApprovalField>
                    </div>
                  </ApprovalFormSection>

                  <ApprovalFormSection title="Vendor, tax, and payment" description="Fields that affect accounting readiness and payment execution.">
                    <div className="approval-form-grid">
                      <ApprovalField label="ผู้ขาย / ร้านค้า" {...approvalFieldRequirements.vendorName}>
                        <input className="approval-input" value={editor.vendor_name} onChange={handleEditorChange('vendor_name')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="เลขที่ใบเสร็จ" {...approvalFieldRequirements.receiptNo}>
                        <input className="approval-input" value={editor.receipt_no} onChange={handleEditorChange('receipt_no')} disabled={!canEdit && !canEditTaxFilingFields} />
                      </ApprovalField>
                      <ApprovalField label="วันที่เอกสาร" {...approvalFieldRequirements.documentDate}>
                        <input className="approval-input" type="date" value={editor.document_date} onChange={handleEditorChange('document_date')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="รูปแบบ VAT" {...approvalFieldRequirements.vatMode}>
                        <select className="approval-input" value={editor.accounting_vat_mode} onChange={handleEditorChange('accounting_vat_mode')} disabled={!canEdit}>
                          {VAT_MODE_OPTIONS.map((option) => (
                            <option key={option.value || 'empty-vat'} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </ApprovalField>
                      <ApprovalField label="เลขผู้เสียภาษี" {...approvalFieldRequirements.vendorTaxId}>
                        <input className="approval-input" value={editor.vendor_tax_id} onChange={handleEditorChange('vendor_tax_id')} disabled={!canEdit && !canEditTaxFilingFields} />
                      </ApprovalField>
                      <ApprovalField label="สาขาผู้ขาย" {...approvalFieldRequirements.vendorBranch}>
                        <input className="approval-input" value={editor.vendor_branch} onChange={handleEditorChange('vendor_branch')} disabled={!canEdit && !canEditTaxFilingFields} placeholder="สำนักงานใหญ่ / 00000" />
                      </ApprovalField>
                      <ApprovalField label="ที่อยู่ผู้ขาย" wide {...approvalFieldRequirements.vendorAddress}>
                        <input className="approval-input" value={editor.vendor_address} onChange={handleEditorChange('vendor_address')} disabled={!canEdit && !canEditTaxFilingFields} />
                      </ApprovalField>
                      <ApprovalField label="หัก ณ ที่จ่าย (%)" {...approvalFieldRequirements.whtRate}>
                        <input className="approval-input amount" type="number" min="0" max="100" step="0.01" value={editor.accounting_wht_rate} onChange={handleEditorChange('accounting_wht_rate')} disabled={!canEdit} />
                      </ApprovalField>
                      <ApprovalField label="เลขอ้างอิงการจ่าย" {...approvalFieldRequirements.paymentReference}>
                        <input className="approval-input" value={editor.payment_reference} onChange={handleEditorChange('payment_reference')} disabled={!canSaveMetadata} />
                      </ApprovalField>
                      <ApprovalField label="วันที่จ่าย" {...approvalFieldRequirements.paymentDate}>
                        <input className="approval-input" type="date" value={editor.payment_date} onChange={handleEditorChange('payment_date')} disabled={!canMutateApprovals} />
                      </ApprovalField>
                    </div>
                  </ApprovalFormSection>

                  <ApprovalFormSection title="Line items" description="แก้ไขรายการจาก OCR ก่อนบันทึกหรืออนุมัติ">
                    <InputLineItemsEditor
                      value={editor.line_items}
                      onChange={handleEditorLineItemsChange}
                      disabled={!canEdit}
                      entryType={selectedRequest.entry_type}
                      workTypeOptions={WORK_TYPE_OPTIONS.filter((option) => option.value)}
                      requestTypeOptions={REQUEST_TYPE_OPTIONS.filter((option) => option.value)}
                      fallbackWorkType={editor.work_type}
                      fallbackRequestType={editor.request_type}
                      title="Line Items"
                    />
                  </ApprovalFormSection>

                  <ApprovalFormSection title="Notes">
                    <div className="approval-form-grid single">
                      <ApprovalField label="หมายเหตุจากผู้ส่ง" wide>
                        <textarea
                          className="approval-input textarea"
                          rows={4}
                          value={editor.note}
                          onChange={handleEditorChange('note')}
                          disabled={!canEdit}
                        />
                      </ApprovalField>
                      <ApprovalField label="หมายเหตุการตรวจ" wide>
                        <textarea
                          className="approval-input textarea compact"
                          rows={3}
                          value={editor.review_note}
                          onChange={handleEditorChange('review_note')}
                          disabled={!canSaveMetadata}
                        />
                      </ApprovalField>
                    </div>
                  </ApprovalFormSection>

                  <ApprovalActionBar canMutate={canMutateApprovals} actions={primaryActions} />
                </div>

                <ApprovalEvidencePanel
                  request={selectedRequest}
                  editor={editor}
                  onFieldChange={handleEditorChange}
                  canEdit={canEdit}
                  receiptPreview={receiptPreview}
                  receiptPreviewLoading={receiptPreviewLoading}
                  receiptPreviewError={receiptPreviewError}
                  canPreviewReceipt={canPreviewReceipt}
                  isPreviewImage={isPreviewImage}
                  isPreviewPdf={isPreviewPdf}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {confirmDialog && selectedRequest ? (
        <div className="approval-reject-scrim" onMouseDown={closeConfirmDialog}>
          <section
            className={`approval-confirm-dialog ${confirmDialog.tone || 'neutral'}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="approval-confirm-title"
            aria-describedby="approval-confirm-description"
            onMouseDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === 'Escape') closeConfirmDialog();
            }}
          >
            <header className="approval-reject-header">
              <div>
                <span className="approval-confirm-kicker">
                  <ConfirmIcon size={15} />
                  {confirmDialog.kicker}
                </span>
                <h3 id="approval-confirm-title">{confirmDialog.title}</h3>
                <p id="approval-confirm-description">{confirmDialog.description}</p>
              </div>
              <button
                type="button"
                className="approval-reject-close"
                onClick={closeConfirmDialog}
                disabled={confirmDialogBusy}
                aria-label="Close confirmation dialog"
              >
                <X size={18} />
              </button>
            </header>

            <div className="approval-reject-summary approval-confirm-summary">
              {(confirmDialog.summary || []).map((item) => (
                <div key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value || '-'}</strong>
                </div>
              ))}
            </div>

            <footer className="approval-reject-actions">
              <button
                type="button"
                className="approval-reject-secondary"
                onClick={closeConfirmDialog}
                disabled={confirmDialogBusy}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`approval-confirm-primary ${confirmDialog.tone || 'neutral'}`}
                onClick={handleConfirmDialogAction}
                disabled={confirmDialogBusy}
              >
                <ConfirmIcon size={16} />
                {confirmDialogBusy ? confirmDialog.busyLabel : confirmDialog.confirmLabel}
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {rejectDialogOpen && selectedRequest ? (
        <div className="approval-reject-scrim" onMouseDown={closeRejectDialog}>
          <section
            className="approval-reject-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="approval-reject-title"
            aria-describedby="approval-reject-description"
            onMouseDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === 'Escape') closeRejectDialog();
            }}
          >
            <header className="approval-reject-header">
              <div>
                <span className="approval-reject-kicker">
                  <OctagonX size={15} />
                  Reject Request
                </span>
                <h3 id="approval-reject-title">ระบุเหตุผลการปฏิเสธ</h3>
                <p id="approval-reject-description">
                  เหตุผลนี้จะถูกบันทึกเป็น Review Note และแสดงในประวัติของคำขอ
                </p>
              </div>
              <button
                type="button"
                className="approval-reject-close"
                onClick={closeRejectDialog}
                disabled={busyAction === 'reject'}
                aria-label="Close reject dialog"
              >
                <X size={18} />
              </button>
            </header>

            <div className="approval-reject-summary">
              <div>
                <span>Project</span>
                <strong>{selectedRequest.project_name || '-'}</strong>
              </div>
              <div>
                <span>Vendor</span>
                <strong>{selectedRequest.vendor_name || '-'}</strong>
              </div>
              <div>
                <span>Amount</span>
                <strong>{Number(selectedRequest.approved_amount ?? selectedRequest.amount ?? 0).toLocaleString()} THB</strong>
              </div>
              <div>
                <span>Receipt No.</span>
                <strong>{selectedRequest.receipt_no || '-'}</strong>
              </div>
            </div>

            <div className="approval-reject-reasons" aria-label="Quick reject reasons">
              {REJECT_REASON_OPTIONS.map((reason) => (
                <button
                  type="button"
                  key={reason}
                  onClick={() => applyRejectReasonOption(reason)}
                  disabled={busyAction === 'reject'}
                >
                  {reason}
                </button>
              ))}
            </div>

            <label className="approval-reject-field">
              <span>เหตุผลการปฏิเสธ</span>
              <textarea
                rows={5}
                value={rejectReason}
                onChange={(event) => {
                  setRejectReason(event.target.value);
                  setRejectDialogError('');
                }}
                placeholder="เช่น ยอดเงินในใบเสร็จไม่ตรงกับยอดที่ขอเบิก กรุณาแก้ไขและส่งใหม่"
                disabled={busyAction === 'reject'}
                autoFocus
              />
            </label>

            {rejectDialogError ? (
              <div className="approval-reject-error">{rejectDialogError}</div>
            ) : null}

            <footer className="approval-reject-actions">
              <button
                type="button"
                className="approval-reject-secondary"
                onClick={closeRejectDialog}
                disabled={busyAction === 'reject'}
              >
                Cancel
              </button>
              <button
                type="button"
                className="approval-reject-primary"
                onClick={handleReject}
                disabled={busyAction === 'reject' || !rejectReason.trim()}
              >
                <OctagonX size={16} />
                {busyAction === 'reject' ? 'Rejecting...' : 'Confirm Reject'}
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </>
  );
}

export default ApprovalPage;
