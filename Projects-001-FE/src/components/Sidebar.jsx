import React, { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  BadgeCheck,
  Bot,
  Briefcase,
  ClipboardCheck,
  ClipboardList,
  FileCheck2,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  ReceiptText,
  Settings,
  TrendingUp,
  UserRound,
  X,
} from 'lucide-react';

import {
  canMutateAdminData,
  canAccessOwnerArea,
  clearAuthSession,
  getStoredAuthUser,
  getStoredSessionToken,
  isAdminPortalUser,
  isSubcontractorUser,
  subscribeToAuthChanges,
  syncStoredProfileUser,
} from '../auth';
import {
  getAdminInputRequests,
  getCurrentProfile,
  getDailyReportNotifications,
  getInputProjectOptions,
  getInspectionDefects,
  getInspectionRounds,
  getSettingAccessRequests,
} from '../api';
import { signOutFirebaseClient } from '../firebaseClient';
import { logoutLineClient } from '../liffClient';
import logoImage from '../assets/Logo.png';
import { isInspectionDefectOverdue } from './inspection/inspectionUtils';
import { SIDEBAR_BADGES_REFRESH_EVENT } from './sidebarBadgeEvents';
import SidebarToggleButton from './SidebarToggleButton';

const MAX_BADGE_COUNT = 99;
const INSPECTION_ACTIVE_STATUSES = new Set(['OPEN', 'IN_PROGRESS']);
const FLOW_ERROR_KEYS = [
  'flowaccount_sync_error',
  'flowaccount_attachment_error',
  'flowaccount_supplier_invoice_error',
  'flowaccount_payment_error',
];
const FLOW_STATUS_KEYS = [
  'flowaccount_sync_status',
  'flowaccount_attachment_status',
  'flowaccount_supplier_invoice_status',
  'flowaccount_payment_status',
];

function formatBadgeCount(value) {
  const count = Number(value || 0);
  if (!Number.isFinite(count) || count <= 0) return '';
  return count > MAX_BADGE_COUNT ? `${MAX_BADGE_COUNT}+` : count.toLocaleString('en-US');
}

function buildBadge(count, tone = 'warning') {
  const label = formatBadgeCount(count);
  return label ? { count, label, tone } : null;
}

function requestHasCriticalAlert(request) {
  return (
    Boolean(request?.is_duplicate_flag) ||
    Boolean(request?.ocr_low_confidence_fields?.length) ||
    FLOW_ERROR_KEYS.some((key) => Boolean(request?.[key])) ||
    FLOW_STATUS_KEYS.some((key) => String(request?.[key] || '').toUpperCase().includes('FAILED'))
  );
}

function normalizeInspectionStatus(status) {
  return String(status || 'OPEN').trim().toUpperCase();
}

async function loadInspectionTaskBadge() {
  const projectOptions = await getInputProjectOptions();
  const projects = (Array.isArray(projectOptions) ? projectOptions : [])
    .map((project) => ({
      ...project,
      project_id: project.project_id || project.id || '',
    }))
    .filter((project) => project.project_id);

  let activeCount = 0;
  let overdueCount = 0;

  await Promise.all(projects.map(async (project) => {
    const rounds = await getInspectionRounds(project.project_id).catch(() => []);
    const roundList = Array.isArray(rounds) ? rounds : [];

    await Promise.all(roundList.map(async (round) => {
      const roundId = round.id || round.round_id || '';
      if (!roundId) return;

      const defects = await getInspectionDefects(project.project_id, roundId).catch(() => []);
      const defectList = Array.isArray(defects) ? defects : [];

      defectList.forEach((defect) => {
        const status = normalizeInspectionStatus(defect.status);
        if (!INSPECTION_ACTIVE_STATUSES.has(status)) return;
        activeCount += 1;
        if (isInspectionDefectOverdue(defect)) {
          overdueCount += 1;
        }
      });
    }));
  }));

  return buildBadge(activeCount, overdueCount > 0 ? 'danger' : 'warning');
}

function SidebarNavBadge({ badge, label }) {
  if (!badge?.label) return null;

  return (
    <span
      className={`sidebar-nav-count-badge tone-${badge.tone || 'warning'}`}
      aria-label={`${badge.label} ${label} items`}
      title={`${badge.count.toLocaleString('en-US')} ${label} items`}
    >
      {badge.label}
    </span>
  );
}

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

function getSubcontractorRouteTitle(pathname) {
  if (pathname.startsWith('/payment-confirmation')) return 'ยืนยันการรับเงิน';
  if (pathname.startsWith('/daily-reports')) return 'รายงานประจำวัน';
  if (pathname.startsWith('/inspection')) return 'งานตรวจแก้';
  if (pathname.startsWith('/profile')) return 'โปรไฟล์ของฉัน';
  return 'ส่งคำขอ';
}

