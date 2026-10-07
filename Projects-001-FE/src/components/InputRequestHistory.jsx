import { useEffect, useState } from 'react';
import { getMyInputRequests } from '../api';
import InputRequestSummary from './InputRequestSummary';
import { inputDate, inputMoney, inputStatusLabel } from './inputWorkflowUtils';

export default function InputRequestHistory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    getMyInputRequests().then((rows) => { if (active) { setItems(rows); setError(''); } })
      .catch(() => { if (active) setError('โหลดคำขอไม่สำเร็จ กรุณาลองอีกครั้ง'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refresh]);
  return (
    <section className="input-workflow-surface" aria-labelledby="input-history-heading" aria-busy={loading}>
      <header className="input-history-heading"><h2 id="input-history-heading">คำขอของฉัน</h2><button className="input-button secondary" type="button" disabled={loading} onClick={() => { setLoading(true); setRefresh((value) => value + 1); }}>โหลดล่าสุด</button></header>
      {loading ? <p role="status">กำลังโหลดคำขอ…</p> : null}
      {error ? <p className="input-notice error" role="alert">{error}</p> : null}
      {!loading && !error && !items.length ? <p className="input-empty-copy">ยังไม่มีคำขอที่ส่ง เริ่มได้ที่แท็บ “ส่งคำขอ”</p> : null}
      <div className="input-history-list">{items.map((item) => (
        <details className="input-history-entry" key={item.request_id}>
          <summary><span><strong>{item.vendor_name || item.receipt_file_name || 'คำขอ'}</strong><small>{item.project_name} · {inputDate(item.request_date)}</small><small>เลขบิล {item.receipt_no || '—'}</small></span><span><strong>{inputMoney(item.amount)} บาท</strong><small className="input-status-label" data-status={item.status}>{inputStatusLabel(item.status)}</small><small>ดูรายละเอียด ▾</small></span></summary>
          <InputRequestSummary request={item} />
        </details>
      ))}</div>
    </section>
  );
}
