import React, { useEffect, useRef, useState } from 'react';
import {
  Briefcase,
  Camera,
  CheckCircle,
  Clock,
  DollarSign,
  Edit3,
  IdCard,
  Landmark,
  Phone,
  RotateCcw,
  Save,
  TrendingUp,
  User,
  Users,
  X,
} from 'lucide-react';
import {
  ComposedChart,
  LineChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { fetchData, resetProfileAvatar, updateCurrentProfile, uploadProfileAvatar } from './api';
import { updateStoredAuthUser } from './auth';
import Loading from './components/Loading';

const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

const cardStyle = {
  backgroundColor: 'var(--card-bg)',
  borderRadius: '12px',
  padding: '24px',
  boxShadow: 'none',
  border: '1px solid var(--border-color)',
};

const labelStyle = {
  display: 'block',
  marginBottom: '8px',
  fontSize: '12px',
  fontWeight: '700',
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
};

const inputStyle = {
  width: '100%',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '11px 12px',
  fontSize: '14px',
  color: 'var(--text-main)',
  backgroundColor: '#fff',
  outlineColor: 'var(--primary)',
  boxSizing: 'border-box',
};

const buttonStyle = (variant = 'secondary') => ({
  minHeight: '40px',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '8px',
  padding: '10px 14px',
  borderRadius: '8px',
  border: variant === 'primary' ? '1px solid var(--primary)' : '1px solid var(--secondary)',
  backgroundColor: variant === 'primary' ? 'var(--primary)' : 'var(--card-bg)',
  color: variant === 'primary' ? '#fff' : 'var(--secondary)',
  cursor: 'pointer',
  fontWeight: '700',
  fontSize: '13px',
});

const disabledButtonStyle = {
  opacity: 0.62,
  cursor: 'not-allowed',
};

const iconMap = {
  active_projects: Briefcase,
  pending_approvals: Clock,
  completed_tasks: CheckCircle,
  team_members: Users,
  reports_generated: TrendingUp,
  budget_managed: DollarSign,
};

const chartFieldKeys = {
  income: ['Income', 'income', 'Incomes', 'incomes', 'Revenue', 'revenue', 'actualIncome', 'actual_income', 'totalIncome', 'total_income'],
  expenses: ['Expenses', 'expenses', 'Expense', 'expense', 'actualExpense', 'actual_expense', 'totalExpense', 'total_expense'],
  activity: ['Activity', 'activity', 'Requests', 'requests', 'request_count', 'requestCount', 'count'],
  netCashFlow: ['NetCashFlow', 'netCashFlow', 'net_cashflow', 'netCashflow', 'Net', 'net', 'Balance', 'balance'],
};

const subcontractorStatCopy = {
  active_projects: {
    label: 'โครงการที่ใช้งานอยู่',
    subtext: 'โครงการที่สามารถเลือกส่งรายการได้',
  },
  pending_approvals: {
    label: 'รอตรวจสอบ',
    subtext: 'คำขอที่ส่งแล้วและกำลังรอผู้ดูแลตรวจสอบ',
  },
  completed_tasks: {
    label: 'รายการสำเร็จ',
    subtext: 'คำขอที่อนุมัติหรือจ่ายเงินแล้ว',
  },
  team_members: {
    label: 'คำขอของฉัน',
    subtext: 'จำนวนคำขอทั้งหมดของบัญชีนี้',
  },
  reports_generated: {
    label: 'อัตรา VAT',
    subtext: 'อัตราภาษีที่บันทึกไว้ในโปรไฟล์',
  },
  budget_managed: {
    label: 'ยอดที่อนุมัติแล้ว',
    subtext: 'ยอดรวมของคำขอที่อนุมัติหรือจ่ายเงินแล้ว',
  },
};

const localizeSubcontractorStats = (stats = []) =>
  stats.map((stat) => ({
    ...stat,
    label: subcontractorStatCopy[stat.id]?.label || stat.label,
    subtext: subcontractorStatCopy[stat.id]?.subtext || stat.subtext,
  }));

const toChartNumber = (value) => {
  if (value == null || value === '') return 0;
  const normalized = typeof value === 'string' ? value.replace(/[^\d.-]/g, '') : value;
  const numberValue = Number(normalized);
  return Number.isFinite(numberValue) ? numberValue : 0;
};

const pickChartNumber = (item, keys) => {
  for (const key of keys) {
    if (item?.[key] != null && item?.[key] !== '') {
      return toChartNumber(item[key]);
    }
  }
  return null;
};

const normalizeProfileChartData = (rows = []) => {
  if (!Array.isArray(rows)) return [];

  return rows.map((item) => {
    const income = pickChartNumber(item, chartFieldKeys.income) ?? 0;
    const expenses = pickChartNumber(item, chartFieldKeys.expenses) ?? 0;
    const activity = pickChartNumber(item, chartFieldKeys.activity) ?? 0;
    const providedNetCashFlow = pickChartNumber(item, chartFieldKeys.netCashFlow);

    return {
      ...item,
      name: item?.name || item?.month || item?.label || '',
      Income: income,
      Expenses: expenses,
      Activity: activity,
      NetCashFlow: providedNetCashFlow ?? income - expenses,
    };
  });
};

const formatCompactNumber = (value) =>
  new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(toChartNumber(value));

const formatWholeNumber = (value) =>
  new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(toChartNumber(value));

const isSubcontractorUser = (user = {}) =>
  String(user?.role_key || user?.role || '').trim().toLowerCase() === 'subcontractor';

const buildInitials = (value) => {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return 'U';
  return words.slice(0, 2).map((word) => word.charAt(0).toUpperCase()).join('');
};

const findStat = (stats, id) => stats.find((stat) => stat.id === id);

const buildProfileForm = (user = {}) => ({
  displayName: user.display_name || user.name || user.contact_name || '',
  contactName: user.contact_name || user.name || user.display_name || '',
  phone: user.phone || '',
  company: user.company || '',
  time: user.time || 'Asia/Bangkok',
  bankName: user.bank_account?.bank_name || '',
  accountNo: user.bank_account?.account_no || '',
  accountName: user.bank_account?.account_name || '',
});

const hasBankDetails = (user = {}) => {
  const bankAccount = user.bank_account || {};
  return Boolean(bankAccount.bank_name || bankAccount.account_no || bankAccount.account_name);
};

const resolveUpdatedUser = (currentUser, response, form) => {
  const responseUser = response?.user || response?.profile || response || {};
  return {
    ...currentUser,
    ...responseUser,
    display_name: responseUser.display_name ?? form.displayName,
    name: responseUser.name ?? form.displayName,
    contact_name: responseUser.contact_name ?? form.contactName,
    phone: responseUser.phone ?? form.phone,
    company: responseUser.company ?? form.company,
    time: responseUser.time ?? form.time,
    bank_account: responseUser.bank_account ?? {
      ...(currentUser.bank_account || {}),
      bank_name: form.bankName,
      account_no: form.accountNo,
      account_name: form.accountName,
    },
  };
};

const syncStoredProfileUser = (user = {}) => {
  updateStoredAuthUser({
    display_name: user.display_name || user.name || user.contact_name || '',
    email: user.email || '',
    role: user.role_key || user.role || '',
    profile_image_url: user.profile_image_url || '',
    line_picture_url: user.line_picture_url || '',
    avatar_url: user.avatar_url || '',
  });
};

const StatCard = ({ value, label, subtext, icon }) => {
  const IconComponent = icon;

  return (
    <div style={{ ...cardStyle, display: 'flex', flexDirection: 'column', gap: '18px', minHeight: '168px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--text-main)', marginBottom: '4px' }}>
            {value}
          </div>
          <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-main)' }}>{label}</div>
        </div>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '12px',
          backgroundColor: 'rgba(79, 111, 100, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--primary)',
          flex: '0 0 auto',
        }}>
          {IconComponent ? <IconComponent size={22} /> : null}
        </div>
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>{subtext}</div>
    </div>
  );
};

