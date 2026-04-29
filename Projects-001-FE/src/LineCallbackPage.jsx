import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { clearPendingLineAuth, resolvePostLoginPath, saveAuthSession, savePendingLineAuth } from './auth';
import { lineLogin } from './api';
import { getActiveLineAccessToken } from './liffClient';

const LineCallbackPage = () => {
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    const completeLogin = async () => {
      try {
        const lineAccessToken = await getActiveLineAccessToken();
        if (!lineAccessToken) {
          throw new Error('LINE login did not return an access token.');
        }

        const response = await lineLogin({ lineAccessToken });
        if (!active) return;

        if (response?.status === 'REQUIRE_SIGNUP') {
          savePendingLineAuth(response);
          navigate('/signup', { replace: true });
          return;
        }

        saveAuthSession(response);
        clearPendingLineAuth();
        navigate(resolvePostLoginPath(response.user), { replace: true });
      } catch (callbackError) {
        if (!active) return;
        setError(callbackError.message || 'Failed to complete LINE login.');
      }
    };

    completeLogin();

    return () => {
      active = false;
    };
  }, [navigate]);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--bg-primary)',
      padding: '24px',
      textAlign: 'center',
    }}>
      <div style={{
        maxWidth: '420px',
        backgroundColor: 'var(--card-bg)',
        borderRadius: '24px',
        border: '1px solid var(--border-color)',
        padding: '28px',
      }}>
        <h1 style={{ fontSize: '24px', marginBottom: '10px' }}>Completing LINE Login</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>
          {error || 'Verifying your LINE account and preparing the next step.'}
        </p>
      </div>
    </div>
  );
};

export default LineCallbackPage;
