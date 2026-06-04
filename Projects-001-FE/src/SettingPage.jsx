import React, { useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  ClipboardCheck,
  Cloud,
  Database,
  ExternalLink,
  KeyRound,
  Link2Off,
  LoaderCircle,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  UsersRound,
} from 'lucide-react';
import {
  createSettingAdmin,
  fetchData,
  getInputProjectOptions,
  getSettingAdmins,
  getSettingSubcontractorKycUrl,
  getSettingSubcontractors,
  resetSettingSubcontractorLine,
  updateSettingAdmin,
  updateSettingSubcontractor,
} from './api';
import { canMutateAdminData, getStoredAuthUser } from './auth';
import Loading from './components/Loading';
import {
  SettingsAccordionItem,
  SettingsAvatar,
  SettingsBadge,
  SettingsDetailGrid,
  SettingsIntegrationCard,
  SettingsLocalNav,
  SettingsNotice,
  SettingsPanel,
  SettingsPanelHeader,
  SettingsToggle,
} from './components/SettingsWorkspace';

const emptyBank = {
  bank_name: '',
  account_no: '',
  account_name: '',
};

const emptySubForm = {
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
};

const emptyAdminForm = {
  email: '',
  display_name: '',
  is_active: true,
};

const NAV_ITEMS = [
  { id: 'general', label: 'General', icon: SlidersHorizontal },
  { id: 'users', label: 'User Management', icon: UsersRound },
  { id: 'kyc', label: 'Subcontractor KYC', icon: ClipboardCheck },
  { id: 'integrations', label: 'Integrations', icon: Cloud },
];

const KYC_RULES = [
  {
    id: 'commercial_registration',
    label: 'Commercial Registration',
    description: 'Required company registration document before approval.',
    enabled: true,
  },
  {
    id: 'vat_registration',
    label: 'VAT Registration',
    description: 'Optional VAT certificate for tax reporting.',
    enabled: false,
  },
  {
    id: 'professional_license',
    label: 'Professional License',
    description: 'Required license for regulated scopes of work.',
    enabled: true,
  },
  {
    id: 'bank_verification',
    label: 'Bank Account Verification',
    description: 'Require bank name, account number, and account holder.',
    enabled: true,
  },
];

const normalize = (value) => String(value || '').trim().toLowerCase();

const buildSubForm = (item = {}) => ({
  name: item.name || '',
  contact_name: item.contact_name || '',
  phone: item.phone || '',
  tax_id: item.tax_id || '',
  assigned_project_ids: Array.isArray(item.assigned_project_ids) ? item.assigned_project_ids : [],
  vat_rate: item.vat_rate ?? 0,
  wht_rate: item.wht_rate ?? 0,
  retention_rate: item.retention_rate ?? 0,
  bank_account: {
    bank_name: item.bank_account?.bank_name || '',
    account_no: item.bank_account?.account_no || '',
    account_name: item.bank_account?.account_name || '',
  },
  is_active: item.is_active !== false,
});

const buildAdminForm = (item = {}) => ({
  email: item.email || '',
  display_name: item.display_name || '',
  is_active: item.is_active !== false,
});

const formatRate = (value) => `${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}%`;

const getKycStatus = (item) => {
  const rawStatus = normalize(item?.kyc_status || item?.kyc_verification_status);

  if (['approved', 'verified', 'complete', 'completed'].includes(rawStatus)) {
    return { label: 'Approved', tone: 'success' };
  }

  if (['rejected', 'failed'].includes(rawStatus)) {
    return { label: 'Rejected', tone: 'danger' };
  }

  if (rawStatus || item?.kyc_storage_key || item?.kyc_image_url || item?.profile_image_url) {
    return { label: 'Pending', tone: 'warning' };
  }

  return { label: 'Missing', tone: 'neutral' };
};

const hasBankInfo = (item) =>
  Boolean(item?.bank_account?.bank_name && item?.bank_account?.account_no && item?.bank_account?.account_name);

const displayValue = (value) => {
  const text = String(value ?? '').trim();
  return text || '-';
};

const maskIdentifier = (value) => {
  const text = String(value || '').trim();
  if (!text) return '-';
  if (text.length <= 4) return text;
  return `•••• ${text.slice(-4)}`;
};