const AvatarCircle = ({ name, imageUrl, size = 120 }) => (
  <div style={{
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: '50%',
    backgroundColor: 'rgba(79, 111, 100, 0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--primary)',
    border: '4px solid var(--card-bg)',
    boxShadow: '0 0 0 2px #d7e3dd',
    overflow: 'hidden',
    flex: '0 0 auto',
  }}>
    {imageUrl ? (
      <img
        src={imageUrl}
        alt={name || 'Profile avatar'}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
    ) : (
      <span style={{ fontSize: `${Math.round(size * 0.28)}px`, fontWeight: '700' }}>
        {buildInitials(name)}
      </span>
    )}
  </div>
);

const DetailRow = ({ label, value }) => (
  <div style={{ display: 'grid', gap: '4px' }}>
    <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
      {label}
    </div>
    <div style={{ fontSize: '14px', color: 'var(--text-main)', fontWeight: '600', wordBreak: 'break-word' }}>
      {value || '-'}
    </div>
  </div>
);

const DetailPanel = ({ title, icon, actions, children }) => {
  const IconComponent = icon;

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', marginBottom: '18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            backgroundColor: 'rgba(79, 111, 100, 0.1)',
            color: 'var(--primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: '0 0 auto',
          }}>
            <IconComponent size={19} />
          </div>
          <h2 style={{ fontSize: '18px', margin: 0, color: 'var(--text-main)' }}>{title}</h2>
        </div>
        {actions ? <div style={{ flex: '0 0 auto' }}>{actions}</div> : null}
      </div>
      <div style={{ display: 'grid', gap: '16px' }}>
        {children}
      </div>
    </div>
  );
};

