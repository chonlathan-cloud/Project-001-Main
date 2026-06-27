import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Building2, FileBadge2, IdCard, Landmark, Phone, ShieldCheck, Smartphone, User } from 'lucide-react';

import {
  clearPendingLineAuth,
  getStoredPendingLineAuth,
  resolvePostLoginPath,
  saveAuthSession,
  savePendingLineAuth,
} from './auth';
import { adminLogin, lineLogin, submitAccessRequest } from './api';
import { signInAdminWithGooglePopup } from './firebaseClient';
import { beginLineLogin, getActiveLineAccessToken } from './liffClient';
import logoImage from './assets/Logo.png';

const fieldBoxStyle = {
  display: 'flex',
  alignItems: 'center',
  backgroundColor: '#fff',
  borderRadius: '8px',
  padding: '11px 14px',
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

const sectionTitleStyle = {
  gridColumn: '1 / -1',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  paddingBottom: '10px',
  borderBottom: '1px solid var(--border-color)',
  fontSize: '18px',
  fontWeight: '700',
  color: 'var(--text-main)',
};

const identityButtonStyle = (tone = 'primary') => ({
  width: '100%',
  minHeight: '52px',
  backgroundColor: tone === 'line' ? '#06c755' : 'var(--primary)',
  color: '#fff',
  border: 'none',
  borderRadius: '8px',
  padding: '14px 16px',
  fontSize: '15px',
  fontWeight: '700',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '10px',
});

const SignUpPage = () => {
  const navigate = useNavigate();
  const pendingLineAuth = useMemo(() => getStoredPendingLineAuth(), []);
  const [lineInfo, setLineInfo] = useState(pendingLineAuth);
  const [formData, setFormData] = useState({
    name: pendingLineAuth?.company_name || pendingLineAuth?.display_name || pendingLineAuth?.email || '',
    contactName: pendingLineAuth?.contact_name || pendingLineAuth?.display_name || '',
    phone: '',
    taxId: '',
    bankName: '',
    accountNo: '',
    accountName: pendingLineAuth?.display_name || '',
    requestedAccountType: pendingLineAuth?.provider === 'google' ? '' : 'subcontractor',
    kycImage: null,
  });
  const [loading, setLoading] = useState(false);
  const [identityLoadingAction, setIdentityLoadingAction] = useState('');
  const [error, setError] = useState('');
  const hasVerifiedIdentity = Boolean(lineInfo?.line_uid || lineInfo?.email);
  const providerLabel = lineInfo?.provider === 'google' ? 'Google' : 'LINE';
  const identityLabel = lineInfo?.email || lineInfo?.display_name || lineInfo?.line_uid || '';

  const applySignupIdentity = (response) => {
    const identity = response || {};
    const provider = String(identity.provider || '').trim().toLowerCase();
    savePendingLineAuth(identity);
    setLineInfo(identity);
    setFormData((current) => ({
      ...current,
      name: current.name || identity.company_name || identity.display_name || identity.email || '',
      contactName: current.contactName || identity.contact_name || identity.display_name || '',
      accountName: current.accountName || identity.display_name || '',
      requestedAccountType: current.requestedAccountType || (provider === 'line' ? 'subcontractor' : ''),
    }));
  };

  const completeAuthenticatedResponse = (response) => {
    saveAuthSession(response);
    clearPendingLineAuth();
    navigate(resolvePostLoginPath(response.user), { replace: true });
  };

  const handleGoogleIdentity = async () => {
    setIdentityLoadingAction('google');
    setError('');

    try {
      const googleAuth = await signInAdminWithGooglePopup();
      const response = await adminLogin(googleAuth);
      if (response?.status === 'REQUIRE_SIGNUP') {
        applySignupIdentity(response);
        return;
      }
      completeAuthenticatedResponse(response);
    } catch (identityError) {
      setError(identityError.message || 'Failed to verify Google identity.');
    } finally {
      setIdentityLoadingAction('');
    }
  };

  const handleLineIdentity = async () => {
    setIdentityLoadingAction('line');
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
        applySignupIdentity(response);
        return;
      }
      completeAuthenticatedResponse(response);
    } catch (identityError) {
      setError(identityError.message || 'Failed to verify LINE identity.');
    } finally {
      setIdentityLoadingAction('');
    }
  };

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
      const provider = String(lineInfo?.provider || (lineInfo?.line_uid ? 'line' : 'google')).trim().toLowerCase();
      if (provider === 'line' && !lineInfo?.line_uid) {
        throw new Error('Missing LINE identity. Start this flow from LINE login first.');
      }
      if (provider === 'google' && !lineInfo?.email) {
        throw new Error('Missing Gmail identity. Start this flow from Google login first.');
      }

      const response = await submitAccessRequest({
        provider,
        email: lineInfo.email,
        lineUid: lineInfo.line_uid,
        pictureUrl: lineInfo.picture_url || lineInfo.line_picture_url,
        displayName: lineInfo.display_name,
        requestedAccountType: formData.requestedAccountType,
        companyName: formData.name,
        contactName: formData.contactName,
        phone: formData.phone,
        taxId: formData.taxId,
        bankName: formData.bankName,
        accountNo: formData.accountNo,
        accountName: formData.accountName,
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
        borderRadius: '12px',
        width: '100%',
        maxWidth: '800px',
        border: '1px solid var(--border-color)',
        boxShadow: 'none',
        overflow: 'hidden',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '28px 0',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '82px', objectFit: 'contain' }} />
        </div>

        <div style={{ padding: '32px' }}>
          <div style={{ marginBottom: '22px' }}>
            <h1 style={{ fontSize: '32px', marginBottom: '8px', color: 'var(--text-main)' }}>Request System Access</h1>
            <p style={{ color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
              Provide your contact details for admin review. Access starts only after approval.
            </p>
          </div>

          {hasVerifiedIdentity ? (
            <div style={{
              marginBottom: '18px',
              padding: '12px 14px',
              borderRadius: '12px',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              fontSize: '13px',
            }}>
              Identity verified with <strong>{providerLabel}</strong>: <strong>{identityLabel}</strong>
            </div>
          ) : null}

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

          {!hasVerifiedIdentity ? (
            <div style={{
              padding: '22px',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', marginBottom: '18px' }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '8px',
                  backgroundColor: '#eef5f2',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flex: '0 0 auto',
                }}>
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <h2 style={{ fontSize: '20px', margin: '0 0 6px', color: 'var(--text-main)' }}>Verify Identity</h2>
                  <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    Choose Google or LINE first. After that, submit your details for admin approval.
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '14px' }} className="identity-choice-grid">
                <button
                  type="button"
                  onClick={handleGoogleIdentity}
                  disabled={identityLoadingAction !== ''}
                  style={{
                    ...identityButtonStyle('primary'),
                    opacity: identityLoadingAction ? 0.72 : 1,
                    cursor: identityLoadingAction ? 'wait' : 'pointer',
                  }}
                >
                  <ShieldCheck size={18} />
                  {identityLoadingAction === 'google' ? 'Verifying Google...' : 'Register with Google'}
                </button>

                <button
                  type="button"
                  onClick={handleLineIdentity}
                  disabled={identityLoadingAction !== ''}
                  style={{
                    ...identityButtonStyle('line'),
                    opacity: identityLoadingAction ? 0.72 : 1,
                    cursor: identityLoadingAction ? 'wait' : 'pointer',
                  }}
                >
                  <Smartphone size={18} />
                  {identityLoadingAction === 'line' ? 'Connecting LINE...' : 'Register with LINE'}
                </button>
              </div>
            </div>
          ) : (
            <form
              onSubmit={handleSignUp}
              className="subcon-signup-form"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: '18px 20px',
              }}
            >
            <div style={sectionTitleStyle}>
              <Building2 size={20} color="var(--primary)" />
              Business Information
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Requested Access Type
              </label>
              <div style={fieldBoxStyle}>
                <Building2 size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <select
                  value={formData.requestedAccountType}
                  onChange={(event) => handleChange('requestedAccountType', event.target.value)}
                  style={inputStyle}
                >
                  <option value="">Admin will decide</option>
                  <option value="subcontractor">Subcontractor</option>
                  <option value="admin">Admin / Staff</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Company / Display Name
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
                Default Contact Name
              </label>
              <div style={fieldBoxStyle}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.contactName}
                  onChange={(event) => handleChange('contactName', event.target.value)}
                  placeholder="Pao"
                  style={inputStyle}
                  required
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Default Phone Number
              </label>
              <div style={fieldBoxStyle}>
                <Phone size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(event) => handleChange('phone', event.target.value)}
                  placeholder="0812345678"
                  style={inputStyle}
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
                />
              </div>
            </div>

            <div style={sectionTitleStyle}>
              <Landmark size={20} color="var(--primary)" />
              Financial Details
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Default Bank Name
              </label>
              <div style={fieldBoxStyle}>
                <Landmark size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.bankName}
                  onChange={(event) => handleChange('bankName', event.target.value)}
                  placeholder="Bangkok Bank"
                  style={inputStyle}
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Default Account Number
              </label>
              <div style={fieldBoxStyle}>
                <Landmark size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.accountNo}
                  onChange={(event) => handleChange('accountNo', event.target.value)}
                  placeholder="123-4-56789-0"
                  style={inputStyle}
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                Default Account Name
              </label>
              <div style={fieldBoxStyle}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input
                  type="text"
                  value={formData.accountName}
                  onChange={(event) => handleChange('accountName', event.target.value)}
                  placeholder="Pao"
                  style={inputStyle}
                />
              </div>
            </div>

            <div style={sectionTitleStyle}>
              <FileBadge2 size={20} color="var(--primary)" />
              KYC Verification
            </div>

            <div style={{ marginBottom: '22px', gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>
                KYC ID Card Image
              </label>
              <div style={{
                borderRadius: '12px',
                border: '2px dashed #c1c8c4',
                backgroundColor: 'var(--bg-primary)',
                padding: '24px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--text-muted)' }}>
                  <FileBadge2 size={18} />
                  Upload a photo for private storage and signed-URL review
                </div>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => handleChange('kycImage', event.target.files?.[0] || null)}
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
                gridColumn: '1 / -1',
                justifySelf: 'end',
                minWidth: '280px',
                backgroundColor: 'var(--primary)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '14px',
                fontSize: '16px',
                fontWeight: '700',
                cursor: loading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Submitting Request...' : 'Submit for Approval'}
              <ArrowRight size={18} />
            </button>
            </form>
          )}

          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px' }}>
            <Link
              to="/login"
              style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: '600', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
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
