import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, FileBadge2, IdCard, User } from 'lucide-react';

import {
  clearPendingLineAuth,
  getStoredPendingLineAuth,
  resolvePostLoginPath,
  saveAuthSession,
} from './auth';
import { signUpSubcontractor } from './api';
import { getActiveLineProfile } from './liffClient';
import logoImage from './assets/Logo.png';

const fieldBoxStyle = {
  display: 'flex',
  alignItems: 'center',
  backgroundColor: '#f3f4f6',
  borderRadius: '12px',
  padding: '10px 16px',
  border: '1px solid var(--border-color)',
};

const inputStyle = {
  border: 'none',
  background: 'transparent',
  width: '100%',
  outline: 'none',
  fontSize: '14px',
  color: 'var(--text-main)',
};

const SignUpPage = () => {
  const navigate = useNavigate();
  const pendingLineAuth = useMemo(() => getStoredPendingLineAuth(), []);
  const [lineInfo, setLineInfo] = useState(pendingLineAuth);
  const [formData, setFormData] = useState({
    name: pendingLineAuth?.display_name || '',
    taxId: '',
    kycImage: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const hydrateFromLiff = async () => {
      if (pendingLineAuth?.line_uid) return;
      try {
        const profile = await getActiveLineProfile();
        if (!profile?.userId) return;
        setLineInfo({
          line_uid: profile.userId,
          display_name: profile.displayName || '',
          status: 'REQUIRE_SIGNUP',
        });
        setFormData((current) => ({
          ...current,
          name: current.name || profile.displayName || '',
        }));
      } catch {
        // Keep the form usable for explicit retry from LoginPage.
      }
    };

    hydrateFromLiff();
  }, [pendingLineAuth?.line_uid]);

  const handleChange = (field, value) => {
    setFormData((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSignUp = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (!lineInfo?.line_uid) {
        throw new Error('Missing LINE identity. Start this flow from LINE login first.');
      }

      if (!formData.kycImage) {
        throw new Error('Please attach the KYC ID card image before submitting.');
      }

      const response = await signUpSubcontractor({
        lineUid: lineInfo.line_uid,
        name: formData.name,
        taxId: formData.taxId,
        kycImage: formData.kycImage,
      });

      saveAuthSession(response);
      clearPendingLineAuth();
      navigate(resolvePostLoginPath(response.user), { replace: true });
    } catch (submitError) {
      setError(submitError.message || 'Failed to complete registration.');
    } finally {
      setLoading(false);
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
      padding: '40px 20px',
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '32px',
        width: '100%',
        maxWidth: '460px',
        border: '1px solid var(--border-color)',
        boxShadow: '0 10px 40px rgba(0,0,0,0.05)',
        overflow: 'hidden',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '40px 0',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '110px', objectFit: 'contain' }} />
        </div>

        <div style={{ padding: '32px' }}>
          <div style={{ marginBottom: '22px' }}>
            <h1 style={{ fontSize: '28px', marginBottom: '10px' }}>Subcontractor Sign Up</h1>
            <p style={{ color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
              First-time access requires tax information and a KYC ID card image. The file is stored in private GCS storage.
            </p>
          </div>

          {lineInfo?.line_uid ? (
            <div style={{
              marginBottom: '18px',
              padding: '12px 14px',
              borderRadius: '14px',
              backgroundColor: '#f8fafc',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              fontSize: '13px',
            }}>
              LINE UID linked for this registration: <strong>{lineInfo.line_uid}</strong>
            </div>
          ) : null}

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

          <form onSubmit={handleSignUp}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Company / Subcontractor Name
              </label>
              <div style={fieldBoxStyle}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.name}
                  onChange={(event) => handleChange('name', event.target.value)}
                  placeholder="ABC Construction Co., Ltd."
                  style={inputStyle}
                  required
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Tax Identification Number
              </label>
              <div style={fieldBoxStyle}>
                <IdCard size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.taxId}
                  onChange={(event) => handleChange('taxId', event.target.value)}
                  placeholder="1234567890123"
                  style={inputStyle}
                  required
                />
              </div>
            </div>

            <div style={{ marginBottom: '22px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                KYC ID Card Image
              </label>
              <div style={{
                borderRadius: '14px',
                border: '1px dashed var(--border-color)',
                backgroundColor: '#faf8f3',
                padding: '18px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--text-muted)' }}>
                  <FileBadge2 size={18} />
                  Upload a photo for private storage and signed-URL review
                </div>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => handleChange('kycImage', event.target.files?.[0] || null)}
                  required
                />
                {formData.kycImage ? (
                  <div style={{ marginTop: '10px', fontSize: '13px', color: 'var(--text-main)' }}>
                    Selected file: {formData.kycImage.name}
                  </div>
                ) : null}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                backgroundColor: 'var(--accent-gold)',
                color: '#fff',
                border: 'none',
                borderRadius: '14px',
                padding: '14px',
                fontSize: '16px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              {loading ? 'Submitting Registration...' : 'Complete Registration'}
              <ArrowRight size={18} />
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px' }}>
            <Link
              to="/login"
              style={{ color: '#0066cc', textDecoration: 'none', fontWeight: '600', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              onClick={() => clearPendingLineAuth()}
            >
              <ArrowLeft size={16} /> Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
