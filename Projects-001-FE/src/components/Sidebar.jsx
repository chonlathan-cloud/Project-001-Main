import React, { useEffect, useMemo, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  BadgeCheck,
  BarChart3,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  PenSquare,
  Settings,
  UserRound,
} from 'lucide-react';

import {
  clearAuthSession,
  getStoredAuthUser,
  isAdminUser,
  subscribeToAuthChanges,
} from '../auth';
import { signOutFirebaseClient } from '../firebaseClient';
import { logoutLineClient } from '../liffClient';
import Logo from './Logo';

const Sidebar = () => {
  const navigate = useNavigate();
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser());

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser());
    });
  }, []);

  const navItems = useMemo(() => {
    if (isAdminUser(authUser)) {
      return [
        { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
        { name: 'Project', icon: FolderKanban, path: '/project' },
        { name: 'Insights', icon: BarChart3, path: '/insights' },
        { name: 'Input', icon: PenSquare, path: '/input' },
        { name: 'Approval', icon: BadgeCheck, path: '/approval' },
        { name: 'Chat AI', icon: MessageSquare, path: '/chat-ai' },
        { name: 'Profile', icon: UserRound, path: '/profile' },
        { name: 'Setting', icon: Settings, path: '/setting' },
      ];
    }

    return [
      { name: 'Input', icon: PenSquare, path: '/input' },
      { name: 'Profile', icon: UserRound, path: '/profile/me' },
    ];
  }, [authUser]);

  const handleLogout = async () => {
    clearAuthSession();
    await Promise.allSettled([signOutFirebaseClient(), logoutLineClient()]);
    navigate('/login', { replace: true });
  };

  return (
    <aside style={{
      width: '240px',
      backgroundColor: 'var(--sidebar-bg)',
      color: 'white',
      padding: '40px 0',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <Logo />

      <div style={{ padding: '0 20px', marginTop: '20px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <p style={{
          fontSize: '11px',
          fontWeight: '700',
          color: 'var(--text-sidebar)',
          letterSpacing: '1px',
          marginBottom: '16px',
          paddingLeft: '12px',
        }}>MANAGE</p>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '12px',
                cursor: 'pointer',
                backgroundColor: isActive ? 'var(--accent-gold)' : 'transparent',
                color: isActive ? 'white' : 'var(--text-sidebar)',
                transition: 'all 0.2s ease',
                textDecoration: 'none',
              })}
            >
              <item.icon size={20} />
              <span style={{ fontWeight: '500', fontSize: '14px' }}>{item.name}</span>
            </NavLink>
          ))}
        </nav>

        <div style={{ marginTop: 'auto', paddingTop: '20px' }}>
          <div style={{
            padding: '12px 14px',
            borderRadius: '14px',
            backgroundColor: 'rgba(255,255,255,0.06)',
            marginBottom: '12px',
          }}>
            <div style={{ fontSize: '12px', color: 'var(--text-sidebar)' }}>Signed in as</div>
            <div style={{ fontSize: '14px', fontWeight: '700', marginTop: '4px' }}>
              {authUser?.display_name || authUser?.email || authUser?.subcontractor_id || 'User'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-sidebar)', marginTop: '4px' }}>
              {authUser?.role || 'session'}
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '12px 14px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.12)',
              backgroundColor: 'transparent',
              color: 'white',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              fontWeight: '700',
            }}
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
