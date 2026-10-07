import { useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Link, Navigate, useLocation, useParams } from 'react-router-dom';
import { getStoredAuthUser, isSubcontractorUser, isAdminUser } from '../auth';
import { getMyInputRequests } from '../api';
import InputRequestSummary from './InputRequestSummary';
import { findOwnedInputRequest } from './inputWorkflowUtils';

export default function InputSuccessPage() {
  const { requestId } = useParams();
  const { state } = useLocation();
  const user = getStoredAuthUser();
  const allowed = isSubcontractorUser(user) && !isAdminUser(user);
  const initial = allowed && user?.subcontractor_id && state?.ownerSubcontractorId === user.subcontractor_id && state?.request?.request_id === requestId ? state.request : null;
  const [request, setRequest] = useState(initial);
  const [loading, setLoading] = useState(!initial);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!allowed || (initial && refresh === 0)) return;
    let active = true;
    getMyInputRequests().then((items) => {
      if (!active) return;
      const found = findOwnedInputRequest(items, requestId);
      setRequest(found);
      setError(found ? '' : 'ไม่พบคำขอนี้ในบัญชีของคุณ กรุณาตรวจในคำขอของฉัน');
    }).catch(() => { if (active) setError('โหลดคำขอไม่สำเร็จ กรุณาลองอีกครั้ง'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [allowed, initial, refresh, requestId]);
  useEffect(() => {
    document.getElementById('input-success-heading')?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [loading]);
  if (!allowed) return <Navigate to="/input" replace />;
  return (
    <section className="input-success-page input-workflow-surface" aria-busy={loading}>
      {loading ? <p role="status">กำลังโหลดคำขอ…</p> : null}
      {error ? <><h1 id="input-success-heading" tabIndex={-1}>ตรวจสอบคำขอ</h1><p className="input-notice error" role="alert">{error}</p><button type="button" className="input-button secondary" disabled={loading} onClick={() => { setLoading(true); setRefresh((value) => value + 1); }}>ลองใหม่</button></> : null}
      {request && !error ? <><header className="input-success-heading"><CheckCircle2 size={40} aria-hidden="true" /><h1 id="input-success-heading" tabIndex={-1}>ส่งคำขอสำเร็จ</h1><p>ระบบรับคำขอแล้ว ไม่ต้องส่งบิลนี้ซ้ำ</p></header><InputRequestSummary key={request.request_id} request={request} /></> : null}
      <footer className="input-success-actions"><Link className="input-button primary" to="/input" replace>กลับไปเริ่มใหม่</Link><Link className="input-button secondary" to="/input?view=history" replace>ดูคำขอของฉัน</Link></footer>
    </section>
  );
}
