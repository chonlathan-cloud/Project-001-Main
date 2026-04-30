import React, { useEffect, useState } from 'react';
import {
  createSettingAdmin,
  getInputProjectOptions,
  getSettingAdmins,
  getSettingSubcontractorKycUrl,
  getSettingSubcontractors,
  resetSettingSubcontractorLine,
  updateSettingAdmin,
  updateSettingSubcontractor,
} from './api';
import Loading from './components/Loading';

const sectionCardStyle = {
  backgroundColor: 'var(--card-bg)',
  borderRadius: '24px',
  border: '1px solid var(--border-color)',
  boxShadow: '0 8px 24px rgba(15, 23, 42, 0.04)',
};

const inputStyle = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: '12px',
  border: '1px solid var(--border-color)',
  backgroundColor: '#fff',
  fontSize: '14px',
  outline: 'none',
};

const labelStyle = {
  display: 'block',
  fontSize: '12px',
  fontWeight: '700',
  color: 'var(--text-muted)',
  marginBottom: '6px',
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
};

const buttonStyle = (tone = 'primary') => ({
  border: tone === 'ghost' ? '1px solid var(--border-color)' : 'none',
  backgroundColor: tone === 'primary' ? 'var(--accent-gold)' : tone === 'danger' ? '#e85d4d' : '#fff',
  color: tone === 'ghost' ? 'var(--text-main)' : '#fff',
  borderRadius: '12px',
  padding: '12px 14px',
  fontWeight: '700',
  cursor: 'pointer',
});

const emptyBank = {
  bank_name: '',
  account_no: '',
  account_name: '',
};

const buildInitials = (value) => {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return 'U';
  return words.slice(0, 2).map((word) => word.charAt(0).toUpperCase()).join('');
};

const AvatarCircle = ({ name, imageUrl, size = 44 }) => (
  <div
    style={{
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: '50%',
      backgroundColor: '#f8f2e6',
      color: 'var(--accent-gold)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: '700',
      fontSize: `${Math.round(size * 0.34)}px`,
      overflow: 'hidden',
      border: '1px solid var(--border-color)',
      flexShrink: 0,
    }}
  >
    {imageUrl ? (
      <img
        src={imageUrl}
        alt={name || 'Avatar'}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
    ) : (
      <span>{buildInitials(name)}</span>
    )}
  </div>
);

