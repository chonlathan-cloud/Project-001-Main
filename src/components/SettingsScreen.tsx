import { useState } from 'react';
import { Eye, EyeOff, Copy, FileText, Database, Globe, MoreVertical } from 'lucide-react';
import type { ReactNode } from 'react';

interface SettingsState {
  emailNotifications: boolean;
  darkMode: boolean;
  defaultCurrency: string;
}

interface KYCRules {
  commercialRegistration: boolean;
  vatRegistration: boolean;
  professionalLicense: boolean;
  bankAccountVerification: boolean;
}

interface Integration {
  id: string;
  name: string;
  icon: ReactNode;
  description: string;
  status: 'connected' | 'disconnected';
  metadata?: string;
  isBeta?: boolean;
}

interface AdminMember {
  id: string;
  initials: string;
  name: string;
  email: string;
  department: string;
  role: string;
  status: boolean;
  employeeId?: string;
}

interface SettingsScreenProps {
  onNavigateToMember?: (memberId: string) => void;
}

interface SubcontractorMember {
  id: string;
  company: string;
  contact: string;
  lineIdStatus: 'connected' | 'pending' | 'disconnected';
  kycStatus: 'approved' | 'pending_review' | 'rejected';
}

export default function SettingsScreen({ onNavigateToMember }: SettingsScreenProps) {
  const [settings, setSettings] = useState<SettingsState>({
    emailNotifications: true,
    darkMode: false,
    defaultCurrency: 'USD'
  });

  const [kycRules, setKYCRules] = useState<KYCRules>({
    commercialRegistration: true,
    vatRegistration: false,
    professionalLicense: true,
    bankAccountVerification: true
  });

  const [activeTab, setActiveTab] = useState('general');
  const [hasChanges, setHasChanges] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeModelVersion, setActiveModelVersion] = useState('Gemini 1.5 Pro');

  const [adminMembers, setAdminMembers] = useState<AdminMember[]>([
    {
      id: '1',
      initials: 'JD',
      name: 'John Doe',
      email: 'john.doe@projects-001.com',
      department: 'Operations',
      role: 'Project Manager',
      status: true,
      employeeId: 'EMI-4092'
    },
    {
      id: '2',
      initials: 'AS',
      name: 'Alice Smith',
      email: 'alice.smith@projects-001.com',
      department: 'Finance',
      role: 'Financial Manager',
      status: true,
      employeeId: 'EMI-4093'
    },
    {
      id: '3',
      initials: 'RJ',
      name: 'Robert Jones',
      email: 'robert.jones@projects-001.com',
      department: 'Engineering',
      role: 'Viewer',
      status: false,
      employeeId: 'EMI-4094'
    }
  ]);

  const [subcontractors, setSubcontractors] = useState<SubcontractorMember[]>([
    {
      id: '1',
      company: 'BuildRight Construction Ltd.',
      contact: 'David Chen',
      lineIdStatus: 'connected',
      kycStatus: 'approved'
    },
    {
      id: '2',
      company: 'SteelWorks Inc.',
      contact: 'Sarah Miller',
      lineIdStatus: 'pending',
      kycStatus: 'pending_review'
    },
    {
      id: '3',
      company: 'Apex Electrical',
      contact: 'Michael Brown',
      lineIdStatus: 'connected',
      kycStatus: 'rejected'
    },
    {
      id: '4',
      company: 'Apex Builders Co.',
      contact: 'Somchai Prasert',
      lineIdStatus: 'connected',
      kycStatus: 'approved'
    }
  ]);

  const integrations: Integration[] = [
    {
      id: 'google-sheets',
      name: 'Google Sheets API',
      icon: <FileText className="w-8 h-8 text-blue-600" />,
      description: 'Financial & BOQ Sync',
      status: 'connected',
      metadata: 'Last sync: 2 hours ago'
    },
    {
      id: 'google-firebase',
      name: 'Google Firebase',
      icon: <Database className="w-8 h-8 text-orange-500" />,
      description: 'Real-time Data Mirroring',
      status: 'connected',
      metadata: 'Last backup: 12 Oct 2024'
    },
    {
      id: 'vertex-ai',
      name: 'Vertex AI Model',
      icon: <Globe className="w-8 h-8 text-purple-600" />,
      description: 'Powers "Chat AI" contextual analysis',
      status: 'connected',
      isBeta: true
    }
  ];

  const handleToggle = (key: keyof SettingsState) => {
    setSettings(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
    setHasChanges(true);
  };

  const handleKYCToggle = (key: keyof KYCRules) => {
    setKYCRules(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
    setHasChanges(true);
  };

  const handleCurrencyChange = (value: string) => {
    setSettings(prev => ({
      ...prev,
      defaultCurrency: value
    }));
    setHasChanges(true);
  };

  const handleSaveChanges = () => {
    console.log('Settings saved:', settings);
    console.log('KYC Rules saved:', kycRules);
    setHasChanges(false);
  };

  const handleCancel = () => {
    setSettings({
      emailNotifications: true,
      darkMode: false,
      defaultCurrency: 'USD'
    });
    setKYCRules({
      commercialRegistration: true,
      vatRegistration: false,
      professionalLicense: true,
      bankAccountVerification: true
    });
    setHasChanges(false);
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-8 py-6 border-b border-zinc-200/60">
        <h1 className="text-2xl font-bold text-zinc-900">Settings</h1>
        <p className="text-sm text-zinc-600 mt-1">Manage your platform preferences and integrations.</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <div className="flex gap-8">
            {/* Sidebar Navigation */}
            <div className="w-48 flex-shrink-0">
              <nav className="space-y-2">
                <button
                  onClick={() => setActiveTab('general')}
                  className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors ${
                    activeTab === 'general'
                      ? 'bg-zinc-100 text-zinc-900'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                  }`}
                >
                  General
                </button>
                <button
                  onClick={() => setActiveTab('kyc')}
                  className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors ${
                    activeTab === 'kyc'
                      ? 'bg-zinc-100 text-zinc-900'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                  }`}
                >
                  Subcontractor KYC
                </button>
                <button
                  onClick={() => setActiveTab('integrations')}
                  className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors ${
                    activeTab === 'integrations'
                      ? 'bg-zinc-100 text-zinc-900'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                  }`}
                >
                  Integrations
                </button>
                <button
                  onClick={() => setActiveTab('user_management')}
                  className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors ${
                    activeTab === 'user_management'
                      ? 'bg-zinc-100 text-zinc-900'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                  }`}
                >
                  User Management (Owner Only)
                </button>
              </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1">
              {activeTab === 'general' && (
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-8">
                  <h2 className="text-xl font-bold text-zinc-900 mb-6">General Preferences</h2>

                  {/* Email Notifications Setting */}
                  <div className="mb-8 pb-8 border-b border-zinc-200/60 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-900">Email Notifications</h3>
                      <p className="text-sm text-zinc-500 mt-1">Receive daily summary reports and urgent alerts.</p>
                    </div>
                    <div className="relative inline-flex items-center h-6 w-11 bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-full transition-colors cursor-pointer"
                      onClick={() => handleToggle('emailNotifications')}
                      role="switch"
                      aria-checked={settings.emailNotifications}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          settings.emailNotifications ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Dark Mode Setting */}
                  <div className="mb-8 pb-8 border-b border-zinc-200/60 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-900">Dark Mode</h3>
                      <p className="text-sm text-zinc-500 mt-1">Toggle dark theme across the admin portal.</p>
                    </div>
                    <div className="relative inline-flex items-center h-6 w-11 bg-gray-300 rounded-full transition-colors cursor-pointer"
                      onClick={() => handleToggle('darkMode')}
                      role="switch"
                      aria-checked={settings.darkMode}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          settings.darkMode ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Default Currency Setting */}
                  <div className="mb-8 flex items-start gap-6">
                    <div className="flex-1">
                      <h3 className="font-semibold text-zinc-900 mb-2">Default Currency</h3>
                    </div>
                    <select
                      value={settings.defaultCurrency}
                      onChange={(e) => handleCurrencyChange(e.target.value)}
                      className="px-4 py-2.5 border border-zinc-200 rounded-lg bg-white text-zinc-900 font-medium text-sm hover:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    >
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                      <option value="AUD">AUD (A$)</option>
                      <option value="CAD">CAD (C$)</option>
                      <option value="SGD">SGD (S$)</option>
                      <option value="INR">INR (₹)</option>
                      <option value="THB">THB (฿)</option>
                    </select>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-end gap-3 pt-6 border-t border-zinc-200/60">
                    <button
                      onClick={handleCancel}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 border border-zinc-300 text-zinc-700 font-semibold rounded-lg hover:bg-zinc-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveChanges}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 bg-[#3F5E53] text-white font-semibold rounded-lg hover:bg-[#344E44] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'kyc' && (
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-8">
                  <h2 className="text-xl font-bold text-zinc-900 mb-2">Subcontractor KYC Rules</h2>
                  <p className="text-sm text-zinc-600 mb-8">Define mandatory documentation and verification requirements for subcontractors during onboarding. These settings govern the automated approval pipeline.</p>

                  {/* Commercial Registration */}
                  <div className="mb-6 pb-6 border-b border-zinc-200/60 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-zinc-900">Commercial Registration</h3>
                        <span className="text-xs font-semibold bg-zinc-800 text-white px-2.5 py-0.5 rounded">REQUIRED</span>
                      </div>
                      <p className="text-sm text-zinc-500">Valid CR certificate issued within the last 12 months.</p>
                    </div>
                    <div
                      className={`relative inline-flex items-center h-6 w-11 rounded-full transition-colors cursor-pointer flex-shrink-0 ${
                        kycRules.commercialRegistration
                          ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                          : 'bg-gray-300'
                      }`}
                      onClick={() => handleKYCToggle('commercialRegistration')}
                      role="switch"
                      aria-checked={kycRules.commercialRegistration}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          kycRules.commercialRegistration ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* VAT Registration */}
                  <div className="mb-6 pb-6 border-b border-zinc-200/60 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-zinc-900">VAT Registration (P.P.20)</h3>
                        <span className="text-xs font-semibold bg-zinc-100 text-zinc-700 px-2.5 py-0.5 rounded">OPTIONAL</span>
                      </div>
                      <p className="text-sm text-zinc-500">Tax certificate for sub-entities exceeding annual threshold.</p>
                    </div>
                    <div
                      className={`relative inline-flex items-center h-6 w-11 rounded-full transition-colors cursor-pointer flex-shrink-0 ${
                        kycRules.vatRegistration
                          ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                          : 'bg-gray-300'
                      }`}
                      onClick={() => handleKYCToggle('vatRegistration')}
                      role="switch"
                      aria-checked={kycRules.vatRegistration}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          kycRules.vatRegistration ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Professional License */}
                  <div className="mb-6 pb-6 border-b border-zinc-200/60 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-zinc-900">Professional License</h3>
                        <span className="text-xs font-semibold bg-zinc-800 text-white px-2.5 py-0.5 rounded">REQUIRED</span>
                      </div>
                      <p className="text-sm text-zinc-500">Trade-specific licensing (e.g., MEP, Civil) verified via central registry.</p>
                    </div>
                    <div
                      className={`relative inline-flex items-center h-6 w-11 rounded-full transition-colors cursor-pointer flex-shrink-0 ${
                        kycRules.professionalLicense
                          ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                          : 'bg-gray-300'
                      }`}
                      onClick={() => handleKYCToggle('professionalLicense')}
                      role="switch"
                      aria-checked={kycRules.professionalLicense}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          kycRules.professionalLicense ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Bank Account Verification */}
                  <div className="mb-8 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-zinc-900">Bank Account Verification</h3>
                        <span className="text-xs font-semibold bg-zinc-800 text-white px-2.5 py-0.5 rounded">REQUIRED</span>
                      </div>
                      <p className="text-sm text-zinc-500">IBAN certification letter stamped by the issuing financial institution.</p>
                    </div>
                    <div
                      className={`relative inline-flex items-center h-6 w-11 rounded-full transition-colors cursor-pointer flex-shrink-0 ${
                        kycRules.bankAccountVerification
                          ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                          : 'bg-gray-300'
                      }`}
                      onClick={() => handleKYCToggle('bankAccountVerification')}
                      role="switch"
                      aria-checked={kycRules.bankAccountVerification}
                    >
                      <div
                        className={`h-5 w-5 bg-white rounded-full transition-transform ${
                          kycRules.bankAccountVerification ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-end gap-3 pt-6 border-t border-zinc-200/60">
                    <button
                      onClick={handleCancel}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 border border-zinc-300 text-zinc-700 font-semibold rounded-lg hover:bg-zinc-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveChanges}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 bg-[#3F5E53] text-white font-semibold rounded-lg hover:bg-[#344E44] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'integrations' && (
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-8">
                  <div className="mb-8">
                    <h2 className="text-xl font-bold text-zinc-900 mb-2">Integrations & API</h2>
                    <p className="text-sm text-zinc-600">Connect external tools to synchronize project data and enhance automation workflows.</p>
                  </div>

                  {/* Integration Cards Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
                    {integrations.map((integration) => (
                      <div key={integration.id} className="border border-zinc-200/60 rounded-xl p-6 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-start gap-4">
                            <div className="bg-zinc-100 p-2 rounded-lg">
                              {integration.icon}
                            </div>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-bold text-zinc-900">{integration.name}</h3>
                                {integration.isBeta && (
                                  <span className="text-xs font-bold bg-purple-100 text-purple-700 px-2.5 py-1 rounded">BETA</span>
                                )}
                              </div>
                              <p className="text-sm text-zinc-600">{integration.description}</p>
                            </div>
                          </div>
                        </div>
                        {integration.metadata && (
                          <div className="flex items-center gap-2 text-sm">
                            <span className="inline-block w-2 h-2 bg-emerald-500 rounded-full"></span>
                            <span className="text-emerald-700 font-medium">CONNECTED</span>
                            <span className="text-zinc-500 ml-auto">{integration.metadata}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Vertex AI Model Version Section */}
                  <div className="border border-zinc-200/60 rounded-xl p-6 mb-12">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-zinc-900">Active Model Version</h3>
                        <p className="text-sm text-zinc-600 mt-1">Select the AI model version for enhanced analysis features.</p>
                      </div>
                      <select
                        value={activeModelVersion}
                        onChange={(e) => {
                          setActiveModelVersion(e.target.value);
                          setHasChanges(true);
                        }}
                        className="px-4 py-2.5 border border-zinc-200 rounded-lg bg-white text-zinc-900 font-medium text-sm hover:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                      >
                        <option>Gemini 1.5 Pro</option>
                        <option>Gemini 1.0 Standard</option>
                        <option>Gemini 1.0 Lite</option>
                      </select>
                    </div>
                  </div>

                  {/* Authentication Section */}
                  <div className="border-t border-zinc-200/60 pt-8">
                    <h3 className="font-bold text-zinc-900 mb-6">Authentication</h3>
                    
                    <div className="mb-8">
                      <label className="block text-sm font-semibold text-zinc-900 mb-3">Global API Key</label>
                      <div className="flex gap-3">
                        <div className="flex-1 flex items-center gap-3 px-4 py-3 bg-zinc-100 border border-zinc-200 rounded-lg">
                          <input
                            type={showApiKey ? 'text' : 'password'}
                            value="••••••••••••••••••••••••••••••••"
                            readOnly
                            className="flex-1 bg-transparent text-zinc-600 font-mono text-sm focus:outline-none"
                          />
                          <button
                            onClick={() => setShowApiKey(!showApiKey)}
                            className="text-zinc-500 hover:text-zinc-700 transition-colors"
                            title={showApiKey ? 'Hide' : 'Show'}
                          >
                            {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                          <button
                            onClick={() => navigator.clipboard.writeText('your-api-key-here')}
                            className="text-zinc-500 hover:text-zinc-700 transition-colors"
                            title="Copy"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-500 mt-2">This key provides read/write access to all connected project modules. Keep it secure.</p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-end gap-3 pt-6 border-t border-zinc-200/60">
                    <button
                      onClick={handleCancel}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 border border-zinc-300 text-zinc-700 font-semibold rounded-lg hover:bg-zinc-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveChanges}
                      disabled={!hasChanges}
                      className="px-6 py-2.5 bg-[#3F5E53] text-white font-semibold rounded-lg hover:bg-[#344E44] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'user_management' && (
                <div className="space-y-8">
                  {/* Admin & Staff Management Section */}
                  <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-8">
                    <div className="flex items-start justify-between mb-8">
                      <div>
                        <h2 className="text-xl font-bold text-zinc-900">Admin & Staff Management</h2>
                        <p className="text-sm text-zinc-600 mt-1">Manage internal team members and their portal access levels.</p>
                      </div>
                      <button className="px-4 py-2.5 bg-[#3F5E53] text-white font-semibold rounded-lg hover:bg-[#344E44] transition-colors flex items-center gap-2">
                        <span>+</span> Invite New Admin/PM
                      </button>
                    </div>

                    {/* Admin Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-zinc-200/60">
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">NAME</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">EMAIL</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">DEPARTMENT</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">ROLE</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">STATUS</th>
                          </tr>
                        </thead>
                        <tbody>
                          {adminMembers.map((member) => (
                            <tr key={member.id} className="border-b border-zinc-200/60 hover:bg-zinc-50/50 transition-colors">
                              <td className="px-4 py-4">
                                <button
                                  onClick={() => onNavigateToMember?.(member.id)}
                                  className="flex items-center gap-3 hover:opacity-75 transition-opacity w-full"
                                >
                                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white text-xs font-semibold">
                                    {member.initials}
                                  </div>
                                  <span className="font-medium text-zinc-900 hover:text-[#3F5E53] underline">{member.name}</span>
                                </button>
                              </td>
                              <td className="px-4 py-4 text-zinc-600">{member.email}</td>
                              <td className="px-4 py-4 text-zinc-600">{member.department}</td>
                              <td className="px-4 py-4">
                                <select className="px-3 py-1.5 border border-zinc-200 rounded-md text-zinc-900 font-medium text-sm hover:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors bg-white">
                                  <option>Project Manager</option>
                                  <option>Financial Manager</option>
                                  <option>Admin</option>
                                  <option>Viewer</option>
                                </select>
                              </td>
                              <td className="px-4 py-4">
                                <div className={`relative inline-flex items-center h-5 w-9 rounded-full transition-colors cursor-pointer ${
                                  member.status
                                    ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                                    : 'bg-gray-300'
                                }`}>
                                  <div
                                    className={`h-4 w-4 bg-white rounded-full transition-transform ${
                                      member.status ? 'translate-x-4' : 'translate-x-0.5'
                                    }`}
                                  />
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Subcontractor Management Section */}
                  <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-8">
                    <div className="mb-8">
                      <h2 className="text-xl font-bold text-zinc-900">Subcontractor Management</h2>
                      <p className="text-sm text-zinc-600 mt-1">Review and manage external vendor compliance and access.</p>
                    </div>

                    {/* Subcontractor Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-zinc-200/60">
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">COMPANY NAME</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">CONTACT PERSON</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">LINE ID STATUS</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">KYC STATUS</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">ACTIONS</th>
                          </tr>
                        </thead>
                        <tbody>
                          {subcontractors.map((subcontractor) => (
                            <tr key={subcontractor.id} className="border-b border-zinc-200/60 hover:bg-zinc-50/50 transition-colors">
                              <td className="px-4 py-4">
                                <button
                                  onClick={() => onNavigateToMember?.(subcontractor.id)}
                                  className="font-medium text-zinc-900 hover:text-blue-600 transition-colors"
                                >
                                  {subcontractor.company}
                                </button>
                              </td>
                              <td className="px-4 py-4 text-zinc-600">{subcontractor.contact}</td>
                              <td className="px-4 py-4">
                                <div className="flex items-center gap-2">
                                  <span className={`inline-block w-2 h-2 rounded-full ${
                                    subcontractor.lineIdStatus === 'connected'
                                      ? 'bg-emerald-500'
                                      : subcontractor.lineIdStatus === 'pending'
                                      ? 'bg-yellow-500'
                                      : 'bg-gray-300'
                                  }`}></span>
                                  <span className={`font-medium ${
                                    subcontractor.lineIdStatus === 'connected'
                                      ? 'text-emerald-700'
                                      : subcontractor.lineIdStatus === 'pending'
                                      ? 'text-yellow-700'
                                      : 'text-gray-700'
                                  }`}>
                                    {subcontractor.lineIdStatus === 'connected' ? 'Connected' : subcontractor.lineIdStatus === 'pending' ? 'Pending Inv.' : 'Disconnected'}
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-4">
                                <span className={`inline-block px-3 py-1.5 rounded text-xs font-semibold border ${
                                  subcontractor.kycStatus === 'approved'
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : subcontractor.kycStatus === 'pending_review'
                                    ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
                                    : 'bg-red-50 text-red-700 border-red-200'
                                }`}>
                                  {subcontractor.kycStatus === 'approved' ? 'APPROVED' : subcontractor.kycStatus === 'pending_review' ? 'PENDING REVIEW' : 'REJECTED'}
                                </span>
                              </td>
                              <td className="px-4 py-4">
                                <button className="text-zinc-400 hover:text-zinc-600 transition-colors">
                                  <MoreVertical className="w-4 h-4" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
