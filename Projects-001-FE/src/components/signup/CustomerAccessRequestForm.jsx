import React from 'react';
import { ArrowRight, CheckCircle2, FolderCheck, Smile, User } from 'lucide-react';

import SignupFormField from './SignupFormField';

const CustomerAccessRequestForm = ({
  formData,
  lineInfo,
  loading,
  onChange,
  onSubmit,
}) => {
  const displayName = lineInfo?.display_name || 'บัญชี LINE ของคุณ';
  const profileImage = lineInfo?.picture_url || lineInfo?.line_picture_url || '';
  const fallbackInitial = displayName.trim().charAt(0) || 'R';

  return (
    <form className="customer-access-form" onSubmit={onSubmit}>
      <section className="customer-line-profile" aria-label="บัญชี LINE ที่เชื่อมต่อแล้ว">
        <div className="customer-line-avatar" aria-hidden={!profileImage}>
          {profileImage ? (
            <img src={profileImage} alt={`รูปโปรไฟล์ LINE ของ ${displayName}`} />
          ) : (
            <span aria-hidden="true">{fallbackInitial}</span>
          )}
        </div>

        <div className="customer-line-details">
          <span className="customer-line-status">
            <CheckCircle2 aria-hidden="true" size={14} />
            เชื่อมต่อ LINE แล้ว
          </span>
          <strong>{displayName}</strong>
          <span>ใช้บัญชีนี้สำหรับรับข่าวสารและดูรายงานโครงการ</span>
        </div>
      </section>

      <div className="customer-form-heading">
        <h2>อยากให้เราเรียกคุณว่าอะไร</h2>
        <p>กรอกเพียงชื่อจริงและชื่อเล่น ใช้เวลาไม่ถึง 1 นาที</p>
      </div>

      <div className="customer-field-stack">
        <SignupFormField id="customer-first-name" label="ชื่อจริง" icon={User}>
          <input
            id="customer-first-name"
            type="text"
            value={formData.firstName}
            onChange={(event) => onChange('firstName', event.target.value)}
            placeholder="เช่น สมชาย (ไม่ต้องใส่นามสกุล)"
            autoComplete="given-name"
            minLength={2}
            maxLength={80}
            required
          />
        </SignupFormField>

        <SignupFormField id="customer-nickname" label="ชื่อเล่น" icon={Smile}>
          <input
            id="customer-nickname"
            type="text"
            value={formData.nickname}
            onChange={(event) => onChange('nickname', event.target.value)}
            placeholder="เช่น ชาย"
            autoComplete="nickname"
            maxLength={40}
            required
          />
        </SignupFormField>
      </div>

      <aside className="customer-assignment-note">
        <FolderCheck aria-hidden="true" size={21} />
        <p>
          <strong>ยังไม่ต้องเลือกโครงการ</strong>
          <span>ผู้ดูแลจะตรวจสอบและเชื่อมบัญชีของคุณกับโครงการที่ถูกต้องหลังอนุมัติ</span>
        </p>
      </aside>

      <button
        className="signup-submit-button customer-submit-button"
        type="submit"
        disabled={loading}
        aria-busy={loading}
      >
        <span>{loading ? 'กำลังส่งคำขอ...' : 'ส่งคำขอเข้าใช้งาน'}</span>
        <ArrowRight aria-hidden="true" size={18} />
      </button>
    </form>
  );
};

export default CustomerAccessRequestForm;
