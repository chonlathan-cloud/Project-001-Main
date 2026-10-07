import { useState } from 'react';
import { getInputRequestReceiptUrl } from '../api';
import { inputDate, inputMoney, inputStatusLabel } from './inputWorkflowUtils';

export default function InputRequestSummary({ request }) {
  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const openReceipt = async () => {
    setLoading(true);
    setError('');
    try { setReceipt(await getInputRequestReceiptUrl(request.request_id, { forceRefresh: Boolean(receipt) })); }
    catch { setError('เปิดเอกสารไม่ได้ กรุณาลองอีกครั้ง'); }
    finally { setLoading(false); }
  };
  return (
    <div className="input-request-summary">
      <div className="input-summary-amount"><span>ยอดคำขอ</span><strong>{inputMoney(request.amount)} <small>บาท</small></strong></div>
      <p className="input-status-label" data-status={request.status}>{inputStatusLabel(request.status)}</p>
      {request.is_duplicate_flag ? <p className="input-notice warning" role="status">รายการนี้ถูกส่งแล้ว และระบบพบข้อมูลที่อาจซ้ำ กรุณารอผู้ดูแลตรวจสอบ ไม่ต้องส่งซ้ำ</p> : null}
      <dl className="input-summary-list">
        <div><dt>เลขคำขอ</dt><dd>{request.request_id}</dd></div>
        <div><dt>โครงการ</dt><dd>{request.project_name || '—'}</dd></div>
        <div><dt>ผู้ขาย</dt><dd>{request.vendor_name || '—'}</dd></div>
        <div><dt>เลขบิล</dt><dd>{request.receipt_no || '—'}</dd></div>
        <div><dt>วันที่เอกสาร</dt><dd>{inputDate(request.document_date)}</dd></div>
        <div><dt>วันที่ส่งคำขอ</dt><dd>{inputDate(request.request_date)}</dd></div>
      </dl>
      {request.review_note ? <p className="input-notice"><strong>หมายเหตุผู้ดูแล</strong><br />{request.review_note}</p> : null}
      <details className="input-disclosure">
        <summary>รายละเอียดคำขอ</summary>
        <dl className="input-summary-list">
          <div><dt>ผู้ยื่น</dt><dd>{request.requester_name || '—'}</dd></div>
          <div><dt>ประเภทงาน</dt><dd>{request.work_type || '—'}</dd></div>
          <div><dt>ประเภทการเบิก</dt><dd>{request.request_type || '—'}</dd></div>
          <div><dt>VAT</dt><dd>{{ no_vat: 'ไม่มี VAT', vat_inclusive: 'รวมในราคา', vat_exclusive: 'แยกจากราคา' }[request.accounting_vat_mode] || '—'}</dd></div>
          <div><dt>บัญชีรับเงิน</dt><dd>{[request.bank_account?.bank_name, request.bank_account?.account_no, request.bank_account?.account_name].filter(Boolean).join(' · ') || '—'}</dd></div>
        </dl>
        <ul className="input-summary-items">{(request.line_items || []).map((item, index) => <li key={item.id || index}><span>{item.description}<small>{item.qty} × {inputMoney(item.unit_price)}</small></span><strong>{inputMoney(item.amount)}</strong></li>)}</ul>
        {request.tags?.length ? <p>แท็ก: {request.tags.join(', ')}</p> : null}
        {request.note ? <p>หมายเหตุ: {request.note}</p> : null}
      </details>
      {request.receipt_storage_key ? (
        <div className="input-receipt-access">
          <button type="button" className="input-button secondary" disabled={loading} onClick={openReceipt}>{loading ? 'กำลังโหลดเอกสาร…' : receipt ? 'โหลดลิงก์เอกสารใหม่' : 'ดูบิลที่ส่ง'}</button>
          {receipt?.signed_url ? <a className="input-button secondary" href={receipt.signed_url} target="_blank" rel="noopener noreferrer">เปิดเอกสาร</a> : null}
          {error ? <p role="alert">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