const Sidebar = ({ collapsed = false, onToggleCollapsed }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser());
  const [navBadges, setNavBadges] = useState({});
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [isMobileViewport, setIsMobileViewport] = useState(() => (
    typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches
  ));
  const profileSyncKeyRef = useRef('');
  const mobileMenuButtonRef = useRef(null);
  const mobileCloseButtonRef = useRef(null);
  const isAdminUser = isAdminPortalUser(authUser);
  const isSubcontractor = isSubcontractorUser(authUser);
  const isDesktopCollapsed = collapsed && !isMobileViewport;
  const userDisplayName =
    authUser?.display_name ||
    authUser?.email ||
    authUser?.subcontractor_id ||
    (isAdminUser ? 'User' : 'ผู้ใช้งาน');

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser());
    });
  }, []);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    const handleChange = (event) => {
      setIsMobileViewport(event.matches);
      if (!event.matches) setMobileNavOpen(false);
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (!isSubcontractor || !isMobileViewport) return undefined;

    document.body.classList.toggle('subcontractor-mobile-nav-open', mobileNavOpen);
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && mobileNavOpen) {
        setMobileNavOpen(false);
        mobileMenuButtonRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    if (mobileNavOpen) {
      window.requestAnimationFrame(() => mobileCloseButtonRef.current?.focus());
    }

    return () => {
      document.body.classList.remove('subcontractor-mobile-nav-open');
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMobileViewport, isSubcontractor, mobileNavOpen]);

  useEffect(() => {
    const sessionToken = getStoredSessionToken();
    const userKey = authUser?.email || authUser?.subcontractor_id || authUser?.id || authUser?.user_id || '';
    const syncKey = `${sessionToken}:${userKey}`;

    if (!sessionToken || !authUser || profileSyncKeyRef.current === syncKey) return;

    let isActive = true;
    profileSyncKeyRef.current = syncKey;

    getCurrentProfile()
      .then((profile) => {
        if (!isActive || !profile?.user) return;
        const syncedUser = syncStoredProfileUser(profile.user);
        if (syncedUser) {
          setAuthUser(syncedUser);
        }
      })
      .catch(() => {
        if (isActive && profileSyncKeyRef.current === syncKey) {
          profileSyncKeyRef.current = '';
        }
      });

    return () => {
      isActive = false;
    };
  }, [authUser]);

  useEffect(() => {
    let isActive = true;

    async function loadNavBadges() {
      if (!authUser) {
        if (isActive) setNavBadges({});
        return;
      }

      if (isAdminUser) {
        const [approvalRequests, accessRequests, dailyReportNotifications] = await Promise.all([
          getAdminInputRequests({ status: 'PENDING_ADMIN' }).catch(() => []),
          canMutateAdminData(authUser) ? getSettingAccessRequests('pending').catch(() => []) : Promise.resolve([]),
          getDailyReportNotifications({ unreadOnly: true }).catch(() => []),
        ]);
        if (!isActive) return;

        setNavBadges({
          approvals: buildBadge(
            approvalRequests.length,
            approvalRequests.some(requestHasCriticalAlert) ? 'danger' : 'warning',
          ),
          dailyReports: buildBadge(dailyReportNotifications.length, 'danger'),
          settings: buildBadge(accessRequests.length, 'warning'),
        });
        return;
      }

      if (isSubcontractorUser(authUser)) {
        const inspectionTasks = await loadInspectionTaskBadge().catch(() => null);
        if (!isActive) return;
        setNavBadges({ inspectionTasks });
        return;
      }

      if (isActive) setNavBadges({});
    }

    loadNavBadges();
    window.addEventListener(SIDEBAR_BADGES_REFRESH_EVENT, loadNavBadges);

    return () => {
      isActive = false;
      window.removeEventListener(SIDEBAR_BADGES_REFRESH_EVENT, loadNavBadges);
    };
  }, [authUser, isAdminUser, location.pathname]);

  const navItems = useMemo(() => {
    if (isAdminUser) {
      const sharedAdminItems = [
        { name: 'Projects', icon: Briefcase, path: '/project' },
        { name: 'Daily Reports', icon: FileCheck2, path: '/daily-reports', badge: navBadges.dailyReports },
        { name: 'Input', icon: ClipboardList, path: '/input' },
        { name: 'Approvals', icon: BadgeCheck, path: '/approval', badge: navBadges.approvals },
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
      { name: 'ยืนยันการรับเงิน', icon: ReceiptText, path: '/payment-confirmation' },
      { name: 'รายงานประจำวัน', icon: FileCheck2, path: '/daily-reports/me' },
      { name: 'งานตรวจแก้', icon: ClipboardCheck, path: '/inspection/tasks', badge: navBadges.inspectionTasks },
      { name: 'โปรไฟล์', icon: UserRound, path: '/profile/me' },
    ];
  }, [authUser, isAdminUser, navBadges]);

  const systemItems = useMemo(() => {
    if (isAdminUser) {
      return [
        { name: 'Settings', icon: Settings, path: '/setting', badge: navBadges.settings },
        { name: 'Support', icon: HelpCircle, path: '/support' },
      ];
    }
    return [];
  }, [isAdminUser, navBadges]);

  const handleLogout = async () => {
    setMobileNavOpen(false);
    clearAuthSession();
    await Promise.allSettled([signOutFirebaseClient(), logoutLineClient()]);
    navigate('/login', { replace: true });
  };

  return (
    <>
      {isSubcontractor ? (
        <header className="subcontractor-mobile-header">
          <img src={logoImage} alt="RAYADEE" />
          <div>
            <span>พื้นที่ผู้รับเหมา</span>
            <strong>{getSubcontractorRouteTitle(location.pathname)}</strong>
          </div>
          <button
            ref={mobileMenuButtonRef}
            type="button"
            onClick={() => setMobileNavOpen(true)}
            aria-controls="primary-sidebar"
            aria-expanded={mobileNavOpen}
            aria-label="เปิดเมนู"
          >
            <Menu size={22} />
          </button>
        </header>
      ) : null}

      {isSubcontractor ? (
        <button
          type="button"
          className={`subcontractor-sidebar-backdrop${mobileNavOpen ? ' open' : ''}`}
          onClick={() => setMobileNavOpen(false)}
          aria-label="ปิดเมนู"
          tabIndex={mobileNavOpen ? 0 : -1}
        />
      ) : null}

      <aside
        id="primary-sidebar"
        className={`app-sidebar${isSubcontractor ? ' subcontractor-sidebar' : ''}${mobileNavOpen ? ' mobile-open' : ''}${isDesktopCollapsed ? ' is-collapsed' : ''}`}
        aria-label={isAdminUser ? 'Admin navigation' : 'เมนูผู้รับเหมา'}
        aria-hidden={isSubcontractor && isMobileViewport ? !mobileNavOpen : undefined}
        inert={isSubcontractor && isMobileViewport && !mobileNavOpen ? '' : undefined}
      >
        <SidebarToggleButton
          collapsed={isDesktopCollapsed}
          onToggle={onToggleCollapsed}
          language={isAdminUser ? 'en' : 'th'}
        />

        <div className="sidebar-brand">
          <img className="sidebar-brand-logo" src={logoImage} alt="RAYADEE" />
          <div className="sidebar-brand-subtitle">
            {isAdminUser ? 'Admin Portal' : 'พื้นที่ผู้รับเหมา'}
          </div>
          {isSubcontractor ? (
            <button
              ref={mobileCloseButtonRef}
              type="button"
              className="subcontractor-sidebar-close"
              onClick={() => {
                setMobileNavOpen(false);
                mobileMenuButtonRef.current?.focus();
              }}
              aria-label="ปิดเมนู"
            >
              <X size={20} />
            </button>
          ) : null}
        </div>

        {canAccessOwnerArea(authUser) ? (
          <button
            type="button"
            className="sidebar-primary-action"
            onClick={() => navigate('/project')}
            aria-label={isDesktopCollapsed ? 'New Project' : undefined}
            title={isDesktopCollapsed ? 'New Project' : undefined}
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
                onClick={() => setMobileNavOpen(false)}
                className={({ isActive }) => `sidebar-nav-link${isActive ? ' active' : ''}`}
                aria-label={isDesktopCollapsed ? item.name : undefined}
                title={isDesktopCollapsed ? item.name : undefined}
              >
                <item.icon size={18} strokeWidth={2} />
                <span className="sidebar-nav-label">{item.name}</span>
                <SidebarNavBadge badge={item.badge} label={item.name} />
              </NavLink>
            ))}
          </nav>

          {systemItems.length > 0 ? (
            <div className="sidebar-system">
              {systemItems.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.path}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) => `sidebar-nav-link${isActive ? ' active' : ''}`}
                  aria-label={isDesktopCollapsed ? item.name : undefined}
                  title={isDesktopCollapsed ? item.name : undefined}
                >
                  <item.icon size={18} strokeWidth={2} />
                  <span className="sidebar-nav-label">{item.name}</span>
                  <SidebarNavBadge badge={item.badge} label={item.name} />
                </NavLink>
              ))}
            </div>
          ) : null}

          <div className="sidebar-footer">
            <div
              className="sidebar-user-card"
              aria-label={isDesktopCollapsed ? userDisplayName : undefined}
              title={isDesktopCollapsed ? userDisplayName : undefined}
              tabIndex={isDesktopCollapsed ? 0 : undefined}
            >
              <SidebarUserAvatar user={authUser} />
              <div className="sidebar-user-meta">
                <div className="sidebar-user-label">
                  {isAdminUser ? 'Signed in as' : 'เข้าสู่ระบบในชื่อ'}
                </div>
                <div className="sidebar-user-name">
                  {userDisplayName}
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
              aria-label={isDesktopCollapsed ? (isAdminUser ? 'Sign Out' : 'ออกจากระบบ') : undefined}
              title={isDesktopCollapsed ? (isAdminUser ? 'Sign Out' : 'ออกจากระบบ') : undefined}
            >
              <LogOut size={16} />
              <span className="sidebar-logout-label">
                {isAdminUser ? 'Sign Out' : 'ออกจากระบบ'}
              </span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