const resolveRoleLabel = (value) => {
  const role = String(value || '').replace(/_/g, ' ').trim();
  return role || 'Admin';
};

function SettingPage() {
  const [subcontractors, setSubcontractors] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [projects, setProjects] = useState([]);
  const [currentProfile, setCurrentProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('users');
  const [selectedSubId, setSelectedSubId] = useState('');
  const [selectedAdminId, setSelectedAdminId] = useState('');
  const [subcontractorSearch, setSubcontractorSearch] = useState('');
  const [subForm, setSubForm] = useState(emptySubForm);
  const [adminForm, setAdminForm] = useState(emptyAdminForm);
  const [generalPrefs, setGeneralPrefs] = useState({
    emailNotifications: true,
    darkMode: false,
    defaultCurrency: 'THB',
  });
  const [kycRules, setKycRules] = useState(KYC_RULES);
  const storedAuthUser = getStoredAuthUser();
  const canMutateSettings = canMutateAdminData(storedAuthUser);

  const loadPage = async () => {
    setLoading(true);
    setError('');
    try {
      const [subItems, adminItems, projectItems, profileResult] = await Promise.all([
        getSettingSubcontractors(),
        getSettingAdmins().catch(() => []),
        getInputProjectOptions().catch(() => []),
        fetchData('profile').catch(() => null),
      ]);

      setSubcontractors(subItems);
      setAdmins(adminItems);
      setProjects(projectItems);
      setCurrentProfile(profileResult);

      if (subItems.length > 0) {
        const selected = subItems[0];
        setSelectedSubId(selected.id);
        setSubForm(buildSubForm(selected));
      }

      if (adminItems.length > 0) {
        const selectedAdmin = adminItems[0];
        setSelectedAdminId(selectedAdmin.id);
        setAdminForm(buildAdminForm(selectedAdmin));
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
    setSubForm(buildSubForm(selected));
  }, [selectedSubId, subcontractors]);

  useEffect(() => {
    const selected = admins.find((item) => item.id === selectedAdminId);
    if (!selected) return;
    setAdminForm(buildAdminForm(selected));
  }, [selectedAdminId, admins]);

  const selectedSubcontractor = subcontractors.find((item) => item.id === selectedSubId);
  const selectedAdmin = admins.find((item) => item.id === selectedAdminId);
  const currentProfileUser = currentProfile?.user || {};
  const currentProfileEmail = normalize(currentProfileUser.email || storedAuthUser?.email);

  const projectNameById = useMemo(() => {
    const map = new Map();
    projects.forEach((project) => {
      const id = String(project.project_id || '');
      if (id) map.set(id, project.name || id);
    });
    return map;
  }, [projects]);

  const filteredSubcontractors = useMemo(() => {
    const query = normalize(subcontractorSearch);
    if (!query) return subcontractors;

    return subcontractors.filter((item) =>
      [item.name, item.contact_name, item.phone, item.tax_id, item.line_uid]
        .some((value) => normalize(value).includes(query))
    );
  }, [subcontractorSearch, subcontractors]);

  const connectedLineCount = useMemo(
    () => subcontractors.filter((item) => Boolean(item.line_uid)).length,
    [subcontractors]
  );

  const bankReadyCount = useMemo(
    () => subcontractors.filter((item) => hasBankInfo(item)).length,
    [subcontractors]
  );

  const updateSubField = (field, value) => {
    if (!canMutateSettings) return;
    setSubForm((current) => ({ ...current, [field]: value }));
  };

  const updateAdminField = (field, value) => {
    if (!canMutateSettings) return;
    setAdminForm((current) => ({ ...current, [field]: value }));
  };

  const toggleAssignedProject = (projectId) => {
    if (!canMutateSettings) return;
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
    if (!canMutateSettings) return;
    setSubForm((current) => ({
      ...current,
      bank_account: {
        ...current.bank_account,
        [field]: value,
      },
    }));
  };

  const handleSaveSubcontractor = async () => {
    if (!selectedSubId || !canMutateSettings) return;
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
    if (!selectedSubId || !canMutateSettings) return;
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
    if (!canMutateSettings) return;
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
    if (!canMutateSettings) return;
    setSelectedAdminId('');
    setAdminForm(emptyAdminForm);
  };

  const handlePreferenceSave = () => {
    setMessage('General preferences updated.');
    setError('');
  };

  const handleKycRuleSave = () => {
    setMessage('Subcontractor KYC rules updated.');
    setError('');
  };

  if (loading) return <Loading />;

  const renderGeneralPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="General"
        title="General Preferences"
        description="Manage platform preferences and admin workspace defaults."
      />

      <div className="settings-row-stack">
        <SettingsToggle
          checked={generalPrefs.emailNotifications}
          disabled={!canMutateSettings}
          label="Email Notifications"
          description="Send approval and project activity updates to admin users."
          onChange={(checked) => setGeneralPrefs((current) => ({ ...current, emailNotifications: checked }))}
        />
        <SettingsToggle
          checked={generalPrefs.darkMode}
          disabled={!canMutateSettings}
          label="Dark Mode"
          description="Use a dark admin interface for this workspace."
          onChange={(checked) => setGeneralPrefs((current) => ({ ...current, darkMode: checked }))}
        />
        <label className="settings-field settings-row-field">
          <span>Default Currency</span>
          <select
            className="settings-input"
            value={generalPrefs.defaultCurrency}
            disabled={!canMutateSettings}
            onChange={(event) => setGeneralPrefs((current) => ({ ...current, defaultCurrency: event.target.value }))}
          >
            <option value="THB">Thai Baht (THB)</option>
            <option value="USD">US Dollar (USD)</option>
            <option value="SGD">Singapore Dollar (SGD)</option>
          </select>
        </label>
      </div>

      <div className="settings-panel-footer">
        <button
          type="button"
          className="settings-button secondary"
          disabled={saving}
          onClick={() => setGeneralPrefs({ emailNotifications: true, darkMode: false, defaultCurrency: 'THB' })}
        >
          Cancel
        </button>
        <button
          type="button"
          className="settings-button primary"
          disabled={!canMutateSettings || saving}
          onClick={handlePreferenceSave}
        >
          <Save size={16} />
          Save Changes
        </button>
      </div>
    </SettingsPanel>
  );

  const renderUsersPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="Owner Only"
        title="Admin & Staff Management"
        description="Manage internal access and subcontractor records with expandable profile details."
        action={(
          <button type="button" className="settings-button primary" onClick={handleNewAdmin} disabled={!canMutateSettings}>
            <Plus size={16} />
            Invite New Admin
          </button>
        )}
      />

      <div className="settings-accordion-section">
        <div className="settings-accordion-section-head">
          <div>
            <span className="settings-kicker">Admins & Staff</span>
            <h3>{admins.length.toLocaleString('en-US')} access records</h3>
          </div>
        </div>

        <div className="settings-accordion-list">
          {admins.length > 0 ? (
            admins.map((item) => {
              const isCurrentProfile = currentProfileEmail && normalize(item.email) === currentProfileEmail;
              const profileUser = isCurrentProfile ? currentProfileUser : {};
              const profileName = profileUser.display_name || profileUser.name || item.display_name || item.email;
              const profilePhone = profileUser.phone || item.phone;
              const profileCompany = profileUser.company || profileUser.department || item.department;
              const profileTime = profileUser.time || profileUser.timezone;
              const profileRole = profileUser.role_key || profileUser.role || item.role || 'admin';
              const bankAccount = profileUser.bank_account || {};

              return (
                <SettingsAccordionItem
                  key={item.id}
                  id={`admin-${item.id}`}
                  isOpen={item.id === selectedAdminId}
                  onToggle={() => {
                    setSelectedAdminId(item.id);
                    setAdminForm(buildAdminForm(item));
                  }}
                  avatar={(
                    <SettingsAvatar
                      name={profileName}
                      imageUrl={profileUser.profile_image_url || profileUser.line_picture_url || profileUser.avatar_url}
                    />
                  )}
                  title={profileName}
                  subtitle={item.email}
                  meta={(
                    <>
                      {isCurrentProfile ? <SettingsBadge tone="warning">Current</SettingsBadge> : null}
                      <SettingsBadge tone={item.is_active !== false ? 'success' : 'neutral'}>
                        {item.is_active !== false ? 'Active' : 'Inactive'}
                      </SettingsBadge>
                    </>
                  )}
                >
                  <div className="settings-accordion-detail">
                    <SettingsDetailGrid
                      items={[
                        { label: 'Admin ID', value: item.id, wide: true },
                        { label: 'Display Name', value: displayValue(profileName) },
                        { label: 'Email', value: displayValue(item.email || profileUser.email) },
                        { label: 'Role', value: resolveRoleLabel(profileRole) },
                        { label: 'Phone', value: displayValue(profilePhone) },
                        { label: 'Company / Department', value: displayValue(profileCompany) },
                        { label: 'Timezone', value: displayValue(profileTime) },
                        { label: 'Bank Name', value: displayValue(bankAccount.bank_name) },
                        { label: 'Account No.', value: maskIdentifier(bankAccount.account_no) },
                        { label: 'Account Name', value: displayValue(bankAccount.account_name) },
                      ]}
                    />

                    <div className="settings-inline-editor">
                      <div>
                        <span className="settings-kicker">Access Control</span>
                        <h4>Edit admin access</h4>
                      </div>

                      <div className="settings-form-grid three">
                        <label className="settings-field">
                          <span>Email</span>
                          <input
                            className="settings-input"
                            value={adminForm.email}
                            onChange={(event) => updateAdminField('email', event.target.value)}
                            disabled
                          />
                        </label>
                        <label className="settings-field">
                          <span>Display Name</span>
                          <input
                            className="settings-input"
                            value={adminForm.display_name}
                            onChange={(event) => updateAdminField('display_name', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Status</span>
                          <select
                            className="settings-input"
                            value={adminForm.is_active ? 'active' : 'inactive'}
                            onChange={(event) => updateAdminField('is_active', event.target.value === 'active')}
                            disabled={!canMutateSettings}
                          >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </select>
                        </label>
                      </div>

                      <div className="settings-editor-actions">
                        <span>{isCurrentProfile ? 'Expanded profile detail includes the current logged-in account record.' : 'Managed admin record.'}</span>
                        <button type="button" className="settings-button primary" onClick={handleSaveAdmin} disabled={saving || !canMutateSettings}>
                          {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
                          Save Admin
                        </button>
                      </div>
                    </div>
                  </div>
                </SettingsAccordionItem>
              );
            })
          ) : (
            <div className="settings-empty-state">No admin records found.</div>
          )}
        </div>
      </div>

      {!selectedAdmin ? (
        <div className="settings-editor-card">
          <div>
            <span className="settings-kicker">New Admin</span>
            <h3>Create admin access</h3>
          </div>

          <div className="settings-form-grid three">
            <label className="settings-field">
              <span>Email</span>
              <input
                className="settings-input"
                value={adminForm.email}
                onChange={(event) => updateAdminField('email', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Display Name</span>
              <input
                className="settings-input"
                value={adminForm.display_name}
                onChange={(event) => updateAdminField('display_name', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Status</span>
              <select
                className="settings-input"
                value={adminForm.is_active ? 'active' : 'inactive'}
                onChange={(event) => updateAdminField('is_active', event.target.value === 'active')}
                disabled={!canMutateSettings}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </label>
          </div>

          <div className="settings-editor-actions">
            <span>Email is required for a new admin record.</span>
            <button type="button" className="settings-button primary" onClick={handleSaveAdmin} disabled={saving || !canMutateSettings}>
              {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
              Add Admin
            </button>
          </div>
        </div>
      ) : null}

      <div className="settings-section-divider" />

      <SettingsPanelHeader
        title="Subcontractor Management"
        description="Review company records, LINE binding, KYC status, project access, and payout details."
        action={(
          <div className="settings-search">
            <input
              value={subcontractorSearch}
              onChange={(event) => setSubcontractorSearch(event.target.value)}
              placeholder="Search subcontractors"
            />
          </div>
        )}
      />

      <div className="settings-metric-grid">
        <article>
          <span>Total Subcontractors</span>
          <strong>{subcontractors.length.toLocaleString('en-US')}</strong>
        </article>
        <article>
          <span>LINE Connected</span>
          <strong>{connectedLineCount.toLocaleString('en-US')}</strong>
        </article>
        <article>
          <span>Bank Ready</span>
          <strong>{bankReadyCount.toLocaleString('en-US')}</strong>
        </article>
      </div>

      <div className="settings-accordion-list">
        {filteredSubcontractors.length > 0 ? (
          filteredSubcontractors.map((item) => {
            const kycStatus = getKycStatus(item);
            const assignedProjectLabels = Array.isArray(item.assigned_project_ids)
              ? item.assigned_project_ids
                  .map((projectId) => projectNameById.get(String(projectId)) || projectId)
                  .filter(Boolean)
                  .join(', ')
              : '';
            const isOpen = item.id === selectedSubId;

            return (
              <SettingsAccordionItem
                key={item.id}
                id={`subcontractor-${item.id}`}
                isOpen={isOpen}
                onToggle={() => {
                  setSelectedSubId(item.id);
                  setSubForm(buildSubForm(item));
                }}
                avatar={(
                  <SettingsAvatar
                    name={item.contact_name || item.name}
                    imageUrl={item.profile_image_url || item.line_picture_url}
                  />
                )}
                title={item.name || 'Unnamed subcontractor'}
                subtitle={item.contact_name || item.phone || item.id}
                meta={(
                  <>
                    <SettingsBadge tone={item.line_uid ? 'success' : 'warning'}>
                      {item.line_uid ? 'LINE Connected' : 'LINE Pending'}
                    </SettingsBadge>
                    <SettingsBadge tone={kycStatus.tone}>{kycStatus.label}</SettingsBadge>
                  </>
                )}
              >
                <div className="settings-accordion-detail">
                  <SettingsDetailGrid
                    items={[
                      { label: 'Subcontractor ID', value: item.id, wide: true },
                      { label: 'Company / Name', value: displayValue(item.name) },
                      { label: 'Contact Person', value: displayValue(item.contact_name) },
                      { label: 'Phone', value: displayValue(item.phone) },
                      { label: 'Tax ID', value: maskIdentifier(item.tax_id) },
                      { label: 'Status', value: item.is_active !== false ? 'Active' : 'Inactive' },
                      { label: 'LINE UID', value: displayValue(item.line_uid), wide: true },
                      { label: 'KYC Status', value: kycStatus.label },
                      { label: 'Bank Name', value: displayValue(item.bank_account?.bank_name) },
                      { label: 'Account No.', value: maskIdentifier(item.bank_account?.account_no) },
                      { label: 'Account Name', value: displayValue(item.bank_account?.account_name) },
                      { label: 'Assigned Projects', value: displayValue(assignedProjectLabels), wide: true },
                    ]}
                  />

                  <div className="settings-inline-editor">
                    <div>
                      <span className="settings-kicker">Subcontractor Profile</span>
                      <h4>Edit profile and payout defaults</h4>
                    </div>

                    <div className="settings-form-grid two">
                      <label className="settings-field">
                        <span>Subcontractor ID</span>
                        <div className="settings-readonly">{item.id}</div>
                      </label>
                      <label className="settings-field">
                        <span>Company / Name</span>
                        <input
                          className="settings-input"
                          value={subForm.name}
                          onChange={(event) => updateSubField('name', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Default Contact Name</span>
                        <input
                          className="settings-input"
                          value={subForm.contact_name}
                          onChange={(event) => updateSubField('contact_name', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Default Phone</span>
                        <input
                          className="settings-input"
                          value={subForm.phone}
                          onChange={(event) => updateSubField('phone', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Tax ID</span>
                        <input
                          className="settings-input"
                          value={subForm.tax_id}
                          onChange={(event) => updateSubField('tax_id', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Status</span>
                        <select
                          className="settings-input"
                          value={subForm.is_active ? 'active' : 'inactive'}
                          onChange={(event) => updateSubField('is_active', event.target.value === 'active')}
                          disabled={!canMutateSettings}
                        >
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                        </select>
                      </label>
                    </div>

                    <div className="settings-form-grid three">
                      <label className="settings-field">
                        <span>VAT Rate</span>
                        <input
                          className="settings-input"
                          type="number"
                          step="0.01"
                          value={subForm.vat_rate}
                          onChange={(event) => updateSubField('vat_rate', Number(event.target.value))}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>WHT Rate</span>
                        <input
                          className="settings-input"
                          type="number"
                          step="0.01"
                          value={subForm.wht_rate}
                          onChange={(event) => updateSubField('wht_rate', Number(event.target.value))}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Retention Rate</span>
                        <input
                          className="settings-input"
                          type="number"
                          step="0.01"
                          value={subForm.retention_rate}
                          onChange={(event) => updateSubField('retention_rate', Number(event.target.value))}
                          disabled={!canMutateSettings}
                        />
                      </label>
                    </div>

                    <div className="settings-form-grid three">
                      <label className="settings-field">
                        <span>Bank Name</span>
                        <input
                          className="settings-input"
                          value={subForm.bank_account.bank_name}
                          onChange={(event) => updateBankField('bank_name', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Account No.</span>
                        <input
                          className="settings-input"
                          value={subForm.bank_account.account_no}
                          onChange={(event) => updateBankField('account_no', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Account Name</span>
                        <input
                          className="settings-input"
                          value={subForm.bank_account.account_name}
                          onChange={(event) => updateBankField('account_name', event.target.value)}
                          disabled={!canMutateSettings}
                        />
                      </label>
                    </div>

                    <div className="settings-project-assignment">
                      <div>
                        <span className="settings-kicker">Assigned Projects</span>
                        <strong>{subForm.assigned_project_ids.length} selected</strong>
                      </div>
                      {projects.length === 0 ? (
                        <div className="settings-empty-row">No projects available.</div>
                      ) : (
                        <div className="settings-project-grid">
                          {projects.map((project) => {
                            const projectId = String(project.project_id || '');
                            const checked = subForm.assigned_project_ids.includes(projectId);
                            return (
                              <label key={projectId} className={checked ? 'selected' : ''}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => toggleAssignedProject(projectId)}
                                  disabled={!canMutateSettings}
                                />
                                <span>{project.name}</span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <div className="settings-editor-actions">
                      <span>
                        Rates: VAT {formatRate(subForm.vat_rate)} / WHT {formatRate(subForm.wht_rate)} / Retention {formatRate(subForm.retention_rate)}
                      </span>
                      <div>
                        <button type="button" className="settings-button secondary" onClick={handleViewKyc} disabled={saving}>
                          <ExternalLink size={16} />
                          View KYC
                        </button>
                        <button type="button" className="settings-button danger" onClick={handleResetLine} disabled={saving || !canMutateSettings}>
                          <Link2Off size={16} />
                          Reset LINE
                        </button>
                        <button type="button" className="settings-button primary" onClick={handleSaveSubcontractor} disabled={saving || !canMutateSettings}>
                          {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
                          Save Subcontractor
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </SettingsAccordionItem>
            );
          })
        ) : (
          <div className="settings-empty-state">No subcontractors match this search.</div>
        )}
      </div>
    </SettingsPanel>
  );

  const renderKycPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="Subcontractor KYC"
        title="Subcontractor KYC Rules"
        description="Configure required documents and verification rules for subcontractor registration."
      />

      <div className="settings-row-stack">
        {kycRules.map((rule) => (
          <SettingsToggle
            key={rule.id}
            checked={rule.enabled}
            disabled={!canMutateSettings}
            label={rule.label}
            description={rule.description}
            onChange={(checked) =>
              setKycRules((current) =>
                current.map((item) => (item.id === rule.id ? { ...item, enabled: checked } : item))
              )
            }
          />
        ))}
      </div>

      <div className="settings-kyc-review">
        <div>
          <span className="settings-kicker">Review Queue</span>
          <h3>{selectedSubcontractor ? selectedSubcontractor.name || selectedSubcontractor.contact_name : 'No subcontractor selected'}</h3>
          <p>
            {selectedSubcontractor
              ? `${getKycStatus(selectedSubcontractor).label} KYC status, ${hasBankInfo(selectedSubcontractor) ? 'bank details complete' : 'bank details incomplete'}`
              : 'Select a subcontractor from User Management to review documents.'}
          </p>
        </div>
        <button
          type="button"
          className="settings-button secondary"
          onClick={handleViewKyc}
          disabled={!selectedSubcontractor}
        >
          <ExternalLink size={16} />
          View KYC
        </button>
      </div>

      <div className="settings-panel-footer">
        <button
          type="button"
          className="settings-button secondary"
          disabled={saving}
          onClick={() => setKycRules(KYC_RULES)}
        >
          Cancel
        </button>
        <button
          type="button"
          className="settings-button primary"
          disabled={!canMutateSettings || saving}
          onClick={handleKycRuleSave}
        >
          <Save size={16} />
          Save Changes
        </button>
      </div>
    </SettingsPanel>
  );

  const renderIntegrationsPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="Integrations"
        title="Integrations & API"
        description="Review connected platform services used by the admin portal."
      />

      <div className="settings-integration-grid">
        <SettingsIntegrationCard
          icon={Database}
          name="Google Sheets API"
          status="Active"
          tone="success"
          description="BOQ and operational worksheet sync source."
          actionLabel="Manage"
          onAction={() => setMessage('Google Sheets integration uses the current backend configuration.')}
        />
        <SettingsIntegrationCard
          icon={Cloud}
          name="Google Firebase"
          status="Active"
          tone="success"
          description="Authentication, Firestore records, and private asset storage."
          actionLabel="Configure"
          onAction={() => setMessage('Firebase settings are managed by the deployed environment.')}
        />
        <SettingsIntegrationCard
          icon={ShieldCheck}
          name="LINE / LIFF"
          status="Active"
          tone="success"
          description="Subcontractor login, profile binding, and mobile form entry."
          actionLabel="Review"
          onAction={() => setMessage('LINE / LIFF integration is active for subcontractor access.')}
        />
        <SettingsIntegrationCard
          icon={KeyRound}
          name="Vertex AI Model"
          status="Configured"
          tone="warning"
          description="AI assistant model used for project and finance queries."
          actionLabel="Configure"
          onAction={() => setMessage('Vertex AI model configuration is connected to the AI assistant.')}
        />
      </div>

      <div className="settings-api-key-card">
        <div className="settings-integration-icon">
          <KeyRound size={19} strokeWidth={2.2} />
        </div>
        <div>
          <span className="settings-kicker">Authentication</span>
          <h3>Global API Key</h3>
          <code>••••••••••••••••••••</code>
        </div>
        <SettingsBadge tone="neutral">Secret Manager</SettingsBadge>
      </div>

      <div className="settings-panel-footer">
        <button
          type="button"
          className="settings-button secondary"
          disabled={saving}
          onClick={() => setMessage('No integration changes to discard.')}
        >
          Cancel
        </button>
        <button type="button" className="settings-button primary" disabled={!canMutateSettings || saving} onClick={() => setMessage('Integration settings reviewed.')}>
          <CheckCircle2 size={16} />
          Save Changes
        </button>
      </div>
    </SettingsPanel>
  );

  return (
    <div className="settings-page">
      <header className="settings-page-header">
        <div>
          <h1>Settings</h1>
          <p>Manage your organization preferences, user access, and system configurations.</p>
        </div>
        <div className="settings-page-status">
          <span>{canMutateSettings ? 'Owner access' : 'View only'}</span>
          <strong>{admins.length.toLocaleString('en-US')} admins</strong>
        </div>
      </header>

      {error ? <SettingsNotice tone="error">{error}</SettingsNotice> : null}
      {message ? <SettingsNotice tone="success">{message}</SettingsNotice> : null}

      <div className="settings-layout">
        <SettingsLocalNav items={NAV_ITEMS} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="settings-content">
          {activeTab === 'general' ? renderGeneralPanel() : null}
          {activeTab === 'users' ? renderUsersPanel() : null}
          {activeTab === 'kyc' ? renderKycPanel() : null}
          {activeTab === 'integrations' ? renderIntegrationsPanel() : null}
        </div>
      </div>
    </div>
  );
}

export default SettingPage;
