import React, { useEffect, useMemo, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  BadgeCheck,
  Bot,
  Briefcase,
  ClipboardList,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  TrendingUp,
  UserRound,
  Wrench,
} from 'lucide-react';

import {
  canAccessOwnerArea,
  clearAuthSession,
  getStoredAuthUser,
  isAdminPortalUser,
  subscribeToAuthChanges,
} from '../auth';
import { signOutFirebaseClient } from '../firebaseClient';
import { logoutLineClient } from '../liffClient';

function getInitials(user) {
  const source =
    user?.display_name ||
    user?.displayName ||
    user?.name ||
    user?.contact_name ||
    user?.contactName ||
    user?.email ||
    user?.subcontractor_id ||
    'User';
  return String(source)
    .split(/[\s@.-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || 'U';
}

function getAvatarUrl(user) {
  return (
    user?.profile_image_url ||
    user?.profileImageUrl ||
    user?.line_picture_url ||
    user?.linePictureUrl ||
    user?.avatar_url ||
    user?.avatarUrl ||
    user?.picture_url ||
    user?.photo_url ||
    ''
  );
}

function SidebarUserAvatar({ user }) {
  const imageUrl = getAvatarUrl(user);
  const [failedImageUrl, setFailedImageUrl] = useState('');
  const shouldShowImage = imageUrl && failedImageUrl !== imageUrl;

  return (
    <div className="sidebar-user-avatar">
      {shouldShowImage ? (
        <img
          src={imageUrl}
          alt=""
          onError={() => setFailedImageUrl(imageUrl)}
        />
      ) : (
        <span>{getInitials(user)}</span>
      )}
    </div>
  );
}

const Sidebar = () => {
  const navigate = useNavigate();
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser());
  const isAdminUser = isAdminPortalUser(authUser);

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser());
    });
  }, []);

  const navItems = useMemo(() => {
    if (isAdminUser) {
      const sharedAdminItems = [
        { name: 'Projects', icon: Briefcase, path: '/project' },
        { name: 'Input', icon: ClipboardList, path: '/input' },
        { name: 'Approvals', icon: BadgeCheck, path: '/approval' },
        { name: 'Insights', icon: TrendingUp, path: '/insights' },
        { name: 'Profile', icon: UserRound, path: '/profile' },
      ];

      if (!canAccessOwnerArea(authUser)) {
        return sharedAdminItems;
      }

      return [
        { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
        ...sharedAdminItems.slice(0, 3),
        { name: 'Chat AI', icon: Bot, path: '/chat-ai' },
        ...sharedAdminItems.slice(3),
      ];
    }

    return [
      { name: 'ส่งคำขอ', icon: ClipboardList, path: '/input' },
      { name: 'โปรไฟล์', icon: UserRound, path: '/profile/me' },
    ];
  }, [authUser, isAdminUser]);

  const systemItems = useMemo(() => {
    if (isAdminUser) {
      return [
        { name: 'Settings', icon: Settings, path: '/setting' },
        { name: 'Support', icon: HelpCircle, path: '/support' },
      ];
    }
    return [];
  }, [isAdminUser]);

  const handleLogout = async () => {
    clearAuthSession();
    await Promise.allSettled([signOutFirebaseClient(), logoutLineClient()]);
    navigate('/login', { replace: true });
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">
          <Wrench size={18} strokeWidth={2.25} />
        </div>
        <div>
          <div className="sidebar-brand-title">RAYADEE</div>
          <div className="sidebar-brand-subtitle">
            {isAdminUser ? 'Admin Portal' : 'พื้นที่ผู้รับเหมา'}
          </div>
        </div>
      </div>

      {canAccessOwnerArea(authUser) ? (
        <button
          type="button"
          className="sidebar-primary-action"
          onClick={() => navigate('/project')}
        >
          <Plus size={16} strokeWidth={2.5} />
          <span>New Project</span>
        </button>
      ) : null}

      <div className="sidebar-inner">
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `sidebar-nav-link${isActive ? ' active' : ''}`}
            >
              <item.icon size={18} strokeWidth={2} />
              <span>{item.name}</span>
            </NavLink>
          ))}
        </nav>

        {systemItems.length > 0 ? (
          <div className="sidebar-system">
            {systemItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) => `sidebar-nav-link${isActive ? ' active' : ''}`}
              >
                <item.icon size={18} strokeWidth={2} />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </div>
        ) : null}

        <div className="sidebar-footer">
          <div className="sidebar-user-card">
            <SidebarUserAvatar user={authUser} />
            <div className="sidebar-user-meta">
              <div className="sidebar-user-label">
                {isAdminUser ? 'Signed in as' : 'เข้าสู่ระบบในชื่อ'}
              </div>
              <div className="sidebar-user-name">
                {authUser?.display_name || authUser?.email || authUser?.subcontractor_id || (isAdminUser ? 'User' : 'ผู้ใช้งาน')}
              </div>
              <div className="sidebar-user-role">
                {isAdminUser ? authUser?.role || 'session' : 'ผู้รับเหมา'}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="sidebar-logout-button"
          >
            <LogOut size={16} />
            {isAdminUser ? 'Sign Out' : 'ออกจากระบบ'}
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
