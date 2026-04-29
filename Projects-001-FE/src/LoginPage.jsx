import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Smartphone } from 'lucide-react';

import { clearPendingLineAuth, resolvePostLoginPath, saveAuthSession, savePendingLineAuth } from './auth';
import { adminLogin, lineLogin } from './api';
import { signInAdminWithGooglePopup } from './firebaseClient';
import { beginLineLogin, getActiveLineAccessToken } from './liffClient';
import logoImage from './assets/Logo.png';

const panelStyle = {
  backgroundColor: 'var(--card-bg)',
  borderRadius: '32px',
  width: '100%',
  maxWidth: '460px',
  border: '1px solid var(--border-color)',
  boxShadow: '0 10px 40px rgba(0,0,0,0.05)',
  overflow: 'hidden',
};

const actionButton = (tone = 'primary') => ({
  width: '100%',
  backgroundColor: tone === 'primary' ? 'var(--accent-gold)' : '#06c755',
  color: '#fff',
  border: 'none',
  borderRadius: '16px',
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
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');

  const handleAdminGoogleLogin = async () => {
    setLoadingAction('admin');
    setError('');
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
          padding: '40px 0',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '110px', objectFit: 'contain' }} />
        </div>

        <div style={{ padding: '32px' }}>
          <div style={{ marginBottom: '26px' }}>
            <h1 style={{ fontSize: '28px', marginBottom: '10px' }}>Sign In</h1>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
              Admin uses Google sign-in. Subcontractor enters through LINE LIFF and completes KYC on first access.
            </p>
          </div>

          {error ? (
            <div style={{
              marginBottom: '18px',
              padding: '12px 14px',
              borderRadius: '14px',
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
            <Link
              to="/signup"
              style={{
                color: '#0066cc',
                textDecoration: 'none',
                fontWeight: '600',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              Open Sign Up <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
