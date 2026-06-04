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
  BarChart,
  Bar,
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
      }
      setLoading(false);
    };
    loadData();
  }, []);

  useEffect(() => {
    if (!profileData?.user || isEditing) return;
    setProfileForm(buildProfileForm(profileData.user));
  }, [isEditing, profileData?.user]);

  const handlePickAvatar = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setAvatarError('Please choose an image file.');
      event.target.value = '';
      return;
    }

    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError('Profile photo must be 5MB or smaller.');
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
      setAvatarError(error.message || 'Failed to upload profile avatar.');
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
      setAvatarError(error.message || 'Failed to reset profile avatar.');
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
    const includeBank = hasBankDetails(currentUser) || String(currentUser.role || '').toLowerCase() === 'subcontractor';
    const payload = {
      display_name: profileForm.displayName.trim(),
      name: profileForm.displayName.trim(),
      contact_name: profileForm.contactName.trim(),
      phone: profileForm.phone.trim(),
      company: profileForm.company.trim(),
      time: profileForm.time.trim(),
      ...(includeBank
        ? {
            bank_account: {
              bank_name: profileForm.bankName.trim(),
              account_no: profileForm.accountNo.trim(),
              account_name: profileForm.accountName.trim(),
            },
          }
        : {}),
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
      setProfileMessage('Profile updated.');
    } catch (error) {
      setProfileError(error.message || 'Failed to update profile.');
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
  const stats = Array.isArray(profileData.stats) ? profileData.stats : [];
  const bankAccount = user.bank_account || {};
  const approvedStat = findStat(stats, 'budget_managed');
  const pendingStat = findStat(stats, 'pending_approvals');
  const assignedProjectIds = Array.isArray(user.assigned_project_ids)
    ? user.assigned_project_ids.filter(Boolean)
    : [];
  const profileName = user.display_name || user.contact_name || user.name;
  const avatarUrl = user.profile_image_url || user.line_picture_url || user.avatar_url;
  const roleLabel = user.role || 'User';
  const normalizedRole = String(user.role || '').trim().toLowerCase();
  const isSubcontractor = normalizedRole === 'subcontractor';
  const shouldShowBankFields = isSubcontractor || hasBankDetails(user);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '8px', fontWeight: '700', color: 'var(--text-main)' }}>
          My Profile
        </h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          Account identity, work context, and profile defaults used across the portal.
        </p>
      </div>

      <div className="profile-hero-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(300px, 0.65fr)', gap: '24px' }}>
        <div style={{ ...cardStyle, display: 'flex', gap: '24px', alignItems: 'center' }}>
          <AvatarCircle name={profileName} imageUrl={avatarUrl} size={120} />

          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--primary)', marginBottom: '6px' }}>
              {roleLabel}
            </div>
            <h2 style={{ fontSize: '26px', margin: 0, color: 'var(--text-main)' }}>
              {user.display_name || user.name || user.contact_name || 'Unknown'}
            </h2>
            <div style={{ color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.5 }}>
              {user.company || (isSubcontractor ? 'Subcontractor Portal' : 'Manee Son Construction')}
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
                {avatarSaving ? 'Uploading...' : 'Change Photo'}
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
                  {isSubcontractor ? 'Use LINE Avatar' : 'Remove Photo'}
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
                {isEditing ? 'Editing' : 'Edit Profile'}
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
              Total Approved Amount
            </div>
            <div style={{ fontSize: '42px', fontWeight: '800', lineHeight: 1 }}>
              {approvedStat?.value || '-'}
            </div>
          </div>
          <div style={{ display: 'grid', gap: '8px', fontSize: '14px', lineHeight: 1.5 }}>
            <div>{approvedStat?.subtext || 'Approved or paid requests for this subcontractor'}</div>
            <div style={{ opacity: 0.82 }}>
              Pending approval: <strong>{pendingStat?.value || '0'}</strong>
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
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: '700', margin: 0, color: 'var(--text-main)' }}>
                Activity vs Expenses
              </h2>
              <div style={{ color: 'var(--text-muted)', marginTop: '6px', fontSize: '13px' }}>
                Last six active months
              </div>
            </div>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#27a57a' }}></span> Activity
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--secondary)' }}></span> Expenses
              </div>
            </div>
          </div>

          <div style={{ height: '320px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={profileData.chartData || []} margin={{ top: 5, right: 0, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'rgba(47,46,44,0.6)' }} />
                <Tooltip
                  cursor={{ fill: '#f8fafc', opacity: 0.8 }}
                  contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: 'none' }}
                />
                <Bar dataKey="Activity" fill="#27a57a" radius={[4, 4, 0, 0]} barSize={12} />
                <Bar dataKey="Expenses" fill="#c2a878" radius={[4, 4, 0, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: 'grid', gap: '24px' }}>
          <DetailPanel
            title="Profile Information"
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
                    Cancel
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
                    {profileSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              ) : null
            }
          >
            {isEditing ? (
              <>
                <EditableField
                  label="Display Name"
                  value={profileForm.displayName}
                  onChange={updateProfileField('displayName')}
                />
                <EditableField
                  label="Contact Name"
                  value={profileForm.contactName}
                  onChange={updateProfileField('contactName')}
                />
                <EditableField label="Phone" value={profileForm.phone} onChange={updateProfileField('phone')} />
                <EditableField
                  label="Company / Organization"
                  value={profileForm.company}
                  onChange={updateProfileField('company')}
                />
                <EditableField label="Timezone" value={profileForm.time} onChange={updateProfileField('time')} />
                <EditableField label="Email" value={user.email || ''} onChange={() => {}} readOnly />
              </>
            ) : (
              <>
                <DetailRow label="Display Name" value={user.display_name || user.name} />
                <DetailRow label="Contact Name" value={user.contact_name || user.name} />
                <DetailRow label="Phone" value={user.phone} />
                <DetailRow label="Email" value={user.email} />
                {user.line_uid ? <DetailRow label="LINE UID" value={user.line_uid} /> : null}
                <DetailRow
                  label="Assigned Projects"
                  value={assignedProjectIds.length ? assignedProjectIds.join(', ') : '-'}
                />
              </>
            )}
          </DetailPanel>

          {shouldShowBankFields ? (
            <DetailPanel title="Bank Account" icon={Landmark}>
              {isEditing ? (
                <>
                  <EditableField
                    label="Bank Name"
                    value={profileForm.bankName}
                    onChange={updateProfileField('bankName')}
                  />
                  <EditableField
                    label="Account Number"
                    value={profileForm.accountNo}
                    onChange={updateProfileField('accountNo')}
                  />
                  <EditableField
                    label="Account Name"
                    value={profileForm.accountName}
                    onChange={updateProfileField('accountName')}
                  />
                </>
              ) : (
                <>
                  <DetailRow label="Bank Name" value={bankAccount.bank_name} />
                  <DetailRow label="Account Number" value={bankAccount.account_no} />
                  <DetailRow label="Account Name" value={bankAccount.account_name} />
                  <DetailRow label="Contact Phone" value={user.phone} />
                </>
              )}
            </DetailPanel>
          ) : null}

          <DetailPanel title={isSubcontractor ? 'Contract Status' : 'Access Details'} icon={Phone}>
            {isSubcontractor ? (
              <DetailRow label="KYC Status" value="Private signed-URL review" />
            ) : (
              <DetailRow label="Portal Role" value={roleLabel} />
            )}
            <DetailRow label="Timezone" value={user.time || 'Asia/Bangkok'} />
          </DetailPanel>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
