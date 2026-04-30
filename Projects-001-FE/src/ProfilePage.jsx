import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, Bell, ChevronDown, User,
  Briefcase, Clock, CheckCircle, TrendingUp, DollarSign, Users, 
  ChevronLeft, ChevronRight 
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
import { fetchData, resetProfileAvatar, uploadProfileAvatar } from './api';
import Loading from './components/Loading';

const StatCard = ({ value, label, subtext, icon }) => {
  const IconComponent = icon;

  return (
    <div style={{
    backgroundColor: 'var(--card-bg)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
    border: '1px solid var(--border-color)',
    height: '100%',
    justifyContent: 'space-between'
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--text-main)', marginBottom: '4px' }}>{value}</div>
        <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-main)' }}>{label}</div>
      </div>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '50%',
        backgroundColor: 'var(--accent-gold)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white'
      }}>
        {IconComponent ? <IconComponent size={24} /> : null}
      </div>
    </div>
    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '16px' }}>{subtext}</div>
  </div>
  );
};

const CalendarWidget = () => {
  // Simple static calendar visual for UI demonstration
  const days = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  const dates = Array.from({ length: 31 }, (_, i) => i + 1);
  // Pad the start with empty slots (assume month starts on Wed)
  const paddedDates = [null, null, null, ...dates, null];

  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      borderRadius: 'var(--radius-lg)',
      padding: '24px',
      boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
      border: '1px solid var(--border-color)',
      height: '100%'
    }}>
      <div style={{ fontSize: '18px', fontWeight: '700', marginBottom: '20px' }}>Calendar</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}><ChevronLeft size={16} /></button>
        <span style={{ fontWeight: '600', color: 'var(--accent-gold)' }}>April 2026</span>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}><ChevronRight size={16} /></button>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', textAlign: 'center', marginBottom: '16px' }}>
        {days.map(d => <div key={d} style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)' }}>{d}</div>)}
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', textAlign: 'center' }}>
        {paddedDates.map((date, index) => (
          <div key={index} style={{ 
            fontSize: '13px', 
            padding: '8px 0',
            backgroundColor: date === 27 ? 'var(--accent-gold)' : 'transparent',
            borderRadius: '50%',
            color: date === 27 ? 'white' : 'var(--text-main)',
            fontWeight: date === 27 ? '600' : '400',
            cursor: date ? 'pointer' : 'default'
          }}>
            {date || '0'}
          </div>
        ))}
      </div>
    </div>
  );
};

const iconMap = {
  'active_projects': Briefcase,
  'pending_approvals': Clock,
  'completed_tasks': CheckCircle,
  'team_members': Users,
  'reports_generated': TrendingUp,
  'budget_managed': DollarSign
};

const buildInitials = (value) => {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return 'U';
  return words.slice(0, 2).map((word) => word.charAt(0).toUpperCase()).join('');
};