const EditableField = ({ label, value, onChange, type = 'text', readOnly = false }) => (
  <label style={{ display: 'grid' }}>
    <span style={labelStyle}>{label}</span>
    <input
      type={type}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      style={{
        ...inputStyle,
        backgroundColor: readOnly ? 'var(--bg-primary)' : '#fff',
        color: readOnly ? 'var(--text-muted)' : 'var(--text-main)',
      }}
      readOnly={readOnly}
    />
  </label>
);

const StatusMessage = ({ tone = 'neutral', children }) => {
  if (!children) return null;
  const toneStyle = tone === 'danger'
    ? { backgroundColor: '#fef2f2', borderColor: '#fecaca', color: '#b91c1c' }
    : { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' };

  return (
    <div
      style={{
        ...toneStyle,
        border: `1px solid ${toneStyle.borderColor}`,
        borderRadius: '8px',
        padding: '10px 12px',
        fontSize: '13px',
        fontWeight: '700',
      }}
    >
      {children}
    </div>
  );
};

const ProfilePage = () => {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [avatarSaving, setAvatarSaving] = useState(false);
  const [avatarError, setAvatarError] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [profileForm, setProfileForm] = useState(buildProfileForm());
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [profileError, setProfileError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('profile');
      if (Array.isArray(result) && result.length === 0) {
        setProfileData(null);
      } else {
        setProfileData(result);
        if (result?.user) {
          syncStoredProfileUser(result.user);
        }
      }
      setLoading(false);
    };
    loadData();
  }, []);

  useEffect(() => {
    if (!profileData?.user || isEditing) return;
    setProfileForm(buildProfileForm(profileData.user));
  }, [isEditing, profileData?.user]);

  const useThaiProfileCopy = isSubcontractorUser(profileData?.user);

  const handlePickAvatar = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setAvatarError(useThaiProfileCopy ? 'กรุณาเลือกไฟล์รูปภาพ' : 'Please choose an image file.');
      event.target.value = '';
      return;
    }

    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError(useThaiProfileCopy ? 'รูปโปรไฟล์ต้องมีขนาดไม่เกิน 5MB' : 'Profile photo must be 5MB or smaller.');
      event.target.value = '';
      return;
    }

    try {
      setAvatarSaving(true);
      setAvatarError('');
      const response = await uploadProfileAvatar(file);
      setProfileData((current) => {
        if (!current?.user) return current;
        const updatedUser = {
          ...current.user,
          profile_image_url: response?.profile_image_url || '',
          line_picture_url: response?.line_picture_url || current.user.line_picture_url || '',
          avatar_url: response?.avatar_url || '',
        };
        syncStoredProfileUser(updatedUser);
        return {
          ...current,
          user: updatedUser,
        };
      });
    } catch (error) {
      setAvatarError(error.message || (useThaiProfileCopy ? 'อัปโหลดรูปโปรไฟล์ไม่สำเร็จ' : 'Failed to upload profile avatar.'));
    } finally {
      setAvatarSaving(false);
      if (event.target) {
        event.target.value = '';
      }
    }
  };

  const handleResetAvatar = async () => {
    try {
      setAvatarSaving(true);
      setAvatarError('');
      const response = await resetProfileAvatar();
      setProfileData((current) => {
        if (!current?.user) return current;
        const updatedUser = {
          ...current.user,
          profile_image_url: '',
          line_picture_url: response?.line_picture_url || current.user.line_picture_url || '',
          avatar_url: response?.avatar_url || response?.line_picture_url || '',
        };
        syncStoredProfileUser(updatedUser);
        return {
          ...current,
          user: updatedUser,
        };
      });
    } catch (error) {
      setAvatarError(error.message || (useThaiProfileCopy ? 'รีเซ็ตรูปโปรไฟล์ไม่สำเร็จ' : 'Failed to reset profile avatar.'));
    } finally {
      setAvatarSaving(false);
    }
  };

  const updateProfileField = (field) => (value) => {
    setProfileForm((current) => ({ ...current, [field]: value }));
    setProfileMessage('');
    setProfileError('');
  };

  const handleStartEditing = () => {
    setProfileForm(buildProfileForm(profileData?.user));
    setProfileMessage('');
    setProfileError('');
    setIsEditing(true);
  };

  const handleCancelEditing = () => {
    setProfileForm(buildProfileForm(profileData?.user));
    setProfileMessage('');
    setProfileError('');
    setIsEditing(false);
  };

  const handleSaveProfile = async () => {
    if (!profileData?.user) return;

    const currentUser = profileData.user;
    const payload = {
      display_name: profileForm.displayName.trim(),
      name: profileForm.displayName.trim(),
      contact_name: profileForm.contactName.trim(),
      phone: profileForm.phone.trim(),
      company: profileForm.company.trim(),
      time: profileForm.time.trim(),
      bank_account: {
        bank_name: profileForm.bankName.trim(),
        account_no: profileForm.accountNo.trim(),
        account_name: profileForm.accountName.trim(),
      },
    };

    try {
      setProfileSaving(true);
      setProfileMessage('');
      setProfileError('');
      const response = await updateCurrentProfile(payload);
      const updatedUser = resolveUpdatedUser(currentUser, response, {
        ...profileForm,
        displayName: payload.display_name,
        contactName: payload.contact_name,
        phone: payload.phone,
        company: payload.company,
        time: payload.time,
      });

      setProfileData((current) => ({
        ...current,
        ...(response?.stats ? { stats: response.stats } : {}),
        ...(response?.chartData ? { chartData: response.chartData } : {}),
        user: updatedUser,
      }));
      setProfileForm(buildProfileForm(updatedUser));
      syncStoredProfileUser(updatedUser);
      setIsEditing(false);
      setProfileMessage(useThaiProfileCopy ? 'บันทึกโปรไฟล์เรียบร้อยแล้ว' : 'Profile updated.');
    } catch (error) {
      setProfileError(error.message || (useThaiProfileCopy ? 'บันทึกโปรไฟล์ไม่สำเร็จ' : 'Failed to update profile.'));
    } finally {
      setProfileSaving(false);
    }
  };

  if (loading) return <Loading />;

  if (!profileData || !profileData.user) {
    return (
      <div style={{ maxWidth: '1400px', margin: '0 auto', textAlign: 'center', padding: '100px 20px' }}>
        <h2 style={{ fontSize: '24px', color: 'var(--text-main)', marginBottom: '16px' }}>
          กำลังรอเชื่อมต่อข้อมูลจาก Backend...
        </h2>
        <p style={{ color: 'var(--text-muted)' }}>หน้าต่างโปรไฟล์จะแสดงข้อมูลของคุณเมื่อ API พร้อมใช้งาน</p>
      </div>
    );
  }

  const user = profileData.user;
  const baseStats = Array.isArray(profileData.stats) ? profileData.stats : [];
  const bankAccount = user.bank_account || {};
  const roleLabel = user.role || 'User';
  const isSubcontractor = isSubcontractorUser(user);
  const stats = isSubcontractor ? localizeSubcontractorStats(baseStats) : baseStats;
  const approvedStat = findStat(stats, 'budget_managed');
  const pendingStat = findStat(stats, 'pending_approvals');
  const assignedProjectIds = Array.isArray(user.assigned_project_ids)
    ? user.assigned_project_ids.filter(Boolean)
    : [];
  const profileName = user.display_name || user.contact_name || user.name;
  const avatarUrl = user.profile_image_url || user.line_picture_url || user.avatar_url;
  const hasProfileBankDetails = hasBankDetails(user);
  const displayRoleLabel = isSubcontractor ? 'ผู้รับเหมา' : roleLabel;
  const fallbackCompany = isSubcontractor ? 'พื้นที่ผู้รับเหมา' : 'Manee Son Construction';
  const displayCompany =
    isSubcontractor && (!user.company || user.company === 'Subcontractor Portal')
      ? fallbackCompany
      : user.company || fallbackCompany;
  const uploadPhotoLabel = avatarSaving
    ? isSubcontractor ? 'กำลังอัปโหลด...' : 'Uploading...'
    : isSubcontractor ? 'เปลี่ยนรูป' : 'Change Photo';
  const editProfileLabel = isEditing
    ? isSubcontractor ? 'กำลังแก้ไข' : 'Editing'
    : isSubcontractor ? 'แก้ไขโปรไฟล์' : 'Edit Profile';
  const saveProfileLabel = profileSaving
    ? isSubcontractor ? 'กำลังบันทึก...' : 'Saving...'
    : isSubcontractor ? 'บันทึก' : 'Save';
  const bankingStatusText = hasProfileBankDetails
    ? isSubcontractor ? 'พร้อมใช้สำหรับข้อมูลการโอนเงิน' : 'Available for transfer records'
    : isSubcontractor ? 'ยังไม่ได้กรอกข้อมูล' : 'Not provided';
  const profileChartData = normalizeProfileChartData(profileData.chartData || []);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '8px', fontWeight: '700', color: 'var(--text-main)' }}>
          {isSubcontractor ? 'โปรไฟล์ของฉัน' : 'My Profile'}
        </h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          {isSubcontractor
            ? 'ข้อมูลติดต่อ บัญชีธนาคาร และข้อมูลที่ระบบใช้กรอกอัตโนมัติ'
            : 'Account identity, work context, and profile defaults used across the portal.'}
        </p>
      </div>

      <div className="profile-hero-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(300px, 0.65fr)', gap: '24px' }}>
        <div style={{ ...cardStyle, display: 'flex', gap: '24px', alignItems: 'center' }}>
          <AvatarCircle name={profileName} imageUrl={avatarUrl} size={120} />

          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--primary)', marginBottom: '6px' }}>
              {displayRoleLabel}
            </div>
            <h2 style={{ fontSize: '26px', margin: 0, color: 'var(--text-main)' }}>
              {user.display_name || user.name || user.contact_name || (isSubcontractor ? 'ไม่พบชื่อผู้ใช้' : 'Unknown')}
            </h2>
            <div style={{ color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.5 }}>
              {displayCompany}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleAvatarChange}
            />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '18px' }}>
              <button
                type="button"
                onClick={handlePickAvatar}
                disabled={avatarSaving}
                style={{
                  ...buttonStyle('primary'),
                  ...(avatarSaving ? disabledButtonStyle : {}),
                  cursor: avatarSaving ? 'wait' : 'pointer',
                }}
              >
                <Camera size={16} />
                {uploadPhotoLabel}
              </button>
              {avatarUrl ? (
                <button
                  type="button"
                  onClick={handleResetAvatar}
                  disabled={avatarSaving}
                  style={{
                    ...buttonStyle('secondary'),
                    ...(avatarSaving ? disabledButtonStyle : {}),
                    cursor: avatarSaving ? 'wait' : 'pointer',
                  }}
                >
                  <RotateCcw size={16} />
                  {isSubcontractor ? 'ใช้รูปจาก LINE' : 'Remove Photo'}
                </button>
              ) : null}
              <button
                type="button"
                onClick={handleStartEditing}
                disabled={profileSaving || isEditing}
                style={{
                  ...buttonStyle('secondary'),
                  ...(profileSaving || isEditing ? disabledButtonStyle : {}),
                }}
              >
                <Edit3 size={16} />
                {editProfileLabel}
              </button>
            </div>
            {avatarError ? (
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#b42318' }}>{avatarError}</div>
            ) : null}
          </div>
        </div>

        <div style={{
          ...cardStyle,
          backgroundColor: 'var(--primary)',
          borderColor: 'var(--primary)',
          color: '#fff',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '220px',
        }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '700', opacity: 0.75, marginBottom: '8px' }}>
              {isSubcontractor ? 'ยอดอนุมัติทั้งหมด' : 'Total Approved Amount'}
            </div>
            <div style={{ fontSize: '42px', fontWeight: '800', lineHeight: 1 }}>
              {approvedStat?.value || '-'}
            </div>
          </div>
          <div style={{ display: 'grid', gap: '8px', fontSize: '14px', lineHeight: 1.5 }}>
            <div>{approvedStat?.subtext || (isSubcontractor ? 'คำขอที่อนุมัติหรือจ่ายเงินแล้ว' : 'Approved or paid requests for this subcontractor')}</div>
            <div style={{ opacity: 0.82 }}>
              {isSubcontractor ? 'รอตรวจสอบ' : 'Pending approval'}: <strong>{pendingStat?.value || '0'}</strong>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '10px', marginTop: '18px' }}>
        <StatusMessage>{profileMessage}</StatusMessage>
        <StatusMessage tone="danger">{profileError}</StatusMessage>
      </div>

      <div className="profile-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginTop: '24px' }}>
        {stats.map((stat) => {
          const Icon = iconMap[stat.id] || User;
          return (
            <StatCard
              key={stat.id}
              value={stat.value}
              label={stat.label}
              subtext={stat.subtext}
              icon={Icon}
            />
          );
        })}
      </div>

      <div className="profile-bottom-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(320px, 0.65fr)', gap: '24px', marginTop: '24px' }}>
        <div style={{ ...cardStyle, display: 'flex', flexDirection: 'column', gap: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: '700', margin: 0, color: 'var(--text-main)' }}>
                {isSubcontractor ? 'รายรับและรายจ่าย' : 'Income vs Expenses'}
              </h2>
              <div style={{ color: 'var(--text-muted)', marginTop: '6px', fontSize: '13px' }}>
                {isSubcontractor ? 'กระแสเงินสดสุทธิจาก 6 เดือนล่าสุดที่มีรายการ' : 'Net cash flow across the last six active months'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--primary)' }}></span> {isSubcontractor ? 'รายรับ' : 'Income'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--secondary)' }}></span> {isSubcontractor ? 'รายจ่าย' : 'Expenses'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '16px', height: '2px', borderRadius: '999px', backgroundColor: 'var(--text-main)' }}></span> {isSubcontractor ? 'สุทธิ' : 'Net'}
              </div>
            </div>
          </div>

          <div style={{ height: '340px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={profileChartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }} dy={10} />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }}
                  tickFormatter={formatCompactNumber}
                  tickMargin={12}
                  width={72}
                />
                <Tooltip
                  cursor={{ fill: '#f8fafc', opacity: 0.8 }}
                  contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: 'none' }}
                  formatter={(value, name) => [formatWholeNumber(value), name]}
                />
                <Bar dataKey="Income" name={isSubcontractor ? 'รายรับ' : 'Income'} fill="#4f6f64" radius={[4, 4, 0, 0]} barSize={12} />
                <Bar dataKey="Expenses" name={isSubcontractor ? 'รายจ่าย' : 'Expenses'} fill="#c2a878" radius={[4, 4, 0, 0]} barSize={12} />
                <Line
                  type="monotone"
                  dataKey="NetCashFlow"
                  name={isSubcontractor ? 'สุทธิ' : 'Net'}
                  stroke="#2f2e2c"
                  strokeWidth={2.25}
                  dot={{ r: 3, fill: '#2f2e2c', strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: '750', margin: 0, color: 'var(--text-main)' }}>
                  {isSubcontractor ? 'จำนวนคำขอ' : 'Request Activity'}
                </h3>
                <div style={{ color: 'var(--text-muted)', marginTop: '4px', fontSize: '12px' }}>
                  {isSubcontractor ? 'ปริมาณรายการที่ส่งในแต่ละเดือน' : 'Monthly submitted request volume'}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#27a57a' }}></span> {isSubcontractor ? 'กิจกรรม' : 'Activity'}
              </div>
            </div>
            <div style={{ height: '150px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={profileChartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }} dy={10} />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }}
                    tickMargin={10}
                    width={44}
                  />
                  <Tooltip
                    cursor={{ stroke: '#d8e2dc', strokeDasharray: '3 3' }}
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: 'none' }}
                    formatter={(value, name) => [formatWholeNumber(value), name]}
                  />
                  <Line
                    type="monotone"
                    dataKey="Activity"
                    name={isSubcontractor ? 'กิจกรรม' : 'Activity'}
                    stroke="#27a57a"
                    strokeWidth={2.25}
                    dot={{ r: 3, fill: '#27a57a', strokeWidth: 0 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gap: '24px' }}>
          <DetailPanel
            title={isSubcontractor ? 'ข้อมูลโปรไฟล์' : 'Profile Information'}
            icon={IdCard}
            actions={
              isEditing ? (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={handleCancelEditing}
                    disabled={profileSaving}
                    style={{ ...buttonStyle('secondary'), ...(profileSaving ? disabledButtonStyle : {}) }}
                  >
                    <X size={16} />
                    {isSubcontractor ? 'ยกเลิก' : 'Cancel'}
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveProfile}
                    disabled={profileSaving}
                    style={{
                      ...buttonStyle('primary'),
                      ...(profileSaving ? disabledButtonStyle : {}),
                      cursor: profileSaving ? 'wait' : 'pointer',
                    }}
                  >
                    <Save size={16} />
                    {saveProfileLabel}
                  </button>
                </div>
              ) : null
            }
          >
            {isEditing ? (
              <>
                <EditableField
                  label={isSubcontractor ? 'ชื่อที่แสดง' : 'Display Name'}
                  value={profileForm.displayName}
                  onChange={updateProfileField('displayName')}
                />
                <EditableField
                  label={isSubcontractor ? 'ชื่อผู้ติดต่อ' : 'Contact Name'}
                  value={profileForm.contactName}
                  onChange={updateProfileField('contactName')}
                />
                <EditableField label={isSubcontractor ? 'เบอร์ติดต่อ' : 'Phone'} value={profileForm.phone} onChange={updateProfileField('phone')} />
                <EditableField
                  label={isSubcontractor ? 'บริษัท / หน่วยงาน' : 'Company / Organization'}
                  value={profileForm.company}
                  onChange={updateProfileField('company')}
                />
                <EditableField label={isSubcontractor ? 'เขตเวลา' : 'Timezone'} value={profileForm.time} onChange={updateProfileField('time')} />
                <EditableField label="Email" value={user.email || ''} onChange={() => {}} readOnly />
              </>
            ) : (
              <>
                <DetailRow label={isSubcontractor ? 'ชื่อที่แสดง' : 'Display Name'} value={user.display_name || user.name} />
                <DetailRow label={isSubcontractor ? 'ชื่อผู้ติดต่อ' : 'Contact Name'} value={user.contact_name || user.name} />
                <DetailRow label={isSubcontractor ? 'เบอร์ติดต่อ' : 'Phone'} value={user.phone} />
                <DetailRow label="Email" value={user.email} />
                {user.line_uid ? <DetailRow label="LINE UID" value={user.line_uid} /> : null}
                <DetailRow
                  label={isSubcontractor ? 'โครงการที่ได้รับมอบหมาย' : 'Assigned Projects'}
                  value={assignedProjectIds.length ? assignedProjectIds.join(', ') : '-'}
                />
              </>
            )}
          </DetailPanel>

          <DetailPanel title={isSubcontractor ? 'ข้อมูลบัญชีธนาคาร' : 'Banking Information'} icon={Landmark}>
            {isEditing ? (
              <>
                <EditableField
                  label={isSubcontractor ? 'ธนาคาร' : 'Bank Name'}
                  value={profileForm.bankName}
                  onChange={updateProfileField('bankName')}
                />
                <EditableField
                  label={isSubcontractor ? 'เลขที่บัญชี' : 'Account Number'}
                  value={profileForm.accountNo}
                  onChange={updateProfileField('accountNo')}
                />
                <EditableField
                  label={isSubcontractor ? 'ชื่อบัญชี' : 'Account Name'}
                  value={profileForm.accountName}
                  onChange={updateProfileField('accountName')}
                />
              </>
            ) : (
              <>
                <DetailRow label={isSubcontractor ? 'ธนาคาร' : 'Bank Name'} value={bankAccount.bank_name} />
                <DetailRow label={isSubcontractor ? 'เลขที่บัญชี' : 'Account Number'} value={bankAccount.account_no} />
                <DetailRow label={isSubcontractor ? 'ชื่อบัญชี' : 'Account Name'} value={bankAccount.account_name} />
                <DetailRow
                  label={isSubcontractor ? 'สถานะข้อมูลบัญชี' : 'Banking Status'}
                  value={bankingStatusText}
                />
              </>
            )}
          </DetailPanel>

          <DetailPanel title={isSubcontractor ? 'สถานะบัญชี' : 'Access Details'} icon={Phone}>
            {isSubcontractor ? (
              <DetailRow label="สถานะ KYC" value="ใช้ลิงก์ส่วนตัวสำหรับตรวจสอบเอกสาร" />
            ) : (
              <DetailRow label="Portal Role" value={roleLabel} />
            )}
            <DetailRow label={isSubcontractor ? 'เขตเวลา' : 'Timezone'} value={user.time || 'Asia/Bangkok'} />
          </DetailPanel>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
