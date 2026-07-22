import React, { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
import CustomerAccessRequestForm from './components/signup/CustomerAccessRequestForm';
import SignupFormField from './components/signup/SignupFormField';

function getThaiSignupError(error, fallbackMessage) {
  const message = String(error?.message || '').trim();
  if (/[฀-๿]/.test(message)) return message;
  if (/popup.*(closed|cancel)|cancel.*popup/i.test(message)) {
    return 'ยกเลิกการยืนยันตัวตนแล้ว กรุณาลองใหม่เมื่อพร้อม';
  }
  if (/network|failed to fetch|connection/i.test(message)) {
    return 'ไม่สามารถเชื่อมต่อระบบได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองอีกครั้ง';
  }
  return fallbackMessage;
}

const SignUpPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const pendingLineAuth = useMemo(() => getStoredPendingLineAuth(), []);
  const portal = pendingLineAuth?.portal === 'customer'
    || new URLSearchParams(location.search).get('portal') === 'customer'
    ? 'customer'
    : 'subcontractor';
  const isCustomerPortal = portal === 'customer';
  const [lineInfo, setLineInfo] = useState(pendingLineAuth);
  const [formData, setFormData] = useState({
    name: isCustomerPortal
      ? ''
      : pendingLineAuth?.company_name || pendingLineAuth?.display_name || pendingLineAuth?.email || '',
    firstName: isCustomerPortal
      ? pendingLineAuth?.first_name || pendingLineAuth?.contact_name || ''
      : '',
    nickname: isCustomerPortal
      ? pendingLineAuth?.nickname || pendingLineAuth?.display_name || ''
      : '',
    contactName: pendingLineAuth?.contact_name
      || (isCustomerPortal ? '' : pendingLineAuth?.display_name || ''),
    phone: '',
    taxId: '',
    bankName: '',
    accountNo: '',
    accountName: pendingLineAuth?.display_name || '',
    requestedAccountType: portal === 'customer'
      ? 'customer'
      : pendingLineAuth?.provider === 'google'
        ? ''
        : 'subcontractor',
    kycImage: null,
  });
  const [loading, setLoading] = useState(false);
  const [identityLoadingAction, setIdentityLoadingAction] = useState('');
  const [error, setError] = useState('');
  const hasVerifiedIdentity = isCustomerPortal
    ? Boolean(lineInfo?.line_uid)
    : Boolean(lineInfo?.line_uid || lineInfo?.email);
  const providerLabel = lineInfo?.provider === 'google' ? 'Google' : 'LINE';
  const identityLabel = lineInfo?.email || lineInfo?.display_name || lineInfo?.line_uid || '';

  const applySignupIdentity = (response) => {
    const identity = response || {};
    const provider = String(identity.provider || '').trim().toLowerCase();
    const isCustomerIdentity = isCustomerPortal || identity.portal === 'customer';
    savePendingLineAuth(identity);
    setLineInfo(identity);
    setFormData((current) => ({
      ...current,
      name: current.name
        || identity.company_name
        || (isCustomerIdentity ? '' : identity.display_name || identity.email || ''),
      firstName: current.firstName
        || (isCustomerIdentity ? identity.first_name || identity.contact_name || '' : ''),
      nickname: current.nickname
        || (isCustomerIdentity ? identity.nickname || identity.display_name || '' : ''),
      contactName: current.contactName
        || identity.contact_name
        || (isCustomerIdentity ? '' : identity.display_name || ''),
      accountName: current.accountName || identity.display_name || '',
      requestedAccountType: current.requestedAccountType
        || (identity.portal === 'customer' ? 'customer' : provider === 'line' ? 'subcontractor' : ''),
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
      setError(getThaiSignupError(
        identityError,
        'ไม่สามารถยืนยันตัวตนด้วย Google ได้ กรุณาลองอีกครั้ง',
      ));
    } finally {
      setIdentityLoadingAction('');
    }
  };

  const handleLineIdentity = async () => {
    setIdentityLoadingAction('line');
    setError('');

    try {
      const liffClient = await beginLineLogin(portal);
      if (!liffClient) {
        return;
      }

      const lineAccessToken = await getActiveLineAccessToken(portal);
      if (!lineAccessToken) {
        throw new Error('ไม่พบข้อมูลยืนยันตัวตนจาก LINE กรุณาเข้าสู่ระบบด้วย LINE ใหม่อีกครั้ง');
      }

      const response = await lineLogin({ lineAccessToken, portal });
      if (response?.status === 'REQUIRE_SIGNUP') {
        applySignupIdentity(response);
        return;
      }
      completeAuthenticatedResponse(response);
    } catch (identityError) {
      setError(getThaiSignupError(
        identityError,
        'ไม่สามารถยืนยันตัวตนด้วย LINE ได้ กรุณาลองอีกครั้ง',
      ));
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
        throw new Error('ไม่พบข้อมูลยืนยันตัวตนจาก LINE กรุณาเริ่มลงทะเบียนผ่าน LINE ใหม่อีกครั้ง');
      }
      if (provider === 'google' && !lineInfo?.email) {
        throw new Error('ไม่พบข้อมูลบัญชี Google กรุณาเริ่มลงทะเบียนผ่าน Google ใหม่อีกครั้ง');
      }
      if (!lineInfo?.registration_token) {
        throw new Error('การยืนยันตัวตนหมดอายุหรือไม่สมบูรณ์ กรุณายืนยันตัวตนใหม่อีกครั้ง');
      }
      const customerFirstName = formData.firstName.trim();
      const customerNickname = formData.nickname.trim();
      if (isCustomerPortal && customerFirstName.length < 2) {
        throw new Error('กรุณากรอกชื่อจริงอย่างน้อย 2 ตัวอักษร');
      }
      if (isCustomerPortal && !customerNickname) {
        throw new Error('กรุณากรอกชื่อเล่น');
      }

      const response = await submitAccessRequest({
        provider,
        registrationToken: lineInfo.registration_token,
        email: lineInfo.email,
        lineUid: lineInfo.line_uid,
        pictureUrl: lineInfo.picture_url || lineInfo.line_picture_url,
        displayName: lineInfo.display_name,
        requestedAccountType: formData.requestedAccountType,
        companyName: formData.name,
        firstName: isCustomerPortal ? customerFirstName : '',
        nickname: isCustomerPortal ? customerNickname : '',
        contactName: isCustomerPortal ? customerFirstName : formData.contactName,
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
      setError(getThaiSignupError(
        submitError,
        'ไม่สามารถส่งคำขอลงทะเบียนได้ กรุณาตรวจสอบข้อมูลแล้วลองอีกครั้ง',
      ));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={`signup-page${isCustomerPortal ? ' customer-signup-page' : ''}`} lang="th">
      <section className={`signup-card${isCustomerPortal ? ' customer-signup-shell' : ''}`} aria-labelledby="signup-title">
        <div className="signup-brand">
          <img className="signup-brand-logo" src={logoImage} alt="DOUBLEBO" />
        </div>

        <div className="signup-content">
          <header className="signup-intro">
            <span className="signup-eyebrow">{isCustomerPortal ? 'สำหรับลูกค้า' : 'สร้างบัญชีผู้ใช้งาน'}</span>
            <h1 id="signup-title">
              {isCustomerPortal ? 'เริ่มต้นใช้งาน RAYADEE' : 'ลงทะเบียนเพื่อเข้าใช้งานระบบ'}
            </h1>
            <p>
              {isCustomerPortal
                ? 'ยืนยันข้อมูลเล็กน้อย เพื่อให้ผู้ดูแลเชื่อมบัญชีของคุณกับโครงการ'
                : 'กรอกข้อมูลติดต่อเพื่อส่งให้ผู้ดูแลตรวจสอบ คุณจะเข้าใช้งานระบบได้หลังจากได้รับอนุมัติ'}
            </p>
          </header>

          {hasVerifiedIdentity && !isCustomerPortal ? (
            <div className="signup-identity-summary" aria-live="polite">
              <ShieldCheck aria-hidden="true" size={18} />
              <span>
                ยืนยันตัวตนด้วย <strong>{providerLabel}</strong> แล้ว: <strong>{identityLabel}</strong>
              </span>
            </div>
          ) : null}

          {error ? (
            <div className="signup-error" role="alert">
              {error}
            </div>
          ) : null}

          {!hasVerifiedIdentity ? (
            <section
              className={`signup-identity-panel${isCustomerPortal ? ' customer-line-panel' : ''}`}
              aria-labelledby="signup-identity-title"
            >
              <div className="signup-identity-heading">
                <div className="signup-identity-icon">
                  <ShieldCheck aria-hidden="true" size={22} />
                </div>
                <div>
                  <h2 id="signup-identity-title">
                    {isCustomerPortal ? 'ยืนยันตัวตนผ่าน LINE' : 'ยืนยันตัวตน'}
                  </h2>
                  <p>
                    {isCustomerPortal
                      ? 'ระบบจะใช้ชื่อและรูปโปรไฟล์จาก LINE เพื่อสร้างคำขอเข้าใช้งานอย่างปลอดภัย'
                      : 'เลือกยืนยันตัวตนด้วย Google หรือ LINE ก่อนกรอกข้อมูลและส่งคำขอให้ผู้ดูแลอนุมัติ'}
                  </p>
                </div>
              </div>

              <div className="signup-identity-actions identity-choice-grid">
                {!isCustomerPortal ? (
                  <button
                    className="signup-identity-button"
                    type="button"
                    onClick={handleGoogleIdentity}
                    disabled={identityLoadingAction !== ''}
                    aria-busy={identityLoadingAction === 'google'}
                  >
                    <ShieldCheck aria-hidden="true" size={18} />
                    {identityLoadingAction === 'google' ? 'กำลังยืนยันด้วย Google...' : 'ลงทะเบียนด้วย Google'}
                  </button>
                ) : null}

                <button
                  className="signup-identity-button is-line"
                  type="button"
                  onClick={handleLineIdentity}
                  disabled={identityLoadingAction !== ''}
                  aria-busy={identityLoadingAction === 'line'}
                >
                  <Smartphone aria-hidden="true" size={18} />
                  {identityLoadingAction === 'line'
                    ? 'กำลังเชื่อมต่อ LINE...'
                    : isCustomerPortal ? 'ดำเนินการต่อด้วย LINE' : 'ลงทะเบียนด้วย LINE'}
                </button>
              </div>
            </section>
          ) : isCustomerPortal ? (
            <CustomerAccessRequestForm
              formData={formData}
              lineInfo={lineInfo}
              loading={loading}
              onChange={handleChange}
              onSubmit={handleSignUp}
            />
          ) : (
            <form onSubmit={handleSignUp} className="signup-form subcon-signup-form">
              <div className="signup-section-title">
                <Building2 aria-hidden="true" size={20} />
                <h2>ข้อมูลผู้สมัคร</h2>
              </div>

              <SignupFormField id="signup-access-type" label="ประเภทการเข้าใช้งานที่ต้องการ" icon={Building2}>
                <select
                  id="signup-access-type"
                  value={formData.requestedAccountType}
                  onChange={(event) => handleChange('requestedAccountType', event.target.value)}
                >
                  <option value="">ให้ผู้ดูแลระบบเป็นผู้กำหนด</option>
                  <option value="subcontractor">ผู้รับเหมา</option>
                  <option value="customer">ลูกค้า</option>
                  <option value="admin">ผู้ดูแลระบบ / พนักงาน</option>
                </select>
              </SignupFormField>

              <SignupFormField id="signup-company-name" label="ชื่อบริษัท / ชื่อที่ใช้แสดง" icon={User}>
                <input
                  id="signup-company-name"
                  type="text"
                  value={formData.name}
                  onChange={(event) => handleChange('name', event.target.value)}
                  placeholder="บริษัท ตัวอย่างก่อสร้าง จำกัด"
                  autoComplete="organization"
                  required
                />
              </SignupFormField>

              <SignupFormField id="signup-contact-name" label="ชื่อผู้ติดต่อหลัก" icon={User}>
                <input
                  id="signup-contact-name"
                  type="text"
                  value={formData.contactName}
                  onChange={(event) => handleChange('contactName', event.target.value)}
                  placeholder="สมชาย ใจดี"
                  autoComplete="name"
                  required
                />
              </SignupFormField>

              <SignupFormField id="signup-phone" label="เบอร์โทรศัพท์" icon={Phone}>
                <input
                  id="signup-phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(event) => handleChange('phone', event.target.value)}
                  placeholder="0812345678"
                  autoComplete="tel"
                  inputMode="tel"
                />
              </SignupFormField>

              <SignupFormField id="signup-tax-id" label="เลขประจำตัวผู้เสียภาษี" icon={IdCard}>
                <input
                  id="signup-tax-id"
                  type="text"
                  value={formData.taxId}
                  onChange={(event) => handleChange('taxId', event.target.value)}
                  placeholder="1234567890123"
                  inputMode="numeric"
                />
              </SignupFormField>

              <div className="signup-section-title">
                <Landmark aria-hidden="true" size={20} />
                <h2>ข้อมูลบัญชีธนาคาร</h2>
              </div>

              <SignupFormField id="signup-bank-name" label="ชื่อธนาคาร" icon={Landmark}>
                <input
                  id="signup-bank-name"
                  type="text"
                  value={formData.bankName}
                  onChange={(event) => handleChange('bankName', event.target.value)}
                  placeholder="ธนาคารกรุงเทพ"
                  autoComplete="off"
                />
              </SignupFormField>

              <SignupFormField id="signup-account-number" label="เลขที่บัญชี" icon={Landmark}>
                <input
                  id="signup-account-number"
                  type="text"
                  value={formData.accountNo}
                  onChange={(event) => handleChange('accountNo', event.target.value)}
                  placeholder="123-4-56789-0"
                  inputMode="numeric"
                />
              </SignupFormField>

              <SignupFormField id="signup-account-name" label="ชื่อบัญชี" icon={User}>
                <input
                  id="signup-account-name"
                  type="text"
                  value={formData.accountName}
                  onChange={(event) => handleChange('accountName', event.target.value)}
                  placeholder="นายสมชาย ใจดี"
                  autoComplete="off"
                />
              </SignupFormField>

              <div className="signup-section-title">
                <FileBadge2 aria-hidden="true" size={20} />
                <h2>การยืนยันตัวตน</h2>
              </div>

              <div className="signup-kyc-field">
                <label className="signup-field-label" htmlFor="signup-kyc-image">รูปบัตรประชาชนสำหรับยืนยันตัวตน (KYC)</label>
                <div className="signup-kyc-dropzone">
                  <div className="signup-kyc-description">
                    <FileBadge2 aria-hidden="true" size={19} />
                    <span>อัปโหลดรูปบัตรประชาชน ระบบจะจัดเก็บไฟล์แบบส่วนตัวเพื่อให้ผู้ดูแลตรวจสอบเท่านั้น</span>
                  </div>
                  <div className="signup-file-picker">
                    <input
                      id="signup-kyc-image"
                      className="signup-file-input"
                      type="file"
                      accept="image/*"
                      onChange={(event) => handleChange('kycImage', event.target.files?.[0] || null)}
                    />
                    <label className="signup-file-button" htmlFor="signup-kyc-image">
                      เลือกรูปบัตรประชาชน
                    </label>
                  </div>
                  {formData.kycImage ? (
                    <div className="signup-selected-file" aria-live="polite">
                      ไฟล์ที่เลือก: <strong>{formData.kycImage.name}</strong>
                    </div>
                  ) : null}
                </div>
              </div>

              <button className="signup-submit-button" type="submit" disabled={loading} aria-busy={loading}>
                <span>{loading ? 'กำลังส่งคำขอ...' : 'ส่งคำขอเพื่อรออนุมัติ'}</span>
                <ArrowRight aria-hidden="true" size={18} />
              </button>
            </form>
          )}

          <div className="signup-login-link">
            <Link to={isCustomerPortal ? '/login?portal=customer' : '/login'} onClick={() => clearPendingLineAuth()}>
              <ArrowLeft aria-hidden="true" size={16} />
              กลับไปหน้าเข้าสู่ระบบ
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
};

export default SignUpPage;
