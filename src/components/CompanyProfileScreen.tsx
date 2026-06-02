import { ArrowLeft, Eye, MessageCircle, Edit, Clock } from 'lucide-react';
import { Subcontractor } from '../types';

interface CompanyProfileScreenProps {
  company: Subcontractor;
  onBack: () => void;
}

export default function CompanyProfileScreen({ company, onBack }: CompanyProfileScreenProps) {
  const statusColorMap = {
    approved: { bg: 'bg-emerald-100', text: 'text-emerald-700', badge: 'APPROVED' },
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', badge: 'PENDING' },
    suspended: { bg: 'bg-red-100', text: 'text-red-700', badge: 'SUSPENDED' },
  };

  const complianceStatusColorMap = {
    verified: { badge: 'VERIFIED', color: 'text-emerald-600' },
    pending: { badge: 'PENDING', color: 'text-amber-600' },
    not_verified: { badge: 'NOT VERIFIED', color: 'text-zinc-600' },
  };

  const statusInfo = statusColorMap[company.status];

  return (
    <div className="flex-1 overflow-y-auto bg-[#FAF8F6]">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="bg-white border-b border-zinc-200/60 px-8 py-6 sticky top-0 z-10">
          <div className="max-w-6xl mx-auto">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-zinc-600 hover:text-zinc-900 transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Settings {'>'} User Management {'>'} Subcontractors</span>
            </button>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-zinc-900">{company.name}</h1>
                <p className="text-sm text-zinc-600 mt-1">
                  {company.registeredName || company.name}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-4 py-2 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 transition-colors text-sm font-medium text-zinc-900">
                  <MessageCircle className="w-4 h-4" />
                  Message via LINE
                </button>
                <button className="flex items-center gap-2 px-4 py-2 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 transition-colors text-sm font-medium text-zinc-900">
                  <Edit className="w-4 h-4" />
                  Edit Details
                </button>
                <button className="w-10 h-10 flex items-center justify-center hover:bg-zinc-100 rounded-lg transition-colors">
                  <Clock className="w-5 h-5 text-zinc-600" />
                </button>
              </div>
            </div>
            <div className={`flex items-center gap-2 mt-4 px-3 py-1 rounded-full w-fit ${statusInfo.bg} ${
              company.status === 'approved' ? 'border border-emerald-200' :
              company.status === 'pending' ? 'border border-amber-200' :
              'border border-red-200'
            }`}>
              <span className={`inline-block w-2 h-2 rounded-full ${
                company.status === 'approved' ? 'bg-emerald-700' :
                company.status === 'pending' ? 'bg-amber-700' :
                'bg-red-700'
              }`}></span>
              <span className={`text-xs font-semibold ${statusInfo.text}`}>{statusInfo.badge}</span>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-8 py-8">
            <div className="grid grid-cols-3 gap-8">
              {/* Left column - Company Information */}
              <div className="col-span-1">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <h2 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
                    📋 Company Information
                  </h2>

                  <div className="space-y-6">
                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Registered Name</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{company.registeredName}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Tax ID</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{company.taxId}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Primary Contact</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{company.primaryContact}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Phone</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{company.phone}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Email</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{company.email}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right column - KYC & Compliance */}
              <div className="col-span-2">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <h2 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
                    🛡️ KYC & Compliance
                  </h2>

                  <div className="space-y-3">
                    {company.compliance.map((item) => {
                      const colorInfo = complianceStatusColorMap[item.status];
                      return (
                        <div key={item.id} className="flex items-center justify-between p-4 border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors">
                          <div className="flex items-center gap-3">
                            <div className={`w-6 h-6 rounded-full border-2 border-emerald-500 flex items-center justify-center flex-shrink-0 ${item.status === 'verified' ? 'bg-emerald-50' : 'bg-zinc-50'}`}>
                              {item.status === 'verified' && (
                                <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                            <span className="text-sm font-medium text-zinc-900">{item.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-semibold ${colorInfo.color}`}>{colorInfo.badge}</span>
                            <Eye className="w-4 h-4 text-zinc-400" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Project History */}
            <div className="mt-8">
              <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                <h2 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
                  ⏱️ Project History
                </h2>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-zinc-200">
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">PROJECT ID & NAME</th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">ROLE / DISCIPLINE</th>
                        <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">CONTRACT VALUE (THB)</th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">STATUS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200">
                      {company.projects.map((project) => {
                        const statusColor = {
                          active: { badge: 'Active', bgColor: 'bg-emerald-100', textColor: 'text-emerald-700' },
                          completed: { badge: 'Completed', bgColor: 'bg-zinc-100', textColor: 'text-zinc-700' },
                          on_hold: { badge: 'On Hold', bgColor: 'bg-amber-100', textColor: 'text-amber-700' },
                        };
                        const status = statusColor[project.status] || statusColor.completed;

                        return (
                          <tr key={project.id} className="hover:bg-zinc-50 transition-colors">
                            <td className="py-4 px-4">
                              <div>
                                <p className="text-sm font-semibold text-zinc-900">{project.code}</p>
                                <p className="text-xs text-zinc-600 mt-0.5">{project.name}</p>
                              </div>
                            </td>
                            <td className="py-4 px-4 text-sm text-zinc-900">{project.role}</td>
                            <td className="py-4 px-4 text-sm font-semibold text-right text-zinc-900">{project.contractValue.toLocaleString()}</td>
                            <td className="py-4 px-4">
                              <span className={`inline-block px-3 py-1 text-xs font-semibold rounded-full ${status.bgColor} ${status.textColor}`}>
                                {status.badge}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {company.projects.length > 3 && (
                  <p className="text-sm text-zinc-600 mt-4">
                    Showing 1 to {Math.min(3, company.projects.length)} of {company.projects.length} entries
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
