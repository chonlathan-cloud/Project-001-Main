import { Bell, HelpCircle, Settings as SettingsIcon, Lock, LogOut, Shield, Smartphone, Loader2, Camera as CameraIcon } from 'lucide-react';
import { useState, useEffect } from 'react';

interface LoginSession {
  id: string;
  device: string;
  browser: string;
  location: string;
  ipAddress: string;
  dateTime: string;
  status: 'ACTIVE NOW' | 'INACTIVE' | 'LOGGED OUT';
}

interface UserData {
  name: string;
  role: string;
  employeeId: string;
  email: string;
  location: string;
  avatar: string;
}

export default function UserProfileScreen() {
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(true);
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [userData, setUserData] = useState<UserData | null>(null);
  const [loginSessions, setLoginSessions] = useState<LoginSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        setIsLoading(true);
        // เปลี่ยน URL เป็น Endpoint จริงของคุณ เช่น /api/user/profile
        const response = await fetch('/api/user/profile');
        if (!response.ok) throw new Error('Failed to fetch profile data');
        
        const data = await response.json();
        setUserData(data.user);
        setLoginSessions(data.sessions);
      } catch (err) {
        console.warn("Backend not found, using preview data:", err);
        // Fallback ข้อมูลจำลองเพื่อให้หน้าจอไม่ว่างเปล่าระหว่างรอ Backend
        setUserData({
          name: 'James Harrison',
          role: 'SYSTEM ADMIN',
          employeeId: 'EMP-4892-A',
          email: 'j.harrison@projects-001.inc',
          location: 'London HQ',
          avatar: 'https://ui-avatars.com/api/?name=James+Harrison&background=3F5E53&color=fff'
        });
        setLoginSessions([
          {
            id: '1',
            device: 'MacBook Pro - Chrome',
            browser: 'Chrome',
            location: 'London, UK',
            ipAddress: '192.168.1.105',
            dateTime: 'Oct 24, 09:12 AM',
            status: 'ACTIVE NOW'
          }
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfileData();
  }, []);

  const toggleSessionSelection = (id: string) => {
    setSelectedSessions(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const getStatusColor = (status: LoginSession['status']) => {
    switch (status) {
      case 'ACTIVE NOW':
        return 'text-green-600';
      case 'INACTIVE':
        return 'text-orange-500';
      case 'LOGGED OUT':
        return 'text-gray-400';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusBgColor = (status: LoginSession['status']) => {
    switch (status) {
      case 'ACTIVE NOW':
        return 'bg-green-50 text-green-700';
      case 'INACTIVE':
        return 'bg-orange-50 text-orange-700';
      case 'LOGGED OUT':
        return 'bg-gray-50 text-gray-700';
      default:
        return 'bg-gray-50 text-gray-700';
    }
  };

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center h-[calc(100vh-100px)]">
        <p className="text-red-500 font-medium">Error: {error}</p>
      </div>
    );
  }

  if (isLoading || !userData) {
    return (
      <div className="flex-1 flex items-center justify-center h-[calc(100vh-100px)]">
        <Loader2 className="w-8 h-8 text-[#3F5E53] animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-8 py-8 md:py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-zinc-900 mb-2">User Profile</h1>
          <p className="text-zinc-600">Manage your administrative account settings and security preferences.</p>
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Left Column: User Profile Card */}
          <div className="col-span-1">
            <div className="bg-white rounded-xl border border-zinc-200/80 p-8 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
              {/* User Avatar */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <img
                    src={userData.avatar}
                    alt={userData.name}
                    className="w-32 h-32 rounded-full object-cover border-4 border-zinc-100"
                  />
                  <button className="absolute bottom-2 right-2 bg-zinc-900 hover:bg-zinc-800 rounded-full p-2 text-white transition-colors">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* User Name and Role */}
              <h2 className="text-2xl font-bold text-zinc-900 text-center mb-3">{userData.name}</h2>
              <div className="flex justify-center mb-6">
                <span className="px-3 py-1 bg-[#3F5E53] text-white text-xs font-semibold rounded-full">
                  {userData.role}
                </span>
              </div>

              {/* User Details */}
              <div className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Employee ID</p>
                  <p className="text-zinc-900 font-medium">{userData.employeeId}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Email Address</p>
                  <p className="text-zinc-900 font-medium text-sm break-all">{userData.email}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Location</p>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <p className="text-zinc-900 font-medium">{userData.location}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Settings and Sessions */}
          <div className="col-span-2 space-y-8">
            {/* Security Settings Section */}
            <div className="bg-white rounded-xl border border-zinc-200/80 p-8 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-bold text-zinc-900">Security Settings</h3>
                  <p className="text-sm text-zinc-600">Manage your password and authentication methods.</p>
                </div>
                <button className="px-4 py-2 border border-zinc-300 rounded-lg text-zinc-700 hover:bg-zinc-50 transition-colors font-medium text-sm">
                  Change Password
                </button>
              </div>

              {/* Two-Factor Authentication */}
              <div className="flex items-start gap-4 pt-4 border-t border-zinc-100">
                <div className="mt-1">
                  <Shield className="w-5 h-5 text-zinc-400" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-zinc-900 mb-1">Two-Factor Authentication</h4>
                  <p className="text-sm text-zinc-600">Currently active via Authenticator App.</p>
                </div>
                <span className="px-3 py-1 bg-green-50 text-green-700 text-xs font-semibold rounded-full">
                  ENABLED
                </span>
              </div>
            </div>

            {/* Recent Login Sessions Section */}
            <div className="bg-white rounded-xl border border-zinc-200/80 p-8 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
              <h3 className="text-lg font-bold text-zinc-900 mb-2">Recent Login Sessions</h3>
              <p className="text-sm text-zinc-600 mb-6">Review active and recent sessions on your account.</p>

              {/* Sessions Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-3 px-4 font-semibold text-zinc-600 text-xs uppercase">Device & Browser</th>
                      <th className="text-left py-3 px-4 font-semibold text-zinc-600 text-xs uppercase">IP Address</th>
                      <th className="text-left py-3 px-4 font-semibold text-zinc-600 text-xs uppercase">Date & Time</th>
                      <th className="text-left py-3 px-4 font-semibold text-zinc-600 text-xs uppercase">Status</th>
                      <th className="text-left py-3 px-4 font-semibold text-zinc-600 text-xs uppercase"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {loginSessions.map((session) => (
                      <tr key={session.id} className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
                        <td className="py-4 px-4">
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={selectedSessions.includes(session.id)}
                              onChange={() => toggleSessionSelection(session.id)}
                              className="mt-1 w-4 h-4 rounded border-zinc-300 cursor-pointer"
                            />
                            <div>
                              <p className="font-medium text-zinc-900">{session.device}</p>
                              <p className="text-xs text-zinc-500">{session.location}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <p className="text-zinc-700 font-mono text-xs">{session.ipAddress}</p>
                        </td>
                        <td className="py-4 px-4">
                          <p className="text-zinc-700">{session.dateTime}</p>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded-md text-xs font-semibold ${getStatusBgColor(session.status)}`}>
                            {session.status}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          <div className="w-2 h-2 rounded-full" style={{
                            backgroundColor: session.status === 'ACTIVE NOW' ? '#16a34a' : '#d4d4d8'
                          }}></div>
                        </td>
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
