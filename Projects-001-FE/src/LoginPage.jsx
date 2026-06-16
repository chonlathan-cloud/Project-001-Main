import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Smartphone } from 'lucide-react';

import {
  clearAuthNotice,
  clearPendingLineAuth,
  getStoredAuthNotice,
  resolvePostLoginPath,
  saveAuthSession,
  savePendingLineAuth,
} from './auth';
import { adminLogin, lineLogin } from './api';
import AuthNotice from './components/AuthNotice';
import { signInAdminWithGooglePopup } from './firebaseClient';
import { beginLineLogin, getActiveLineAccessToken } from './liffClient';
import logoImage from './assets/Logo.png';

const panelStyle = {
  backgroundColor: 'var(--card-bg)',
  borderRadius: '12px',
  width: '100%',
  maxWidth: '440px',
  border: '1px solid var(--border-color)',
  boxShadow: 'none',
  overflow: 'hidden',
};

const actionButton = (tone = 'primary') => ({
  width: '100%',
  backgroundColor: tone === 'primary' ? 'var(--primary)' : '#06c755',
  color: '#fff',
  border: 'none',
  borderRadius: '8px',
  padding: '16px 18px',
  fontSize: '15px',
  fontWeight: '700',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '10px',
});

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [authNotice, setAuthNotice] = useState(() => (
    location.state?.authNotice ||
    (location.state?.reason === 'session_expired'
      ? {
          tone: 'warning',
          title: 'Session expired',
          message: 'เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้งเพื่อใช้งานต่อ',
        }
      : null) ||
    getStoredAuthNotice()
  ));

  const handleAdminGoogleLogin = async () => {
    setLoadingAction('admin');
    setError('');
    setAuthNotice(null);
    clearAuthNotice();
    clearPendingLineAuth();

    try {
      const googleAuth = await signInAdminWithGooglePopup();
      const response = await adminLogin(googleAuth);
      saveAuthSession(response);
      navigate(resolvePostLoginPath(response.user), { replace: true });
    } catch (loginError) {
      setError(loginError.message || 'Failed to sign in with Google.');
    } finally {
      setLoadingAction('');
    }
  };

  const handleLineLogin = async () => {
    setLoadingAction('line');
    setError('');
    setAuthNotice(null);
    clearAuthNotice();

    try {
      const liffClient = await beginLineLogin();
      if (!liffClient) {
        return;
      }

      const lineAccessToken = await getActiveLineAccessToken();
      if (!lineAccessToken) {
        throw new Error('LINE login did not return an access token.');
      }

      const response = await lineLogin({ lineAccessToken });
      if (response?.status === 'REQUIRE_SIGNUP') {
        savePendingLineAuth(response);
        navigate('/signup', { replace: true });
        return;
      }

      saveAuthSession(response);
      clearPendingLineAuth();
      navigate(resolvePostLoginPath(response.user), { replace: true });
    } catch (loginError) {
      setError(loginError.message || 'Failed to sign in with LINE.');
    } finally {
      setLoadingAction('');
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      width: '100%',
      padding: '20px',
    }}>
      <div style={panelStyle}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '28px 0',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '92px', objectFit: 'contain' }} />
        </div>

        <div style={{ padding: '32px' }}>
          <div style={{ marginBottom: '26px' }}>
            <h1 style={{ fontSize: '32px', marginBottom: '8px', color: 'var(--text-main)' }}>Projects-001</h1>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
              Subcontractor Portal access with LINE LIFF. Admins can continue with Google sign-in.
            </p>
          </div>

          <AuthNotice notice={authNotice} />

          {error ? (
            <div style={{
              marginBottom: '18px',
              padding: '12px 14px',
              borderRadius: '12px',
              backgroundColor: '#fff5f4',
              color: '#b42318',
              border: '1px solid #f7b4ad',
              fontSize: '14px',
            }}>
              {error}
            </div>
          ) : null}

          <div style={{ display: 'grid', gap: '14px' }}>
            <button
              type="button"
              style={actionButton('primary')}
              onClick={handleAdminGoogleLogin}
              disabled={loadingAction !== ''}
            >
              <ShieldCheck size={18} />
              {loadingAction === 'admin' ? 'Signing in with Google...' : 'Continue as Admin with Google'}
            </button>

            <button
              type="button"
              style={actionButton('line')}
              onClick={handleLineLogin}
              disabled={loadingAction !== ''}
            >
              <Smartphone size={18} />
              {loadingAction === 'line' ? 'Connecting LINE...' : 'Continue as Subcontractor with LINE'}
            </button>
          </div>

          <div style={{ marginTop: '28px', paddingTop: '22px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              Need to complete first-time subcontractor registration?
            </div>
            <button
              type="button"
              onClick={handleLineLogin}
              disabled={loadingAction !== ''}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                color: 'var(--primary)',
                fontWeight: '600',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                cursor: loadingAction ? 'wait' : 'pointer',
              }}
            >
              Start with LINE <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
