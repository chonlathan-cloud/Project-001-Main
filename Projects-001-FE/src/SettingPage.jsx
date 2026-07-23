import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  ClipboardCheck,
  Cloud,
  Copy,
  Database,
  ExternalLink,
  KeyRound,
  Link2Off,
  LoaderCircle,
  Plus,
  RotateCcw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  UserCheck,
  UsersRound,
  XCircle,
} from 'lucide-react';
import {
  approveSettingAccessRequest,
  createSettingAdmin,
  fetchData,
  getSettingAccessRequests,
  getInputProjectOptions,
  getSettingAdmins,
  getSettingCustomers,
  getSettingSubcontractorKycUrl,
  getSettingSubcontractors,
  rejectSettingAccessRequest,
  reopenSettingAccessRequest,
  resetSettingCustomerLine,
  resetSettingSubcontractorLine,
  updateSettingAdmin,
  updateSettingCustomer,
  updateSettingSubcontractor,
} from './api';
import { canMutateAdminData, canMutateSubcontractorData, getStoredAuthUser } from './auth';
import Loading from './components/Loading';
import CustomerManagementSection from './components/settings/CustomerManagementSection';
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
  phone: '',
  company: '',
  department: '',
  time: 'Asia/Bangkok',
  bank_account: { ...emptyBank },
  role: 'admin',
  roles: ['admin'],
  assigned_project_ids: [],
  is_active: true,
};

const emptyCustomerForm = {
  name: '',
  contact_name: '',
  phone: '',
  assigned_project_ids: [],
  is_active: true,
};

const emptyAccessDecision = {
  account_type: 'subcontractor',
  existing_subcontractor_id: '',
  project_ids: [],
  display_name: '',
  contact_name: '',
  phone: '',
  company: '',
  department: '',
  time: 'Asia/Bangkok',
  tax_id: '',
  bank_account: { ...emptyBank },
  role: 'admin',
  roles: ['admin'],
  rejection_reason: '',
};

const ROLE_OPTIONS = [
  { id: 'owner', label: 'Owner', description: 'Full business control' },
  { id: 'admin', label: 'Admin', description: 'Admin operations' },
  { id: 'inspector', label: 'Inspector', description: 'Inspection work' },
];

const OWNER_SUBCONTRACTOR_FIELDS = [
  'name',
  'contact_name',
  'phone',
  'tax_id',
  'assigned_project_ids',
  'vat_rate',
  'wht_rate',
  'retention_rate',
  'bank_account',
  'is_active',
];

const ADMIN_SUBCONTRACTOR_FIELDS = [
  'name',
  'contact_name',
  'phone',
  'tax_id',
  'bank_account',
];

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
  phone: item.phone || '',
  company: item.company || '',
  department: item.department || '',
  time: item.time || item.timezone || 'Asia/Bangkok',
  bank_account: {
    bank_name: item.bank_account?.bank_name || '',
    account_no: item.bank_account?.account_no || '',
    account_name: item.bank_account?.account_name || '',
  },
  role: item.role || 'admin',
  roles: Array.isArray(item.roles) && item.roles.length > 0 ? item.roles : [item.role || 'admin'],
  assigned_project_ids: Array.isArray(item.assigned_project_ids) ? item.assigned_project_ids : [],
  is_active: item.is_active !== false,
});

const buildCustomerForm = (item = {}) => ({
  name: item.name || '',
  contact_name: item.contact_name || '',
  phone: item.phone || '',
  assigned_project_ids: Array.isArray(item.assigned_project_ids) ? item.assigned_project_ids : [],
  is_active: item.is_active !== false,
});

const buildAccessDecision = (item = {}) => {
  const requestedType = normalize(item.requested_account_type);
  const accountType = ['admin', 'customer'].includes(requestedType) ? requestedType : 'subcontractor';
  const displayName = accountType === 'customer'
    ? item.nickname || item.first_name || item.contact_name || item.display_name || ''
    : item.company_name || item.display_name || item.email || item.line_uid || '';
  return {
    ...emptyAccessDecision,
    account_type: accountType,
    display_name: displayName,
    contact_name: accountType === 'customer'
      ? item.first_name || item.contact_name || ''
      : item.contact_name || item.display_name || '',
    phone: item.phone || '',
    company: item.company_name || '',
    tax_id: item.tax_id || '',
    bank_account: {
      bank_name: item.bank_account?.bank_name || '',
      account_no: item.bank_account?.account_no || '',
      account_name: item.bank_account?.account_name || '',
    },
    roles: ['admin'],
    role: 'admin',
    project_ids: [],
  };
};

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

const normalizeRoleList = (roles = [], fallback = 'admin') => {
  const seen = new Set();
  const normalized = [];
  roles.forEach((role) => {
    const cleaned = normalize(role);
    if (cleaned && ROLE_OPTIONS.some((option) => option.id === cleaned) && !seen.has(cleaned)) {
      normalized.push(cleaned);
      seen.add(cleaned);
    }
  });
  if (normalized.length > 0) return normalized;
  const fallbackRole = normalize(fallback);
  return ROLE_OPTIONS.some((option) => option.id === fallbackRole) ? [fallbackRole] : ['admin'];
};

const primaryRoleForRoles = (roles = []) => {
  if (roles.includes('owner')) return 'owner';
  if (roles.includes('admin')) return 'admin';
  if (roles.includes('inspector')) return 'inspector';
  return 'admin';
};

const pickFields = (source, fields) => fields.reduce((payload, field) => ({
  ...payload,
  [field]: source[field],
}), {});

