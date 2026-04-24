import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CheckCheck, CircleDollarSign, ExternalLink, Filter, LoaderCircle, OctagonX, Save, TriangleAlert } from 'lucide-react';
import Loading from './components/Loading';
import {
  approveAdminInputRequest,
  getAdminInputReceiptUrl,
  getAdminInputRequests,
  getInputProjectOptions,
  markPaidAdminInputRequest,
  rejectAdminInputRequest,
  updateAdminInputRequest,
} from './api';

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

const WORK_TYPE_OPTIONS = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'งานโครงสร้าง', label: 'งานโครงสร้าง' },
  { value: 'งานสถาปัตย์', label: 'งานสถาปัตย์' },
  { value: 'งานระบบ', label: 'งานระบบ' },
  { value: 'งานบริหารโครงการ', label: 'งานบริหารโครงการ' },
];

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: '12px',
  border: '1px solid #d8cfbf',
  backgroundColor: '#faf7f1',
  fontSize: '14px',
  outline: 'none',
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
  receipt_no: '',
  amount: '',
  review_note: '',
  payment_reference: '',
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
const matchesFilters = (item, filters) =>
  (!filters.status || item.status === filters.status) &&
  (!filters.entryType || item.entry_type === filters.entryType) &&
  (!filters.projectId || item.project_id === filters.projectId);

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

    setEditor({
      requester_name: request.requester_name || '',
      phone: request.phone || '',
      request_date: request.request_date || '',
      document_date: request.document_date || '',
      work_type: request.work_type || '',
      request_type: request.request_type || '',
      note: request.note || '',
      vendor_name: request.vendor_name || '',
      receipt_no: request.receipt_no || '',
      amount: request.approved_amount ?? request.amount ?? '',
      review_note: request.review_note || '',
      payment_reference: request.payment_reference || '',
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

  const replaceRequest = (nextItem) => {
    setRequests((current) => current.map((item) => (item.request_id === nextItem.request_id ? nextItem : item)));
    setSelectedRequestId(nextItem.request_id);
    syncEditorWithRequest(nextItem);
  };

  const handleSave = async () => {
    if (!selectedRequest) return;

    try {
      setBusyAction('save');
      setActionError('');
      const updated = await updateAdminInputRequest(selectedRequest.request_id, {
        requester_name: editor.requester_name.trim(),
        phone: editor.phone.trim() || null,
        request_date: editor.request_date,
        document_date: editor.document_date || null,
        work_type: editor.work_type || null,
        request_type: editor.request_type || null,
        note: editor.note.trim() || null,
        vendor_name: editor.vendor_name.trim() || null,
        receipt_no: editor.receipt_no.trim() || null,
        amount: Number(editor.amount),
      });
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

    try {
      setBusyAction('approve');
      setActionError('');
      const approved = await approveAdminInputRequest(selectedRequest.request_id, {
        approved_amount: Number(editor.amount),
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

  const handleReject = async () => {
    if (!selectedRequest) return;
    if (!editor.review_note.trim()) {
      setActionError('กรุณาระบุเหตุผลก่อน reject');
      return;
    }

    try {
      setBusyAction('reject');
      setActionError('');
      const rejected = await rejectAdminInputRequest(selectedRequest.request_id, {
        review_note: editor.review_note.trim(),
      });
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

  if (loading) return <Loading />;

  if (pageError) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {pageError}
      </div>
    );
  }

  const projectOptions = [{ project_id: '', name: 'ทุกโครงการ' }, ...projects];
  const canEdit = selectedRequest ? isReviewableStatus(selectedRequest.status) : false;
  const canApprove = canEdit;
  const canReject = canEdit;
  const canMarkPaid = selectedRequest?.status === 'APPROVED';
  const canPreviewReceipt = Boolean(receiptPreview?.signed_url);
  const isPreviewImage = (receiptPreview?.content_type || '').startsWith('image/');
  const isPreviewPdf = (receiptPreview?.content_type || '') === 'application/pdf';
  const isDeepLinkedRequest = Boolean(deepLinkRequestId) && selectedRequest?.request_id === deepLinkRequestId;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '24px' }}>
        <div>
          <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Approval</h1>
          <p style={{ color: '#666', fontWeight: '500' }}>
            ตรวจสอบ แก้ไข และอนุมัติคำขอจากหน้า Input ตาม admin review flow
          </p>
          {isDeepLinkedRequest ? (
            <div style={{ marginTop: '10px', color: '#166534', backgroundColor: '#ecfdf5', border: '1px solid #86efac', borderRadius: '12px', padding: '10px 12px', fontSize: '13px', fontWeight: '600' }}>
              Focused from Insight Warehouse: request {deepLinkRequestId}
            </div>
          ) : null}
        </div>
        {refreshing ? (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: '#666' }}>
            <LoaderCircle size={16} />
            <span>Refreshing...</span>
          </div>
        ) : null}
      </div>

      <div className="chart-section" style={{ gridTemplateColumns: '1.05fr 1.35fr' }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Filter size={18} />
            <h2 style={{ fontSize: '18px' }}>Review Queue</h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
            <select
              value={filters.status}
              onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
              style={inputStyle}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <select
              value={filters.entryType}
              onChange={(event) => setFilters((current) => ({ ...current, entryType: event.target.value }))}
              style={inputStyle}
            >
              {ENTRY_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <select
              value={filters.projectId}
              onChange={(event) => setFilters((current) => ({ ...current, projectId: event.target.value }))}
              style={inputStyle}
            >
              {projectOptions.map((option) => (
                <option key={option.project_id || 'all-projects'} value={option.project_id}>
                  {option.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '620px', overflowY: 'auto' }}>
            {requests.length === 0 ? (
              <div style={{ color: '#666', padding: '24px 8px' }}>ไม่พบรายการในคิวตาม filter ปัจจุบัน</div>
            ) : (
              requests.map((item) => {
                const isActive = item.request_id === selectedRequestId;
                return (
                  <button
                    key={item.request_id}
                    type="button"
                    onClick={() => setSelectedRequestId(item.request_id)}
                    style={{
                      textAlign: 'left',
                      border: `1px solid ${isActive ? '#c4a470' : '#e7decd'}`,
                      backgroundColor: isActive ? '#fcf6ea' : 'white',
                      borderRadius: '16px',
                      padding: '14px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                      <strong>{item.project_name}</strong>
                      <span style={{ color: '#666' }}>{formatEntryType(item.entry_type)}</span>
                    </div>
                    <div style={{ color: '#555' }}>{item.requester_name}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', color: '#777', fontSize: '13px' }}>
                      <span>{item.request_type || 'ไม่ระบุประเภท'}</span>
                      <span>{Number(item.approved_amount ?? item.amount ?? 0).toLocaleString()} THB</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                      <div style={{ color: '#9a8b73', fontSize: '12px' }}>{item.status}</div>
                      {item.is_duplicate_flag ? (
                        <div style={{ color: '#8b5a00', backgroundColor: '#fff4de', borderRadius: '999px', padding: '4px 8px', fontSize: '11px', fontWeight: '700' }}>
                          DUPLICATE FLAG
                        </div>
                      ) : null}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {!selectedRequest ? (
            <div style={{ color: '#666' }}>เลือกรายการจากคิวด้านซ้ายเพื่อเริ่ม review</div>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start' }}>
                <div>
                  <h2 style={{ fontSize: '22px', marginBottom: '6px' }}>{selectedRequest.project_name}</h2>
                  <div style={{ color: '#666', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    <span>{formatEntryType(selectedRequest.entry_type)}</span>
                    <span>{selectedRequest.status}</span>
                    <span>{selectedRequest.request_date}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right', color: '#666' }}>
                  <div style={{ fontSize: '12px', marginBottom: '4px' }}>Request ID</div>
                  <div style={{ fontSize: '13px' }}>{selectedRequest.request_id}</div>
                </div>
              </div>

              {flashMessage ? (
                <div style={{ color: '#13654b', backgroundColor: '#e6f5ec', border: '1px solid #27a57a', borderRadius: '12px', padding: '10px 12px' }}>
                  {flashMessage}
                </div>
              ) : null}

              {actionError ? (
                <div style={{ color: '#912018', backgroundColor: '#fde8e8', border: '1px solid #de5b52', borderRadius: '12px', padding: '10px 12px' }}>
                  {actionError}
                </div>
              ) : null}

              {selectedRequest.is_duplicate_flag ? (
                <div style={{ color: '#8b5a00', backgroundColor: '#fff4de', border: '1px solid #c98c1c', borderRadius: '12px', padding: '12px 14px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <TriangleAlert size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
                  <div>
                    <strong style={{ display: 'block', marginBottom: '4px' }}>Duplicate Red Flag</strong>
                    <span>{selectedRequest.duplicate_reason || 'พบรายการซ้ำตามกฎ Receipt No. + Date + Amount'}</span>
                  </div>
                </div>
              ) : null}

              {selectedRequest.ocr_low_confidence_fields?.length ? (
                <div style={{ color: '#8b5a00', backgroundColor: '#fff4de', border: '1px solid #c98c1c', borderRadius: '12px', padding: '12px 14px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <TriangleAlert size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
                  <div>
                    <strong style={{ display: 'block', marginBottom: '4px' }}>OCR Low Confidence</strong>
                    <span>{selectedRequest.ocr_low_confidence_fields.map(formatOcrFieldLabel).join(', ')}</span>
                  </div>
                </div>
              ) : null}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                  <div>
                    <strong style={{ display: 'block', marginBottom: '4px' }}>Receipt Preview</strong>
                    <span style={{ color: '#666', fontSize: '13px' }}>
                      {selectedRequest.receipt_file_name || 'ไม่มีชื่อไฟล์แนบ'}
                    </span>
                  </div>
                  {canPreviewReceipt ? (
                    <a
                      href={receiptPreview.signed_url}
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

                {receiptPreviewLoading ? (
                  <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                    กำลังโหลดลิงก์ไฟล์จาก GCS...
                  </div>
                ) : null}

                {receiptPreviewError ? (
                  <div style={{ color: '#912018', backgroundColor: '#fde8e8', border: '1px solid #de5b52', borderRadius: '12px', padding: '12px 14px' }}>
                    {receiptPreviewError}
                  </div>
                ) : null}

                {!selectedRequest.receipt_storage_key && !receiptPreviewLoading ? (
                  <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                    รายการนี้ยังไม่มีไฟล์ receipt ที่เก็บไว้
                  </div>
                ) : null}

                {canPreviewReceipt && isPreviewImage ? (
                  <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                    <img
                      src={receiptPreview.signed_url}
                      alt={receiptPreview.file_name || 'Receipt preview'}
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

                {canPreviewReceipt && isPreviewPdf ? (
                  <div style={{ backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '16px', padding: '12px' }}>
                    <iframe
                      src={receiptPreview.signed_url}
                      title={receiptPreview.file_name || 'Receipt PDF preview'}
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

                {canPreviewReceipt && !isPreviewImage && !isPreviewPdf ? (
                  <div style={{ color: '#666', backgroundColor: '#faf7f1', border: '1px solid #e7decd', borderRadius: '12px', padding: '14px 16px' }}>
                    ไฟล์นี้ไม่ใช่รูปภาพ ใช้ปุ่ม Open Receipt เพื่อเปิดไฟล์ต้นฉบับ
                  </div>
                ) : null}
              </div>

              {selectedRequest.ocr_raw_json ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <strong style={{ display: 'block' }}>OCR Debug JSON</strong>
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

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Requester</span>
                  <input style={inputStyle} value={editor.requester_name} onChange={handleEditorChange('requester_name')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Phone</span>
                  <input style={inputStyle} value={editor.phone} onChange={handleEditorChange('phone')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Request Date</span>
                  <input type="date" style={inputStyle} value={editor.request_date} onChange={handleEditorChange('request_date')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Approved Amount</span>
                  <input type="number" style={inputStyle} value={editor.amount} onChange={handleEditorChange('amount')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Receipt No</span>
                  <input style={inputStyle} value={editor.receipt_no} onChange={handleEditorChange('receipt_no')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Document Date</span>
                  <input type="date" style={inputStyle} value={editor.document_date} onChange={handleEditorChange('document_date')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Work Type</span>
                  <select style={inputStyle} value={editor.work_type} onChange={handleEditorChange('work_type')} disabled={!canEdit}>
                    {WORK_TYPE_OPTIONS.map((option) => (
                      <option key={option.value || 'empty-work'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Request Type</span>
                  <select style={inputStyle} value={editor.request_type} onChange={handleEditorChange('request_type')} disabled={!canEdit}>
                    {REQUEST_TYPE_OPTIONS.map((option) => (
                      <option key={option.value || 'empty-request'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Vendor</span>
                  <input style={inputStyle} value={editor.vendor_name} onChange={handleEditorChange('vendor_name')} disabled={!canEdit} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600' }}>Payment Reference</span>
                  <input style={inputStyle} value={editor.payment_reference} onChange={handleEditorChange('payment_reference')} />
                </label>
              </div>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '13px', fontWeight: '600' }}>Submission Note</span>
                <textarea
                  rows={4}
                  style={{ ...inputStyle, resize: 'vertical', minHeight: '92px' }}
                  value={editor.note}
                  onChange={handleEditorChange('note')}
                  disabled={!canEdit}
                />
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '13px', fontWeight: '600' }}>Review Note</span>
                <textarea
                  rows={3}
                  style={{ ...inputStyle, resize: 'vertical', minHeight: '78px' }}
                  value={editor.review_note}
                  onChange={handleEditorChange('review_note')}
                />
              </label>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '6px' }}>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!!busyAction || !canEdit}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: '1px solid #d8cfbf',
                    backgroundColor: 'white',
                    cursor: busyAction || !canEdit ? 'wait' : 'pointer',
                    opacity: canEdit ? 1 : 0.55,
                  }}
                >
                  <Save size={16} />
                  {busyAction === 'save' ? 'Saving...' : 'Save Changes'}
                </button>

                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={!!busyAction || !canApprove}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: 'none',
                    backgroundColor: '#27a57a',
                    color: 'white',
                    cursor: busyAction || !canApprove ? 'wait' : 'pointer',
                    opacity: canApprove ? 1 : 0.55,
                  }}
                >
                  <CheckCheck size={16} />
                  {busyAction === 'approve' ? 'Approving...' : 'Approve'}
                </button>

                <button
                  type="button"
                  onClick={handleReject}
                  disabled={!!busyAction || !canReject}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: 'none',
                    backgroundColor: '#de5b52',
                    color: 'white',
                    cursor: busyAction || !canReject ? 'wait' : 'pointer',
                    opacity: canReject ? 1 : 0.55,
                  }}
                >
                  <OctagonX size={16} />
                  {busyAction === 'reject' ? 'Rejecting...' : 'Reject'}
                </button>

                <button
                  type="button"
                  onClick={handleMarkPaid}
                  disabled={!!busyAction || !canMarkPaid}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: 'none',
                    backgroundColor: '#1f6f8b',
                    color: 'white',
                    cursor: busyAction || !canMarkPaid ? 'wait' : 'pointer',
                    opacity: canMarkPaid ? 1 : 0.55,
                  }}
                >
                  <CircleDollarSign size={16} />
                  {busyAction === 'mark-paid' ? 'Marking Paid...' : 'Mark Paid'}
                </button>
              </div>

              <div style={{ marginTop: '8px', padding: '14px', borderRadius: '16px', backgroundColor: '#f7f4ef' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <CircleDollarSign size={18} />
                  <strong>Financial Snapshot</strong>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', color: '#555' }}>
                  <div>Requested Amount: {Number(selectedRequest.amount || 0).toLocaleString()} THB</div>
                  <div>Approved Amount: {Number(selectedRequest.approved_amount ?? selectedRequest.amount ?? 0).toLocaleString()} THB</div>
                  <div>Vendor: {selectedRequest.vendor_name || '-'}</div>
                  <div>Receipt No: {selectedRequest.receipt_no || '-'}</div>
                  <div>Document Date: {selectedRequest.document_date || '-'}</div>
                  <div>Receipt File: {selectedRequest.receipt_file_name || '-'}</div>
                  <div>Reviewed At: {selectedRequest.reviewed_at || '-'}</div>
                  <div>Paid At: {selectedRequest.paid_at || '-'}</div>
                  <div>Payment Ref: {selectedRequest.payment_reference || '-'}</div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default ApprovalPage;