function SettingPage() {
  const [subcontractors, setSubcontractors] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [selectedSubId, setSelectedSubId] = useState('');
  const [selectedAdminId, setSelectedAdminId] = useState('');
  const [subForm, setSubForm] = useState({
    name: '',
    contact_name: '',
    phone: '',
    tax_id: '',
    assigned_project_ids: [],
    vat_rate: 0,
    wht_rate: 0,
    retention_rate: 0,
    bank_account: { ...emptyBank },
    is_active: true,
  });
  const [adminForm, setAdminForm] = useState({
    email: '',
    display_name: '',
    is_active: true,
  });

  const loadPage = async () => {
    setLoading(true);
    setError('');
    try {
      const [subItems, adminItems, projectItems] = await Promise.all([
        getSettingSubcontractors(),
        getSettingAdmins().catch(() => []),
        getInputProjectOptions().catch(() => []),
      ]);

      setSubcontractors(subItems);
      setAdmins(adminItems);
      setProjects(projectItems);

      if (subItems.length > 0) {
        const selected = subItems[0];
        setSelectedSubId(selected.id);
        setSubForm({
          name: selected.name || '',
          contact_name: selected.contact_name || '',
          phone: selected.phone || '',
          tax_id: selected.tax_id || '',
          assigned_project_ids: Array.isArray(selected.assigned_project_ids) ? selected.assigned_project_ids : [],
          vat_rate: selected.vat_rate ?? 0,
          wht_rate: selected.wht_rate ?? 0,
          retention_rate: selected.retention_rate ?? 0,
          bank_account: {
            bank_name: selected.bank_account?.bank_name || '',
            account_no: selected.bank_account?.account_no || '',
            account_name: selected.bank_account?.account_name || '',
          },
          is_active: selected.is_active !== false,
        });
      }

      if (adminItems.length > 0) {
        const selectedAdmin = adminItems[0];
        setSelectedAdminId(selectedAdmin.id);
        setAdminForm({
          email: selectedAdmin.email || '',
          display_name: selectedAdmin.display_name || '',
          is_active: selectedAdmin.is_active !== false,
        });
      }
    } catch (loadError) {
      setError(loadError.message || 'Failed to load settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPage();
  }, []);

  useEffect(() => {
    const selected = subcontractors.find((item) => item.id === selectedSubId);
    if (!selected) return;
    setSubForm({
      name: selected.name || '',
      contact_name: selected.contact_name || '',
      phone: selected.phone || '',
      tax_id: selected.tax_id || '',
      assigned_project_ids: Array.isArray(selected.assigned_project_ids) ? selected.assigned_project_ids : [],
      vat_rate: selected.vat_rate ?? 0,
      wht_rate: selected.wht_rate ?? 0,
      retention_rate: selected.retention_rate ?? 0,
      bank_account: {
        bank_name: selected.bank_account?.bank_name || '',
        account_no: selected.bank_account?.account_no || '',
        account_name: selected.bank_account?.account_name || '',
      },
      is_active: selected.is_active !== false,
    });
  }, [selectedSubId, subcontractors]);

  useEffect(() => {
    const selected = admins.find((item) => item.id === selectedAdminId);
    if (!selected) return;
    setAdminForm({
      email: selected.email || '',
      display_name: selected.display_name || '',
      is_active: selected.is_active !== false,
    });
  }, [selectedAdminId, admins]);

  if (loading) return <Loading />;

  const selectedSubcontractor = subcontractors.find((item) => item.id === selectedSubId);
  const selectedAdmin = admins.find((item) => item.id === selectedAdminId);

  const updateSubField = (field, value) => {
    setSubForm((current) => ({ ...current, [field]: value }));
  };

  const toggleAssignedProject = (projectId) => {
    setSubForm((current) => {
      const currentIds = Array.isArray(current.assigned_project_ids) ? current.assigned_project_ids : [];
      return {
        ...current,
        assigned_project_ids: currentIds.includes(projectId)
          ? currentIds.filter((item) => item !== projectId)
          : [...currentIds, projectId],
      };
    });
  };

  const updateBankField = (field, value) => {
    setSubForm((current) => ({
      ...current,
      bank_account: {
        ...current.bank_account,
        [field]: value,
      },
    }));
  };

  const handleSaveSubcontractor = async () => {
    if (!selectedSubId) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const updated = await updateSettingSubcontractor(selectedSubId, subForm);
      setSubcontractors((current) =>
        current.map((item) => (item.id === selectedSubId ? updated : item))
      );
      setMessage('Subcontractor profile updated.');
    } catch (saveError) {
      setError(saveError.message || 'Failed to save subcontractor profile.');
    } finally {
      setSaving(false);
    }
  };

  const handleResetLine = async () => {
    if (!selectedSubId) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const updated = await resetSettingSubcontractorLine(selectedSubId);
      setSubcontractors((current) =>
        current.map((item) => (item.id === selectedSubId ? updated : item))
      );
      setMessage('LINE binding reset completed.');
    } catch (actionError) {
      setError(actionError.message || 'Failed to reset LINE binding.');
    } finally {
      setSaving(false);
    }
  };

  const handleViewKyc = async () => {
    if (!selectedSubId) return;
    setError('');
    try {
      const response = await getSettingSubcontractorKycUrl(selectedSubId);
      if (response?.signed_url) {
        window.open(response.signed_url, '_blank', 'noopener,noreferrer');
      }
    } catch (previewError) {
      setError(previewError.message || 'Failed to generate KYC preview URL.');
    }
  };

  const handleSaveAdmin = async () => {
    setSaving(true);
    setMessage('');
    setError('');
    try {
      if (selectedAdmin) {
        const updated = await updateSettingAdmin(selectedAdmin.id, {
          display_name: adminForm.display_name,
          is_active: adminForm.is_active,
        });
        setAdmins((current) => current.map((item) => (item.id === selectedAdmin.id ? updated : item)));
        setMessage('Admin updated.');
      } else {
        const created = await createSettingAdmin(adminForm);
        setAdmins((current) => [...current, created].sort((left, right) => left.email.localeCompare(right.email)));
        setSelectedAdminId(created.id);
        setMessage('Admin added.');
      }
    } catch (saveError) {
      setError(saveError.message || 'Failed to save admin.');
    } finally {
      setSaving(false);
    }
  };

  const handleNewAdmin = () => {
    setSelectedAdminId('');
    setAdminForm({
      email: '',
      display_name: '',
      is_active: true,
    });
  };

  return (
    <div style={{ maxWidth: '1480px', margin: '0 auto' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Settings</h1>
        <p style={{ color: 'var(--text-muted)', fontWeight: '500' }}>
          จัดการ subcontractor profile, financial rates, LINE binding และ admin directory
        </p>
      </div>

      {error ? (
        <div style={{ ...sectionCardStyle, marginBottom: '16px', padding: '14px 18px', color: '#b42318', backgroundColor: '#fff5f4' }}>
          {error}
        </div>
      ) : null}

      {message ? (
        <div style={{ ...sectionCardStyle, marginBottom: '16px', padding: '14px 18px', color: '#087443', backgroundColor: '#f0fdf4' }}>
          {message}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', alignItems: 'start' }}>
        <section style={{ ...sectionCardStyle, padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h2 style={{ fontSize: '22px', marginBottom: '6px' }}>Subcontractors</h2>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>
                ใช้ข้อมูลก้อนนี้เป็น source of truth สำหรับ KYC, LINE binding และ financial rate
              </p>
            </div>
            <select
              value={selectedSubId}
              onChange={(event) => setSelectedSubId(event.target.value)}
              style={{ ...inputStyle, width: '260px' }}
            >
              {subcontractors.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          {selectedSubcontractor ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '18px' }}>
                <AvatarCircle
                  name={selectedSubcontractor.contact_name || selectedSubcontractor.name}
                  imageUrl={selectedSubcontractor.profile_image_url || selectedSubcontractor.line_picture_url}
                  size={58}
                />
                <div>
                  <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-main)' }}>
                    {selectedSubcontractor.contact_name || selectedSubcontractor.name}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    {selectedSubcontractor.profile_image_url
                      ? 'Custom profile avatar'
                      : 'LINE avatar default with initials fallback'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '16px', marginBottom: '18px' }}>
                <div>
                  <span style={labelStyle}>Subcontractor ID</span>
                  <div style={{ ...inputStyle, backgroundColor: '#f8fafc' }}>{selectedSubcontractor.id}</div>
                </div>
                <div>
                  <span style={labelStyle}>LINE UID</span>
                  <div style={{ ...inputStyle, backgroundColor: '#f8fafc' }}>{selectedSubcontractor.line_uid || 'Unbound'}</div>
                </div>
                <div>
                  <span style={labelStyle}>Company / Name</span>
                  <input value={subForm.name} onChange={(event) => updateSubField('name', event.target.value)} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>Default Contact Name</span>
                  <input value={subForm.contact_name} onChange={(event) => updateSubField('contact_name', event.target.value)} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>Default Phone</span>
                  <input value={subForm.phone} onChange={(event) => updateSubField('phone', event.target.value)} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>Tax ID</span>
                  <input value={subForm.tax_id} onChange={(event) => updateSubField('tax_id', event.target.value)} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>VAT Rate</span>
                  <input type="number" step="0.01" value={subForm.vat_rate} onChange={(event) => updateSubField('vat_rate', Number(event.target.value))} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>WHT Rate</span>
                  <input type="number" step="0.01" value={subForm.wht_rate} onChange={(event) => updateSubField('wht_rate', Number(event.target.value))} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>Retention Rate</span>
                  <input type="number" step="0.01" value={subForm.retention_rate} onChange={(event) => updateSubField('retention_rate', Number(event.target.value))} style={inputStyle} />
                </div>
                <div>
                  <span style={labelStyle}>Active</span>
                  <select value={subForm.is_active ? 'active' : 'inactive'} onChange={(event) => updateSubField('is_active', event.target.value === 'active')} style={inputStyle}>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div style={{ ...sectionCardStyle, padding: '18px', marginBottom: '18px', backgroundColor: '#fcfcfd' }}>
                <h3 style={{ marginTop: 0, marginBottom: '14px', fontSize: '18px' }}>Assigned Projects</h3>
                <p style={{ marginTop: 0, marginBottom: '14px', color: 'var(--text-muted)', fontSize: '13px' }}>
                  โครงการที่เลือกไว้ที่นี่เท่านั้นจะปรากฏใน dropdown ของหน้า Input สำหรับ subcontractor คนนี้
                </p>
                {projects.length === 0 ? (
                  <div style={{ ...inputStyle, backgroundColor: '#f8fafc' }}>No projects available.</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' }}>
                    {projects.map((project) => {
                      const projectId = String(project.project_id || '');
                      const checked = subForm.assigned_project_ids.includes(projectId);
                      return (
                        <label
                          key={projectId}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '12px 14px',
                            borderRadius: '12px',
                            border: '1px solid var(--border-color)',
                            backgroundColor: checked ? '#f8f2e6' : '#fff',
                            cursor: 'pointer',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleAssignedProject(projectId)}
                          />
                          <span style={{ fontSize: '14px', color: 'var(--text-main)', fontWeight: checked ? '700' : '500' }}>
                            {project.name}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              <div style={{ ...sectionCardStyle, padding: '18px', marginBottom: '18px', backgroundColor: '#fcfcfd' }}>
                <h3 style={{ marginTop: 0, marginBottom: '14px', fontSize: '18px' }}>Bank Account</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '16px' }}>
                  <div>
                    <span style={labelStyle}>Bank Name</span>
                    <input value={subForm.bank_account.bank_name} onChange={(event) => updateBankField('bank_name', event.target.value)} style={inputStyle} />
                  </div>
                  <div>
                    <span style={labelStyle}>Account No.</span>
                    <input value={subForm.bank_account.account_no} onChange={(event) => updateBankField('account_no', event.target.value)} style={inputStyle} />
                  </div>
                  <div>
                    <span style={labelStyle}>Account Name</span>
                    <input value={subForm.bank_account.account_name} onChange={(event) => updateBankField('account_name', event.target.value)} style={inputStyle} />
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button type="button" style={buttonStyle('primary')} onClick={handleSaveSubcontractor} disabled={saving}>
                  Save Subcontractor
                </button>
                <button type="button" style={buttonStyle('ghost')} onClick={handleViewKyc} disabled={saving}>
                  View KYC
                </button>
                <button type="button" style={buttonStyle('danger')} onClick={handleResetLine} disabled={saving}>
                  Reset LINE Binding
                </button>
              </div>
            </>
          ) : (
            <p style={{ color: 'var(--text-muted)' }}>No subcontractor profiles found.</p>
          )}
        </section>

        <section style={{ ...sectionCardStyle, padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h2 style={{ fontSize: '22px', marginBottom: '6px' }}>Admins</h2>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>
                bootstrap ด้วย domain ได้ แต่รายชื่อจริงจะจัดการผ่านหน้านี้
              </p>
            </div>
            <button type="button" style={buttonStyle('ghost')} onClick={handleNewAdmin}>
              New Admin
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '18px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {admins.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedAdminId(item.id)}
                  style={{
                    textAlign: 'left',
                    padding: '12px 14px',
                    borderRadius: '14px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: item.id === selectedAdminId ? '#f8f2e6' : '#fff',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-main)' }}>{item.display_name || item.email}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{item.email}</div>
                </button>
              ))}
            </div>

            <div>
              <div style={{ display: 'grid', gap: '16px' }}>
                <div>
                  <span style={labelStyle}>Email</span>
                  <input
                    value={adminForm.email}
                    onChange={(event) => setAdminForm((current) => ({ ...current, email: event.target.value }))}
                    style={inputStyle}
                    disabled={Boolean(selectedAdmin)}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Display Name</span>
                  <input
                    value={adminForm.display_name}
                    onChange={(event) => setAdminForm((current) => ({ ...current, display_name: event.target.value }))}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Status</span>
                  <select
                    value={adminForm.is_active ? 'active' : 'inactive'}
                    onChange={(event) => setAdminForm((current) => ({ ...current, is_active: event.target.value === 'active' }))}
                    style={inputStyle}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', minHeight: '20px' }}>
                  {selectedAdmin ? `Selected admin id: ${selectedAdmin.id}` : 'Create a new admin record using email.'}
                </div>
                <button type="button" style={buttonStyle('primary')} onClick={handleSaveAdmin} disabled={saving}>
                  {selectedAdmin ? 'Save Admin' : 'Add Admin'}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default SettingPage;