function SettingPage() {
  const [accessRequests, setAccessRequests] = useState([]);
  const [accessRequestStatus, setAccessRequestStatus] = useState('pending');
  const [subcontractors, setSubcontractors] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [currentProfile, setCurrentProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('users');
  const [selectedAccessRequestId, setSelectedAccessRequestId] = useState('');
  const [selectedSubId, setSelectedSubId] = useState('');
  const [selectedAdminId, setSelectedAdminId] = useState('');
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [subcontractorSearch, setSubcontractorSearch] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');
  const [subForm, setSubForm] = useState(emptySubForm);
  const [adminForm, setAdminForm] = useState(emptyAdminForm);
  const [customerForm, setCustomerForm] = useState(emptyCustomerForm);
  const [accessDecision, setAccessDecision] = useState(emptyAccessDecision);
  const [generalPrefs, setGeneralPrefs] = useState({
    emailNotifications: true,
    darkMode: false,
    defaultCurrency: 'THB',
  });
  const [kycRules, setKycRules] = useState(KYC_RULES);
  const storedAuthUser = getStoredAuthUser();
  const canMutateSettings = canMutateAdminData(storedAuthUser);
  const canMutateSubcontractors = canMutateSubcontractorData(storedAuthUser);
  const canMutateCustomers = canMutateSubcontractorData(storedAuthUser);
  const settingsAccessLabel = canMutateSettings
    ? 'Owner access'
    : canMutateSubcontractors
      ? 'Subcontractor edit'
      : 'View only';

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [subItems, adminItems, customerItems, projectItems, profileResult] = await Promise.all([
        canMutateSubcontractors ? getSettingSubcontractors() : Promise.resolve([]),
        canMutateSubcontractors ? getSettingAdmins().catch(() => []) : Promise.resolve([]),
        getSettingCustomers(),
        getInputProjectOptions().catch(() => []),
        fetchData('profile').catch(() => null),
      ]);
      const accessItems = canMutateSubcontractors
        ? await getSettingAccessRequests('all').catch(() => [])
        : [];

      setAccessRequests(accessItems);
      setSubcontractors(subItems);
      setAdmins(adminItems);
      setCustomers(customerItems);
      setProjects(projectItems);
      setCurrentProfile(profileResult);

      setSelectedSubId('');
      setSubForm(emptySubForm);
      setSelectedAdminId('');
      setAdminForm(emptyAdminForm);
      setSelectedCustomerId('');
      setCustomerForm(emptyCustomerForm);
      setSelectedAccessRequestId('');
      setAccessDecision(emptyAccessDecision);
    } catch (loadError) {
      setError(loadError.message || 'Failed to load settings.');
    } finally {
      setLoading(false);
    }
  }, [canMutateSubcontractors]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  useEffect(() => {
    const selected = accessRequests.find((item) => item.id === selectedAccessRequestId);
    if (!selected) {
      setAccessDecision(emptyAccessDecision);
      return;
    }
    setAccessDecision(buildAccessDecision(selected));
  }, [selectedAccessRequestId, accessRequests]);

  useEffect(() => {
    const selected = subcontractors.find((item) => item.id === selectedSubId);
    if (!selected) {
      setSubForm(emptySubForm);
      return;
    }
    setSubForm(buildSubForm(selected));
  }, [selectedSubId, subcontractors]);

  useEffect(() => {
    const selected = admins.find((item) => item.id === selectedAdminId);
    if (!selected) {
      setAdminForm(emptyAdminForm);
      return;
    }
    setAdminForm(buildAdminForm(selected));
  }, [selectedAdminId, admins]);

  useEffect(() => {
    const selected = customers.find((item) => item.id === selectedCustomerId);
    if (!selected) {
      setCustomerForm(emptyCustomerForm);
      return;
    }
    setCustomerForm(buildCustomerForm(selected));
  }, [selectedCustomerId, customers]);

  const selectedSubcontractor = subcontractors.find((item) => item.id === selectedSubId);
  const selectedAdmin = admins.find((item) => item.id === selectedAdminId);
  const selectedCustomer = customers.find((item) => item.id === selectedCustomerId);
  const selectedAccessRequest = accessRequests.find((item) => item.id === selectedAccessRequestId);
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

  const filteredCustomers = useMemo(() => {
    const query = normalize(customerSearch);
    if (!query) return customers;

    return customers.filter((item) =>
      [item.name, item.first_name, item.nickname, item.contact_name, item.phone, item.email, item.line_uid]
        .some((value) => normalize(value).includes(query))
    );
  }, [customerSearch, customers]);

  const customerProjects = useMemo(() => {
    if (canMutateSubcontractors) return projects;
    const visibleProjectIds = new Set(
      customers.flatMap((item) => (
        Array.isArray(item.assigned_project_ids) ? item.assigned_project_ids : []
      )),
    );
    return projects.filter((project) =>
      visibleProjectIds.has(String(project.project_id || project.id || ''))
    );
  }, [canMutateSubcontractors, customers, projects]);

  const connectedLineCount = useMemo(
    () => subcontractors.filter((item) => Boolean(item.line_uid)).length,
    [subcontractors]
  );

  const bankReadyCount = useMemo(
    () => subcontractors.filter((item) => hasBankInfo(item)).length,
    [subcontractors]
  );

  const pendingAccessRequests = useMemo(
    () => accessRequests.filter((item) => normalize(item.status) === 'pending'),
    [accessRequests],
  );

  const rejectedAccessRequests = useMemo(
    () => accessRequests.filter((item) => normalize(item.status) === 'rejected'),
    [accessRequests],
  );

  const visibleAccessRequests = accessRequestStatus === 'rejected'
    ? rejectedAccessRequests
    : pendingAccessRequests;

  const updateSubField = (field, value) => {
    if (!canMutateSubcontractors) return;
    setSubForm((current) => ({ ...current, [field]: value }));
  };

  const updateAdminField = (field, value) => {
    if (!canMutateSettings) return;
    setAdminForm((current) => ({ ...current, [field]: value }));
  };

  const updateCustomerField = (field, value) => {
    if (!canMutateCustomers) return;
    setCustomerForm((current) => ({ ...current, [field]: value }));
  };

  const toggleCustomerProject = (projectId) => {
    if (!canMutateCustomers) return;
    setCustomerForm((current) => {
      const currentIds = Array.isArray(current.assigned_project_ids)
        ? current.assigned_project_ids
        : [];
      return {
        ...current,
        assigned_project_ids: currentIds.includes(projectId)
          ? currentIds.filter((item) => item !== projectId)
          : [...currentIds, projectId],
      };
    });
  };

  const updateAdminBankField = (field, value) => {
    if (!canMutateSettings) return;
    setAdminForm((current) => ({
      ...current,
      bank_account: {
        ...current.bank_account,
        [field]: value,
      },
    }));
  };

  const toggleAdminRole = (roleId) => {
    if (!canMutateSettings) return;
    setAdminForm((current) => {
      const roles = normalizeRoleList(current.roles, current.role);
      const hasRole = roles.includes(roleId);
      const nextRoles = hasRole
        ? roles.filter((role) => role !== roleId)
        : [...roles, roleId];
      const normalizedRoles = nextRoles.length > 0 ? normalizeRoleList(nextRoles, roleId) : roles;
      return {
        ...current,
        roles: normalizedRoles,
        role: primaryRoleForRoles(normalizedRoles),
      };
    });
  };

  const toggleAdminProject = (projectId) => {
    if (!canMutateSettings) return;
    setAdminForm((current) => {
      const currentIds = Array.isArray(current.assigned_project_ids)
        ? current.assigned_project_ids
        : [];
      return {
        ...current,
        assigned_project_ids: currentIds.includes(projectId)
          ? currentIds.filter((item) => item !== projectId)
          : [...currentIds, projectId],
      };
    });
  };

  const updateAccessDecisionField = (field, value) => {
    if (!canMutateSubcontractors) return;
    setAccessDecision((current) => ({ ...current, [field]: value }));
  };

  const updateAccessDecisionBankField = (field, value) => {
    if (!canMutateSubcontractors) return;
    setAccessDecision((current) => ({
      ...current,
      bank_account: {
        ...current.bank_account,
        [field]: value,
      },
    }));
  };

  const toggleAccessDecisionProject = (projectId) => {
    if (!canMutateSubcontractors) return;
    setAccessDecision((current) => {
      const currentIds = Array.isArray(current.project_ids) ? current.project_ids : [];
      return {
        ...current,
        project_ids: currentIds.includes(projectId)
          ? currentIds.filter((item) => item !== projectId)
          : [...currentIds, projectId],
      };
    });
  };

  const toggleAccessDecisionRole = (roleId) => {
    if (!canMutateSettings) return;
    setAccessDecision((current) => {
      const roles = normalizeRoleList(current.roles, current.role);
      const hasRole = roles.includes(roleId);
      const nextRoles = hasRole
        ? roles.filter((role) => role !== roleId)
        : [...roles, roleId];
      const normalizedRoles = nextRoles.length > 0 ? normalizeRoleList(nextRoles, roleId) : roles;
      return {
        ...current,
        roles: normalizedRoles,
        role: primaryRoleForRoles(normalizedRoles),
      };
    });
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
    if (!canMutateSubcontractors) return;
    setSubForm((current) => ({
      ...current,
      bank_account: {
        ...current.bank_account,
        [field]: value,
      },
    }));
  };

  const handleSaveSubcontractor = async () => {
    if (!selectedSubId || !canMutateSubcontractors) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const payload = canMutateSettings
        ? pickFields(subForm, OWNER_SUBCONTRACTOR_FIELDS)
        : pickFields(subForm, ADMIN_SUBCONTRACTOR_FIELDS);
      const updated = await updateSettingSubcontractor(selectedSubId, payload);
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

  const handleSaveCustomer = async () => {
    if (!selectedCustomer || !canMutateCustomers) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const updated = await updateSettingCustomer(selectedCustomer.id, customerForm);
      setCustomers((current) =>
        current.map((item) => (item.id === selectedCustomer.id ? updated : item))
      );
      setMessage('Customer profile and project access updated.');
    } catch (saveError) {
      setError(saveError.message || 'Failed to save customer profile.');
    } finally {
      setSaving(false);
    }
  };

  const handleResetCustomerLine = async (customer) => {
    if (!customer?.id || !canMutateCustomers) return;
    if (!window.confirm(`Reset the LINE connection for ${customer.contact_name || customer.name || 'this customer'}?`)) {
      return;
    }
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const updated = await resetSettingCustomerLine(customer.id);
      setCustomers((current) =>
        current.map((item) => (item.id === customer.id ? updated : item))
      );
      setMessage('Customer LINE binding reset completed.');
    } catch (actionError) {
      setError(actionError.message || 'Failed to reset customer LINE binding.');
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
      const roles = normalizeRoleList(adminForm.roles, adminForm.role);
      const isSelfAdmin = selectedAdmin && currentProfileEmail && normalize(selectedAdmin.email) === currentProfileEmail;
      const staffPayload = {
        display_name: adminForm.display_name,
        phone: adminForm.phone,
        company: adminForm.company,
        department: adminForm.department,
        time: adminForm.time,
        bank_account: adminForm.bank_account,
        assigned_project_ids: adminForm.assigned_project_ids,
      };
      if (selectedAdmin) {
        const updated = await updateSettingAdmin(selectedAdmin.id, isSelfAdmin
          ? staffPayload
          : {
              ...staffPayload,
              role: primaryRoleForRoles(roles),
              roles,
              is_active: adminForm.is_active,
            });
        setAdmins((current) => current.map((item) => (item.id === selectedAdmin.id ? updated : item)));
        setMessage('Admin updated.');
      } else {
        const created = await createSettingAdmin({
          ...staffPayload,
          email: adminForm.email,
          role: primaryRoleForRoles(roles),
          roles,
          is_active: adminForm.is_active,
        });
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
    setAdminForm({ ...emptyAdminForm, bank_account: { ...emptyBank }, roles: ['admin'] });
  };

  const handleApproveAccessRequest = async () => {
    if (!selectedAccessRequest || !canMutateSubcontractors) return;
    if (accessDecision.account_type === 'admin' && !canMutateSettings) {
      setError('Owner access is required to approve admin or staff accounts.');
      return;
    }
    if (accessDecision.account_type === 'customer' && accessDecision.project_ids.length === 0) {
      setError('Select at least one project for customer access.');
      return;
    }
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const roles = normalizeRoleList(accessDecision.roles, accessDecision.role);
      await approveSettingAccessRequest(selectedAccessRequest.id, {
        account_type: accessDecision.account_type,
        existing_subcontractor_id: accessDecision.existing_subcontractor_id || null,
        project_ids: accessDecision.project_ids || [],
        display_name: accessDecision.display_name,
        contact_name: accessDecision.contact_name,
        phone: accessDecision.phone,
        company: accessDecision.company,
        department: accessDecision.department,
        time: accessDecision.time,
        tax_id: accessDecision.tax_id,
        bank_account: accessDecision.bank_account,
        role: primaryRoleForRoles(roles),
        roles,
      });
      setMessage('Access request approved.');
      await loadPage();
    } catch (approveError) {
      setError(approveError.message || 'Failed to approve access request.');
    } finally {
      setSaving(false);
    }
  };

  const handleRejectAccessRequest = async () => {
    if (!selectedAccessRequest || !canMutateSubcontractors) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      await rejectSettingAccessRequest(selectedAccessRequest.id, {
        reason: accessDecision.rejection_reason || 'Access request rejected by admin.',
      });
      setMessage('Access request rejected.');
      await loadPage();
    } catch (rejectError) {
      setError(rejectError.message || 'Failed to reject access request.');
    } finally {
      setSaving(false);
    }
  };

  const handleReopenAccessRequest = async () => {
    if (!selectedAccessRequest || !canMutateSubcontractors) return;
    setSaving(true);
    setMessage('');
    setError('');
    try {
      await reopenSettingAccessRequest(selectedAccessRequest.id);
      setAccessRequestStatus('pending');
      setMessage('Access request reopened and returned to pending review.');
      await loadPage();
    } catch (reopenError) {
      setError(reopenError.message || 'Failed to reopen access request.');
    } finally {
      setSaving(false);
    }
  };

  const handleCopyText = async (label, text) => {
    setMessage('');
    setError('');
    try {
      if (!navigator?.clipboard?.writeText) {
        throw new Error('Clipboard is not available in this browser.');
      }
      await navigator.clipboard.writeText(text);
      setMessage(`${label} copied.`);
    } catch (copyError) {
      setError(copyError.message || `Failed to copy ${label.toLowerCase()}.`);
    }
  };

  const handleCopySubcontractorProfile = (item) => {
    if (!item) return;
    const assignedProjectLabels = Array.isArray(item.assigned_project_ids)
      ? item.assigned_project_ids
          .map((projectId) => projectNameById.get(String(projectId)) || projectId)
          .filter(Boolean)
          .join(', ')
      : '';
    handleCopyText('Subcontractor profile', [
      `Name: ${item.name || '-'}`,
      `Contact: ${item.contact_name || '-'}`,
      `Phone: ${item.phone || '-'}`,
      `Tax ID: ${item.tax_id || '-'}`,
      `Bank: ${item.bank_account?.bank_name || '-'}`,
      `Account No.: ${item.bank_account?.account_no || '-'}`,
      `Account Name: ${item.bank_account?.account_name || '-'}`,
      `Assigned Projects: ${assignedProjectLabels || '-'}`,
    ].join('\n'));
  };

  const handleCopySubcontractorBank = (item) => {
    if (!item) return;
    handleCopyText('Bank details', [
      `Bank: ${item.bank_account?.bank_name || '-'}`,
      `Account No.: ${item.bank_account?.account_no || '-'}`,
      `Account Name: ${item.bank_account?.account_name || '-'}`,
    ].join('\n'));
  };

  const handleCopyCustomerProfile = (item) => {
    if (!item) return;
    const assignedProjectLabels = Array.isArray(item.assigned_project_ids)
      ? item.assigned_project_ids
          .map((projectId) => projectNameById.get(String(projectId)) || projectId)
          .filter(Boolean)
          .join(', ')
      : '';
    handleCopyText('Customer profile', [
      `First name: ${item.first_name || item.contact_name || '-'}`,
      `Nickname: ${item.nickname || '-'}`,
      `Display name: ${item.name || '-'}`,
      `Contact: ${item.contact_name || '-'}`,
      `Phone: ${item.phone || '-'}`,
      `LINE: ${item.line_uid ? 'Connected' : 'Not connected'}`,
      `Status: ${item.is_active !== false ? 'Active' : 'Inactive'}`,
      `Assigned Projects: ${assignedProjectLabels || '-'}`,
    ].join('\n'));
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

  const renderAccessRequestsSection = () => (
    <div className="settings-accordion-section">
      <div className="settings-accordion-section-head">
        <div>
          <span className="settings-kicker">Access Review</span>
          <h3>{visibleAccessRequests.length.toLocaleString('en-US')} {accessRequestStatus} requests</h3>
        </div>
        <div className="settings-access-request-filters" role="group" aria-label="Filter access requests by status">
          <button
            type="button"
            className={`settings-button ${accessRequestStatus === 'pending' ? 'primary' : 'secondary'}`}
            onClick={() => {
              setAccessRequestStatus('pending');
              setSelectedAccessRequestId('');
            }}
          >
            Pending ({pendingAccessRequests.length})
          </button>
          <button
            type="button"
            className={`settings-button ${accessRequestStatus === 'rejected' ? 'danger' : 'secondary'}`}
            onClick={() => {
              setAccessRequestStatus('rejected');
              setSelectedAccessRequestId('');
            }}
          >
            Rejected ({rejectedAccessRequests.length})
          </button>
        </div>
      </div>

      <div className="settings-accordion-list">
        {visibleAccessRequests.length > 0 ? (
          visibleAccessRequests.map((item) => {
            const isOpen = item.id === selectedAccessRequestId;
            const isRejected = normalize(item.status) === 'rejected';
            const requestedType = item.requested_account_type || 'Admin decides';
            const isCustomerRequest = normalize(item.requested_account_type) === 'customer';
            const identity = item.email || item.line_uid || item.id;
            const customerName = item.first_name
              ? `${item.first_name}${item.nickname ? ` (${item.nickname})` : ''}`
              : '';

            return (
              <SettingsAccordionItem
                key={item.id}
                id={`access-request-${item.id}`}
                isOpen={isOpen}
                onToggle={() => {
                  if (isOpen) {
                    setSelectedAccessRequestId('');
                    setAccessDecision(emptyAccessDecision);
                    return;
                  }
                  setSelectedAccessRequestId(item.id);
                  setAccessDecision(buildAccessDecision(item));
                }}
                avatar={(
                  <SettingsAvatar
                    name={customerName || item.display_name || item.company_name || identity}
                    imageUrl={item.picture_url}
                  />
                )}
                title={customerName || item.company_name || item.display_name || identity}
                subtitle={`${item.provider || 'provider'} • ${identity}`}
                meta={(
                  <>
                    <SettingsBadge tone={isRejected ? 'danger' : 'warning'}>
                      {isRejected ? 'Rejected' : 'Pending'}
                    </SettingsBadge>
                    <SettingsBadge tone="neutral">{requestedType}</SettingsBadge>
                  </>
                )}
              >
                <div className="settings-accordion-detail">
                  <SettingsDetailGrid
                    items={[
                      { label: 'Request ID', value: item.id, wide: true },
                      { label: 'Provider', value: item.provider },
                      { label: 'Identity', value: identity, wide: true },
                      { label: 'Requested Type', value: requestedType },
                      ...(isCustomerRequest ? [
                        { label: 'First Name', value: displayValue(item.first_name) },
                        { label: 'Nickname', value: displayValue(item.nickname) },
                      ] : []),
                      { label: 'Contact', value: displayValue(item.contact_name) },
                      { label: 'Phone', value: displayValue(item.phone) },
                      { label: 'Tax ID', value: maskIdentifier(item.tax_id) },
                      { label: 'Bank Name', value: displayValue(item.bank_account?.bank_name) },
                      { label: 'Account No.', value: maskIdentifier(item.bank_account?.account_no) },
                      { label: 'Account Name', value: displayValue(item.bank_account?.account_name) },
                      ...(isRejected ? [
                        { label: 'Rejection Reason', value: displayValue(item.rejection_reason), wide: true },
                        { label: 'Rejected By', value: displayValue(item.decided_by) },
                      ] : []),
                    ]}
                  />

                  {isRejected ? (
                    <div className="settings-inline-editor settings-reopen-panel">
                      <div>
                        <span className="settings-kicker">Recover Request</span>
                        <h4>Return this request to pending review</h4>
                        <p>
                          Use this when the request was rejected by mistake. The applicant’s submitted
                          information remains unchanged and the action is recorded in the review history.
                        </p>
                      </div>
                      <div className="settings-editor-actions">
                        <span>
                          Reopening does not approve access. An admin must still review and approve the request.
                        </span>
                        <div>
                          <button
                            type="button"
                            className="settings-button primary"
                            onClick={handleReopenAccessRequest}
                            disabled={saving || !canMutateSubcontractors}
                          >
                            {saving ? <LoaderCircle size={16} className="spin" /> : <RotateCcw size={16} />}
                            Reopen Request
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="settings-inline-editor">
                    <div>
                      <span className="settings-kicker">Approval Decision</span>
                      <h4>Classify and approve access</h4>
                    </div>

                    <div className="settings-form-grid three">
                      <label className="settings-field">
                        <span>Account Type</span>
                        <select
                          className="settings-input"
                          value={accessDecision.account_type}
                          onChange={(event) => updateAccessDecisionField('account_type', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        >
                          <option value="subcontractor">Subcontractor</option>
                          <option value="customer">Customer</option>
                          <option value="admin">Admin / Staff</option>
                        </select>
                      </label>
                      <label className="settings-field">
                        <span>{accessDecision.account_type === 'admin' ? 'Display Name' : 'Company / Name'}</span>
                        <input
                          className="settings-input"
                          value={accessDecision.display_name}
                          onChange={(event) => updateAccessDecisionField('display_name', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Contact Name</span>
                        <input
                          className="settings-input"
                          value={accessDecision.contact_name}
                          onChange={(event) => updateAccessDecisionField('contact_name', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Phone</span>
                        <input
                          className="settings-input"
                          value={accessDecision.phone}
                          onChange={(event) => updateAccessDecisionField('phone', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Company</span>
                        <input
                          className="settings-input"
                          value={accessDecision.company}
                          onChange={(event) => updateAccessDecisionField('company', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Tax ID</span>
                        <input
                          className="settings-input"
                          value={accessDecision.tax_id}
                          onChange={(event) => updateAccessDecisionField('tax_id', event.target.value)}
                          disabled={!canMutateSubcontractors || accessDecision.account_type === 'admin'}
                        />
                      </label>
                    </div>

                    {accessDecision.account_type === 'subcontractor' ? (
                      <label className="settings-field">
                        <span>Link Existing Subcontractor</span>
                        <select
                          className="settings-input"
                          value={accessDecision.existing_subcontractor_id}
                          onChange={(event) => updateAccessDecisionField('existing_subcontractor_id', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        >
                          <option value="">Create new subcontractor profile</option>
                          {subcontractors.map((subcontractor) => (
                            <option key={subcontractor.id} value={subcontractor.id}>
                              {subcontractor.name || subcontractor.contact_name || subcontractor.id}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : accessDecision.account_type === 'admin' ? (
                      <div className="settings-project-assignment">
                        <div>
                          <span className="settings-kicker">Internal Roles</span>
                          <strong>{normalizeRoleList(accessDecision.roles, accessDecision.role).map(resolveRoleLabel).join(', ')}</strong>
                        </div>
                        <div className="settings-project-grid">
                          {ROLE_OPTIONS.map((roleOption) => {
                            const roles = normalizeRoleList(accessDecision.roles, accessDecision.role);
                            const checked = roles.includes(roleOption.id);
                            return (
                              <label key={roleOption.id} className={checked ? 'selected' : ''}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => toggleAccessDecisionRole(roleOption.id)}
                                  disabled={!canMutateSettings || (checked && roles.length === 1)}
                                />
                                <span>{roleOption.label}</span>
                              </label>
                            );
                          })}
                        </div>
                        {!normalizeRoleList(accessDecision.roles, accessDecision.role).includes('owner') ? (
                          <>
                            <div>
                              <span className="settings-kicker">Daily Report Projects</span>
                              <strong>{accessDecision.project_ids.length} selected</strong>
                            </div>
                            <div className="settings-project-grid">
                              {projects.map((project) => {
                                const projectId = project.project_id || project.id;
                                const checked = accessDecision.project_ids.includes(projectId);
                                return (
                                  <label key={projectId} className={checked ? 'selected' : ''}>
                                    <input
                                      type="checkbox"
                                      checked={checked}
                                      onChange={() => toggleAccessDecisionProject(projectId)}
                                      disabled={!canMutateSettings}
                                    />
                                    <span>{project.name || project.project_name || projectId}</span>
                                  </label>
                                );
                              })}
                            </div>
                          </>
                        ) : null}
                      </div>
                    ) : (
                      <div className="settings-project-assignment">
                        <div>
                          <span className="settings-kicker">Customer Projects</span>
                          <strong>{accessDecision.project_ids.length} selected</strong>
                        </div>
                        <div className="settings-project-grid">
                          {projects.map((project) => {
                            const projectId = project.project_id || project.id;
                            const checked = accessDecision.project_ids.includes(projectId);
                            return (
                              <label key={projectId} className={checked ? 'selected' : ''}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => toggleAccessDecisionProject(projectId)}
                                  disabled={!canMutateSubcontractors}
                                />
                                <span>{project.name || project.project_name || projectId}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {accessDecision.account_type === 'subcontractor' ? (
                      <div className="settings-form-grid three">
                        <label className="settings-field">
                          <span>Bank Name</span>
                          <input
                            className="settings-input"
                            value={accessDecision.bank_account.bank_name}
                            onChange={(event) => updateAccessDecisionBankField('bank_name', event.target.value)}
                            disabled={!canMutateSubcontractors}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Account No.</span>
                          <input
                            className="settings-input"
                            value={accessDecision.bank_account.account_no}
                            onChange={(event) => updateAccessDecisionBankField('account_no', event.target.value)}
                            disabled={!canMutateSubcontractors}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Account Name</span>
                          <input
                            className="settings-input"
                            value={accessDecision.bank_account.account_name}
                            onChange={(event) => updateAccessDecisionBankField('account_name', event.target.value)}
                            disabled={!canMutateSubcontractors}
                          />
                        </label>
                      </div>
                    ) : null}

                    <label className="settings-field">
                      <span>Rejection Reason</span>
                      <input
                        className="settings-input"
                        value={accessDecision.rejection_reason}
                        onChange={(event) => updateAccessDecisionField('rejection_reason', event.target.value)}
                        disabled={!canMutateSubcontractors}
                      />
                    </label>

                    <div className="settings-editor-actions">
                      <span>
                        {accessDecision.account_type === 'admin' && !canMutateSettings
                          ? 'Owner access is required to approve admin or staff accounts.'
                          : 'Approval creates or links the account immediately.'}
                      </span>
                      <div>
                        <button type="button" className="settings-button danger" onClick={handleRejectAccessRequest} disabled={saving || !canMutateSubcontractors}>
                          <XCircle size={16} />
                          Reject
                        </button>
                        <button
                          type="button"
                          className="settings-button primary"
                          onClick={handleApproveAccessRequest}
                          disabled={
                            saving
                            || !canMutateSubcontractors
                            || (accessDecision.account_type === 'admin' && !canMutateSettings)
                            || (accessDecision.account_type === 'customer' && accessDecision.project_ids.length === 0)
                          }
                        >
                          {saving ? <LoaderCircle size={16} className="spin" /> : <UserCheck size={16} />}
                          Approve Access
                        </button>
                      </div>
                    </div>
                    </div>
                  )}
                </div>
              </SettingsAccordionItem>
            );
          })
        ) : (
          <div className="settings-empty-state">
            No {accessRequestStatus} access requests.
          </div>
        )}
      </div>
    </div>
  );

  const renderUsersPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="Owner Only"
        title="Admin & Staff Management"
        description="Manage internal access, customer accounts, and subcontractor records with expandable details."
        action={(
          <button type="button" className="settings-button primary" onClick={handleNewAdmin} disabled={!canMutateSettings}>
            <Plus size={16} />
            Invite New Admin
          </button>
        )}
      />

      {renderAccessRequestsSection()}

      <div className="settings-section-divider" />

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
              const profileCompany = profileUser.company || item.company;
              const profileDepartment = profileUser.department || item.department;
              const profileTime = profileUser.time || profileUser.timezone || item.time || item.timezone;
              const profileRole = profileUser.role_key || profileUser.role || item.role || 'admin';
              const bankAccount = profileUser.bank_account || item.bank_account || {};
              const roleSummary = Array.isArray(item.roles) && item.roles.length > 0
                ? item.roles.map(resolveRoleLabel).join(', ')
                : resolveRoleLabel(profileRole);

              return (
                <SettingsAccordionItem
                  key={item.id}
                  id={`admin-${item.id}`}
                  isOpen={item.id === selectedAdminId}
                  onToggle={() => {
                    if (item.id === selectedAdminId) {
                      setSelectedAdminId('');
                      setAdminForm(emptyAdminForm);
                      return;
                    }
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
                        { label: 'Role', value: roleSummary },
                        { label: 'Phone', value: displayValue(profilePhone) },
                        { label: 'Company', value: displayValue(profileCompany) },
                        { label: 'Department', value: displayValue(profileDepartment) },
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
                            disabled={!canMutateSettings || isCurrentProfile}
                          >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </select>
                        </label>
                      </div>

                      <div className="settings-project-assignment">
                        <div>
                          <span className="settings-kicker">Roles</span>
                          <strong>{normalizeRoleList(adminForm.roles, adminForm.role).map(resolveRoleLabel).join(', ')}</strong>
                        </div>
                        <div className="settings-project-grid">
                          {ROLE_OPTIONS.map((roleOption) => {
                            const roles = normalizeRoleList(adminForm.roles, adminForm.role);
                            const checked = roles.includes(roleOption.id);
                            return (
                              <label key={roleOption.id} className={checked ? 'selected' : ''}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => toggleAdminRole(roleOption.id)}
                                  disabled={!canMutateSettings || isCurrentProfile || (checked && roles.length === 1)}
                                />
                                <span>{roleOption.label}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {!normalizeRoleList(adminForm.roles, adminForm.role).includes('owner') ? (
                        <div className="settings-project-assignment">
                          <div>
                            <span className="settings-kicker">Daily Report Projects</span>
                            <strong>{adminForm.assigned_project_ids.length} selected</strong>
                          </div>
                          <div className="settings-project-grid">
                            {projects.map((project) => {
                              const projectId = project.project_id || project.id;
                              const checked = adminForm.assigned_project_ids.includes(projectId);
                              return (
                                <label key={projectId} className={checked ? 'selected' : ''}>
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggleAdminProject(projectId)}
                                    disabled={!canMutateSettings || isCurrentProfile}
                                  />
                                  <span>{project.name || project.project_name || projectId}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}

                      <div className="settings-form-grid three">
                        <label className="settings-field">
                          <span>Phone</span>
                          <input
                            className="settings-input"
                            value={adminForm.phone}
                            onChange={(event) => updateAdminField('phone', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Company</span>
                          <input
                            className="settings-input"
                            value={adminForm.company}
                            onChange={(event) => updateAdminField('company', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Department</span>
                          <input
                            className="settings-input"
                            value={adminForm.department}
                            onChange={(event) => updateAdminField('department', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                      </div>

                      <div className="settings-form-grid three">
                        <label className="settings-field">
                          <span>Timezone</span>
                          <input
                            className="settings-input"
                            value={adminForm.time}
                            onChange={(event) => updateAdminField('time', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Bank Name</span>
                          <input
                            className="settings-input"
                            value={adminForm.bank_account.bank_name}
                            onChange={(event) => updateAdminBankField('bank_name', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Account No.</span>
                          <input
                            className="settings-input"
                            value={adminForm.bank_account.account_no}
                            onChange={(event) => updateAdminBankField('account_no', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                        <label className="settings-field">
                          <span>Account Name</span>
                          <input
                            className="settings-input"
                            value={adminForm.bank_account.account_name}
                            onChange={(event) => updateAdminBankField('account_name', event.target.value)}
                            disabled={!canMutateSettings}
                          />
                        </label>
                      </div>

                      <div className="settings-editor-actions">
                        <span>{isCurrentProfile ? 'You can edit profile fields for yourself, but role and status changes are blocked.' : 'Managed admin record.'}</span>
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

          <div className="settings-project-assignment">
            <div>
              <span className="settings-kicker">Roles</span>
              <strong>{normalizeRoleList(adminForm.roles, adminForm.role).map(resolveRoleLabel).join(', ')}</strong>
            </div>
            <div className="settings-project-grid">
              {ROLE_OPTIONS.map((roleOption) => {
                const roles = normalizeRoleList(adminForm.roles, adminForm.role);
                const checked = roles.includes(roleOption.id);
                return (
                  <label key={roleOption.id} className={checked ? 'selected' : ''}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleAdminRole(roleOption.id)}
                      disabled={!canMutateSettings || (checked && roles.length === 1)}
                    />
                    <span>{roleOption.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {!normalizeRoleList(adminForm.roles, adminForm.role).includes('owner') ? (
            <div className="settings-project-assignment">
              <div>
                <span className="settings-kicker">Daily Report Projects</span>
                <strong>{adminForm.assigned_project_ids.length} selected</strong>
              </div>
              <div className="settings-project-grid">
                {projects.map((project) => {
                  const projectId = project.project_id || project.id;
                  const checked = adminForm.assigned_project_ids.includes(projectId);
                  return (
                    <label key={projectId} className={checked ? 'selected' : ''}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleAdminProject(projectId)}
                        disabled={!canMutateSettings}
                      />
                      <span>{project.name || project.project_name || projectId}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ) : null}

          <div className="settings-form-grid three">
            <label className="settings-field">
              <span>Phone</span>
              <input
                className="settings-input"
                value={adminForm.phone}
                onChange={(event) => updateAdminField('phone', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Company</span>
              <input
                className="settings-input"
                value={adminForm.company}
                onChange={(event) => updateAdminField('company', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Department</span>
              <input
                className="settings-input"
                value={adminForm.department}
                onChange={(event) => updateAdminField('department', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
          </div>

          <div className="settings-form-grid three">
            <label className="settings-field">
              <span>Timezone</span>
              <input
                className="settings-input"
                value={adminForm.time}
                onChange={(event) => updateAdminField('time', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Bank Name</span>
              <input
                className="settings-input"
                value={adminForm.bank_account.bank_name}
                onChange={(event) => updateAdminBankField('bank_name', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Account No.</span>
              <input
                className="settings-input"
                value={adminForm.bank_account.account_no}
                onChange={(event) => updateAdminBankField('account_no', event.target.value)}
                disabled={!canMutateSettings}
              />
            </label>
            <label className="settings-field">
              <span>Account Name</span>
              <input
                className="settings-input"
                value={adminForm.bank_account.account_name}
                onChange={(event) => updateAdminBankField('account_name', event.target.value)}
                disabled={!canMutateSettings}
              />
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

      <CustomerManagementSection
        canEdit={canMutateCustomers}
        customerForm={customerForm}
        customers={customers}
        filteredCustomers={filteredCustomers}
        onCopy={handleCopyCustomerProfile}
        onFieldChange={updateCustomerField}
        onResetLine={handleResetCustomerLine}
        onSave={handleSaveCustomer}
        onSearchChange={setCustomerSearch}
        onSelect={setSelectedCustomerId}
        onToggleProject={toggleCustomerProject}
        projects={projects}
        saving={saving}
        search={customerSearch}
        selectedCustomerId={selectedCustomerId}
      />

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
                  if (isOpen) {
                    setSelectedSubId('');
                    setSubForm(emptySubForm);
                    return;
                  }
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
                      {item.line_uid ? 'LINE Connected' : 'LINE Not Connected'}
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
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Default Contact Name</span>
                        <input
                          className="settings-input"
                          value={subForm.contact_name}
                          onChange={(event) => updateSubField('contact_name', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Default Phone</span>
                        <input
                          className="settings-input"
                          value={subForm.phone}
                          onChange={(event) => updateSubField('phone', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Tax ID</span>
                        <input
                          className="settings-input"
                          value={subForm.tax_id}
                          onChange={(event) => updateSubField('tax_id', event.target.value)}
                          disabled={!canMutateSubcontractors}
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
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Account No.</span>
                        <input
                          className="settings-input"
                          value={subForm.bank_account.account_no}
                          onChange={(event) => updateBankField('account_no', event.target.value)}
                          disabled={!canMutateSubcontractors}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Account Name</span>
                        <input
                          className="settings-input"
                          value={subForm.bank_account.account_name}
                          onChange={(event) => updateBankField('account_name', event.target.value)}
                          disabled={!canMutateSubcontractors}
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
                        <button type="button" className="settings-button secondary" onClick={() => handleCopySubcontractorProfile(item)} disabled={saving}>
                          <Copy size={16} />
                          Copy Info
                        </button>
                        <button type="button" className="settings-button secondary" onClick={() => handleCopySubcontractorBank(item)} disabled={saving}>
                          <Copy size={16} />
                          Copy Bank
                        </button>
                        <button type="button" className="settings-button secondary" onClick={handleViewKyc} disabled={saving}>
                          <ExternalLink size={16} />
                          View KYC
                        </button>
                        <button type="button" className="settings-button danger" onClick={handleResetLine} disabled={saving || !canMutateSettings}>
                          <Link2Off size={16} />
                          Reset LINE
                        </button>
                        <button type="button" className="settings-button primary" onClick={handleSaveSubcontractor} disabled={saving || !canMutateSubcontractors}>
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

  const renderReadOnlyCustomerPanel = () => (
    <SettingsPanel>
      <SettingsPanelHeader
        kicker="Staff View"
        title="Customer Access"
        description="View customers connected to your assigned projects. Editing is restricted to Owners and Admins."
      />
      <CustomerManagementSection
        canEdit={false}
        customerForm={customerForm}
        customers={customers}
        filteredCustomers={filteredCustomers}
        onCopy={handleCopyCustomerProfile}
        onFieldChange={updateCustomerField}
        onResetLine={handleResetCustomerLine}
        onSave={handleSaveCustomer}
        onSearchChange={setCustomerSearch}
        onSelect={setSelectedCustomerId}
        onToggleProject={toggleCustomerProject}
        projects={customerProjects}
        saving={saving}
        search={customerSearch}
        selectedCustomerId={selectedCustomerId}
      />
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
          <span>{settingsAccessLabel}</span>
          <strong>
            {canMutateSubcontractors
              ? `${admins.length.toLocaleString('en-US')} admins · ${customers.length.toLocaleString('en-US')} customers`
              : `${customers.length.toLocaleString('en-US')} customers`}
          </strong>
        </div>
      </header>

      {error ? <SettingsNotice tone="error">{error}</SettingsNotice> : null}
      {message ? <SettingsNotice tone="success">{message}</SettingsNotice> : null}

      <div className="settings-layout">
        <SettingsLocalNav
          items={canMutateSubcontractors ? NAV_ITEMS : NAV_ITEMS.filter((item) => item.id === 'users')}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        <div className="settings-content">
          {activeTab === 'general' ? renderGeneralPanel() : null}
          {activeTab === 'users'
            ? canMutateSubcontractors ? renderUsersPanel() : renderReadOnlyCustomerPanel()
            : null}
          {activeTab === 'kyc' ? renderKycPanel() : null}
          {activeTab === 'integrations' ? renderIntegrationsPanel() : null}
        </div>
      </div>
    </div>
  );
}

export default SettingPage;