const AvatarCircle = ({ name, imageUrl, size = 140 }) => (
  <div style={{
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: '50%',
    backgroundColor: 'var(--accent-gold-light)',
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--accent-gold)',
    border: '4px solid var(--card-bg)',
    boxShadow: '0 0 0 2px var(--accent-gold-light)',
    overflow: 'hidden',
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


const ProfilePage = () => {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [avatarSaving, setAvatarSaving] = useState(false);
  const [avatarError, setAvatarError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('profile');
      // result might be [] from api.js if backend is not ready
      if (Array.isArray(result) && result.length === 0) {
        setProfileData(null);
      } else {
        setProfileData(result);
      }
      setLoading(false);
    };
    loadData();
  }, []);

  const handlePickAvatar = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setAvatarSaving(true);
      setAvatarError('');
      const response = await uploadProfileAvatar(file);
      setProfileData((current) => {
        if (!current?.user) return current;
        return {
          ...current,
          user: {
            ...current.user,
            profile_image_url: response?.profile_image_url || '',
            line_picture_url: response?.line_picture_url || current.user.line_picture_url || '',
            avatar_url: response?.avatar_url || '',
          },
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
        return {
          ...current,
          user: {
            ...current.user,
            profile_image_url: '',
            line_picture_url: response?.line_picture_url || current.user.line_picture_url || '',
            avatar_url: response?.avatar_url || response?.line_picture_url || '',
          },
        };
      });
    } catch (error) {
      setAvatarError(error.message || 'Failed to reset profile avatar.');
    } finally {
      setAvatarSaving(false);
    }
  };

  if (loading) return <Loading />;

  if (!profileData || !profileData.user) {
    return (
      <div style={{ maxWidth: '1400px', margin: '0 auto', textAlign: 'center', padding: '100px 20px' }}>
        <h2 style={{ fontSize: '24px', color: 'var(--text-main)', marginBottom: '16px' }}>กำลังรอเชื่อมต่อข้อมูลจาก Backend...</h2>
        <p style={{ color: 'var(--text-muted)' }}>หน้าต่างโปรไฟล์จะแสดงข้อมูลของคุณเมื่อ API พร้อมใช้งาน</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      
      {/* Top Navigation Bar */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '32px',
        backgroundColor: 'var(--card-bg)',
        padding: '16px 24px',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 4px 15px rgba(0,0,0,0.02)'
      }}>
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" 
            placeholder="Search..." 
            style={{ 
              width: '100%', 
              padding: '12px 16px 12px 42px', 
              borderRadius: '24px', 
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              outline: 'none',
              fontSize: '14px'
            }} 
          />
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontSize: '14px', fontWeight: '500' }}>
            ENG <ChevronDown size={16} />
          </div>
          
          <div style={{ position: 'relative', cursor: 'pointer' }}>
            <Bell size={20} color="var(--text-muted)" />
            <div style={{ 
              position: 'absolute', top: '-4px', right: '-4px', 
              width: '14px', height: '14px', 
              backgroundColor: 'var(--chart-green)', 
              borderRadius: '50%', border: '2px solid white',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontSize: '9px', fontWeight: 'bold'
            }}>
              3
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        
        {/* Left Side: Profile Info Card */}
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: 'var(--radius-lg)',
          padding: '32px 24px',
          boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--accent-gold)', marginBottom: '4px' }}>Today Available</div>
          <div style={{ fontSize: '14px', color: 'var(--text-main)', fontWeight: '500', marginBottom: '32px' }}>From: {profileData?.user?.company || 'N/A'}</div>
          
          <div style={{ position: 'relative', marginBottom: '24px' }}>
            <button style={{ position: 'absolute', left: '-40px', top: '50%', transform: 'translateY(-50%)', background: 'var(--bg-primary)', border: 'none', width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-muted)' }}><ChevronLeft size={16}/></button>
            
            <AvatarCircle
              name={profileData?.user?.contact_name || profileData?.user?.name}
              imageUrl={profileData?.user?.profile_image_url || profileData?.user?.line_picture_url}
              size={140}
            />
            
            <button style={{ position: 'absolute', right: '-40px', top: '50%', transform: 'translateY(-50%)', background: 'var(--bg-primary)', border: 'none', width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-muted)' }}><ChevronRight size={16}/></button>
          </div>
          
          <div style={{ fontSize: '22px', fontWeight: '700', marginBottom: '8px' }}>{profileData?.user?.name || 'Unknown'}</div>
          <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '8px' }}>{profileData?.user?.role || 'N/A'} <span style={{ margin: '0 8px' }}>|</span> {profileData?.user?.time || 'N/A'}</div>
          {profileData?.user?.role === 'Subcontractor' ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={handleAvatarChange}
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '10px', marginTop: '16px' }}>
                <button
                  type="button"
                  onClick={handlePickAvatar}
                  disabled={avatarSaving}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '12px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: '#fff',
                    cursor: avatarSaving ? 'wait' : 'pointer',
                    fontWeight: '600',
                  }}
                >
                  {avatarSaving ? 'Uploading...' : 'Change Photo'}
                </button>
                {profileData?.user?.profile_image_url ? (
                  <button
                    type="button"
                    onClick={handleResetAvatar}
                    disabled={avatarSaving}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '12px',
                      border: '1px solid var(--border-color)',
                      backgroundColor: '#f8f2e6',
                      cursor: avatarSaving ? 'wait' : 'pointer',
                      fontWeight: '600',
                    }}
                  >
                    Use LINE Avatar
                  </button>
                ) : null}
              </div>
              {avatarError ? (
                <div style={{ marginTop: '12px', fontSize: '13px', color: '#b42318' }}>{avatarError}</div>
              ) : null}
            </>
          ) : null}
        </div>

        {/* Right Side: Grid Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          {profileData?.stats?.map((stat) => {
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
      </div>

      {/* Bottom Section: Chart and Calendar */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginTop: '24px' }}>
        
        {/* Bar Chart Section */}
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
          border: '1px solid var(--border-color)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div style={{ fontSize: '18px', fontWeight: '700' }}>Project Activity vs Expenses</div>
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '500', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--chart-green)' }}></span> Activity
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '500', color: 'var(--text-muted)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-gold)' }}></span> Expenses
              </div>
            </div>
          </div>
          
          <div style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={profileData?.chartData || []} margin={{ top: 5, right: 0, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-muted)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-muted)' }} />
                <Tooltip 
                  cursor={{ fill: 'var(--bg-primary)', opacity: 0.5 }}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }}
                />
                <Bar dataKey="Activity" fill="var(--chart-green)" radius={[4, 4, 0, 0]} barSize={12} />
                <Bar dataKey="Expenses" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Calendar Widget Section */}
        <CalendarWidget />

      </div>

    </div>
  );
};

export default ProfilePage;
