import { useState } from 'react';
import { ArrowLeft, Edit2 } from 'lucide-react';

interface MemberDetailsProps {
  memberId: string;
  memberName: string;
  onBack: () => void;
  onSuspendAccount: (memberId: string, memberName: string) => void;
}

interface Permission {
  name: string;
  description: string;
  enabled: boolean;
}

interface Activity {
  date: string;
  time: string;
  action: string;
  resource: string;
  ipAddress: string;
}

export default function MemberDetailsScreen({ memberId, memberName, onBack, onSuspendAccount }: MemberDetailsProps) {
  const [permissions, setPermissions] = useState<Permission[]>([
    {
      name: 'Can Approve Invoices',
      description: 'Allows user to finalize financial payouts',
      enabled: true
    },
    {
      name: 'Can Edit BOQ',
      description: 'Modify Bill of Quantities contracts',
      enabled: true
    },
    {
      name: 'Admin Panel Access',
      description: 'Full administration and management system',
      enabled: false
    }
  ]);

  const activities: Activity[] = [
    {
      date: 'Oct 24, 2023',
      time: '14:32',
      action: 'Approved BOQ Update',
      resource: 'PRJ-294 Alpha Tower',
      ipAddress: '192.168.1.45'
    },
    {
      date: 'Oct 24, 2023',
      time: '09:15',
      action: 'Logged in',
      resource: 'System Portal',
      ipAddress: '192.168.1.45'
    }
  ];

  const memberData = {
    id: 'EMI-4092',
    name: 'John Doe',
    status: 'ACTIVE',
    profileImage: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop',
    personal: {
      fullName: 'Jonathan Edward Doe',
      email: 'john.doe@projects001.com',
      department: 'Construction Management',
      joiningDate: 'October 12, 2021',
      location: 'London Headquarters'
    },
    roleAndPermissions: {
      role: 'Project Manager',
      assignedProjects: [
        'PRJ-294 Alpha Tower',
        'PRJ-301 Marina Phase 2'
      ]
    }
  };

  const togglePermission = (index: number) => {
    setPermissions(prev =>
      prev.map((perm, i) =>
        i === index ? { ...perm, enabled: !perm.enabled } : perm
      )
    );
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#FAF8F6]">
      <div className="flex flex-col h-full">
        {/* Header with back button */}
        <div className="bg-white border-b border-zinc-200/60 px-8 py-6 sticky top-0 z-10">
          <div className="max-w-6xl mx-auto">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-zinc-600 hover:text-zinc-900 transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Settings {`>`} User Management</span>
            </button>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="w-20 h-20 rounded-lg overflow-hidden bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                  <span className="text-2xl font-bold text-white">JD</span>
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-2xl font-bold text-zinc-900">{memberData.name}</h1>
                    <span className="inline-block px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">
                      {memberData.status}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-600">Employee ID: {memberData.id}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onSuspendAccount(memberId, memberData.name)}
                  className="px-4 py-2.5 border border-zinc-200 text-zinc-900 font-medium rounded-lg hover:bg-zinc-50 transition-colors"
                >
                  Suspend Account
                </button>
                <button className="px-4 py-2.5 bg-[#3F5E53] text-white font-medium rounded-lg hover:bg-[#344E44] transition-colors flex items-center gap-2">
                  <Edit2 className="w-4 h-4" />
                  Edit Member Details
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-8 py-8">
            <div className="grid grid-cols-3 gap-8">
              {/* Left column - Personal Information */}
              <div className="col-span-1">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <div className="flex items-center gap-2 mb-6">
                    <div className="w-5 h-5 rounded-full bg-zinc-300"></div>
                    <h2 className="text-lg font-bold text-zinc-900">Personal Information</h2>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Full Name</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberData.personal.fullName}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Email</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberData.personal.email}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Department</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberData.personal.department}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Joining Date</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberData.personal.joiningDate}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Location</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberData.personal.location}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right column - Role & Permissions */}
              <div className="col-span-2">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-zinc-300"></div>
                      <h2 className="text-lg font-bold text-zinc-900">Role & Permissions</h2>
                    </div>
                    <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider bg-zinc-100 px-3 py-1 rounded">
                      Project Manager
                    </span>
                  </div>

                  {/* Assigned Projects Section */}
                  <div className="mb-8">
                    <h3 className="text-sm font-semibold text-zinc-900 mb-4">Assigned Projects</h3>
                    <div className="space-y-2">
                      {memberData.roleAndPermissions.assignedProjects.map((project, idx) => (
                        <div key={idx} className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
                          <span className="inline-block w-2 h-2 bg-emerald-500 rounded-full"></span>
                          <span className="text-sm text-zinc-900 font-medium">{project}</span>
                        </div>
                      ))}
                    </div>
                    <button className="mt-4 text-sm text-[#3F5E53] font-semibold hover:text-[#344E44] transition-colors">
                      + Assign Project
                    </button>
                  </div>

                  {/* Permissions Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900 mb-4">Specific Permissions</h3>
                    <div className="space-y-4">
                      {permissions.map((permission, idx) => (
                        <div
                          key={idx}
                          className="flex items-start justify-between p-4 border border-zinc-200/60 rounded-lg hover:bg-zinc-50/50 transition-colors"
                        >
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-zinc-900">{permission.name}</p>
                            <p className="text-xs text-zinc-600 mt-1">{permission.description}</p>
                          </div>
                          <button
                            onClick={() => togglePermission(idx)}
                            className={`relative inline-flex items-center h-5 w-9 rounded-full transition-colors ml-4 flex-shrink-0 ${
                              permission.enabled
                                ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                                : 'bg-gray-300'
                            }`}
                          >
                            <div
                              className={`h-4 w-4 bg-white rounded-full transition-transform ${
                                permission.enabled ? 'translate-x-4' : 'translate-x-0.5'
                              }`}
                            />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity Section - Full width */}
            <div className="mt-8 bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-full bg-zinc-300"></div>
                  <h2 className="text-lg font-bold text-zinc-900">Recent Activity</h2>
                </div>
                <button className="text-xs font-semibold text-zinc-600 hover:text-zinc-900 transition-colors">
                  View Full Log
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200/60">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">DATE & TIME</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">ACTION</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">TARGET RESOURCE</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">IP ADDRESS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activities.map((activity, idx) => (
                      <tr key={idx} className="border-b border-zinc-200/60 hover:bg-zinc-50/50 transition-colors">
                        <td className="px-4 py-4 text-zinc-600 font-medium">
                          {activity.date} - {activity.time}
                        </td>
                        <td className="px-4 py-4 text-zinc-900 font-medium">{activity.action}</td>
                        <td className="px-4 py-4 text-zinc-600">{activity.resource}</td>
                        <td className="px-4 py-4 text-zinc-600">{activity.ipAddress}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
