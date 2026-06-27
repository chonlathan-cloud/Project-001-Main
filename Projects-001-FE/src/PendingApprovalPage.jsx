import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock3, LogOut, RefreshCw, ShieldCheck, XCircle } from 'lucide-react';

import { clearAuthSession, getStoredAuthUser } from './auth';
import { getAccessRequestStatus } from './api';
import { signOutFirebaseClient } from './firebaseClient';
import { logoutLineClient } from './liffClient';
import logoImage from './assets/Logo.png';

const statusCopy = {
  pending: {
    icon: Clock3,
    title: 'Access request pending',
    message: 'An admin is reviewing your account before system access is enabled.',
    tone: '#9a6700',
    bg: '#fff8e1',
  },
  approved: {
    icon: ShieldCheck,
    title: 'Access approved',
    message: 'Please sign in again to start with your approved permissions.',
    tone: '#157347',
    bg: '#e9f7ef',
  },
  rejected: {
    icon: XCircle,
    title: 'Access request rejected',
    message: 'Please contact your admin if you think this needs another review.',
    tone: '#b42318',
    bg: '#fff1f0',
  },
};

export default function PendingApprovalPage() {
  const navigate = useNavigate();
  const [authUser] = useState(() => getStoredAuthUser());
  const [status, setStatus] = useState(() => authUser?.access_status || 'pending');
  const [rejectionReason, setRejectionReason] = useState(() => authUser?.rejection_reason || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const refreshStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const request = await getAccessRequestStatus();
      setStatus(request?.status || 'pending');
      setRejectionReason(request?.rejection_reason || '');
    } catch (statusError) {
      setError(statusError.message || 'Unable to refresh approval status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  const handleSignOut = async () => {
    clearAuthSession();
    await Promise.allSettled([signOutFirebaseClient(), logoutLineClient()]);
    navigate('/login', { replace: true });
  };

  const copy = statusCopy[status] || statusCopy.pending;
  const Icon = copy.icon;
  const identity = authUser?.email || authUser?.line_uid || authUser?.access_request_id || 'Pending account';

  return (
    <main style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)',
      padding: '24px',
    }}>
      <section style={{
        width: '100%',
        maxWidth: '520px',
        background: 'var(--card-bg)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '28px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '72px', objectFit: 'contain' }} />
        </div>

        <div style={{
          display: 'flex',
          gap: '14px',
          alignItems: 'flex-start',
          background: copy.bg,
          border: `1px solid ${copy.tone}33`,
          borderRadius: '10px',
          padding: '16px',
          color: copy.tone,
        }}>
          <Icon size={24} />
          <div>
            <h1 style={{ margin: 0, fontSize: '22px', color: copy.tone }}>{copy.title}</h1>
            <p style={{ margin: '8px 0 0', color: 'var(--text-main)', lineHeight: 1.5 }}>{copy.message}</p>
          </div>
        </div>

        <div style={{ marginTop: '22px', display: 'grid', gap: '10px', color: 'var(--text-main)' }}>
          <div><strong>Identity:</strong> {identity}</div>
          <div><strong>Provider:</strong> {authUser?.auth_provider || (authUser?.line_uid ? 'line' : 'google')}</div>
          {rejectionReason ? <div><strong>Reason:</strong> {rejectionReason}</div> : null}
          {error ? <div style={{ color: '#b42318' }}>{error}</div> : null}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '26px', flexWrap: 'wrap' }}>
          <button type="button" className="settings-button secondary" onClick={refreshStatus} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Refresh
          </button>
          <button type="button" className="settings-button primary" onClick={handleSignOut}>
            <LogOut size={16} />
            Sign In Again
          </button>
        </div>
      </section>
    </main>
  );
}
