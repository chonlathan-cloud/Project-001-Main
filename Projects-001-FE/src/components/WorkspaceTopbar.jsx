import React, { useMemo } from 'react';
import { Calendar, UserRound } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const routeMeta = [
  {
    match: (path) => path === '/',
    title: 'Dashboard Overview',
    description: 'Financial summary and critical alerts across active projects.',
  },
  {
    match: (path) => path.startsWith('/project'),
    title: 'Projects',
    description: 'Project budgets, BOQ sync status, and execution details.',
  },
  {
    match: (path) => path.startsWith('/approval'),
    title: 'Approvals',
    description: 'Review payment, bill, and input requests waiting for action.',
  },
  {
    match: (path) => path.startsWith('/insights'),
    title: 'Insights',
    description: 'Cross-project financial signals and operational trends.',
  },
  {
    match: (path) => path.startsWith('/chat-ai'),
    title: 'Chat AI',
    description: 'Ask project and finance questions against available records.',
  },
  {
    match: (path) => path.startsWith('/input'),
    title: 'Input',
    description: 'Submit and track project payment or receipt requests.',
  },
  {
    match: (path) => path.startsWith('/profile'),
    title: 'User Profile',
    description: 'Account profile, activity summary, and session details.',
  },
  {
    match: (path) => path.startsWith('/setting'),
    title: 'Settings',
    description: 'Manage admins, subcontractors, and service configuration.',
  },
];

function formatDate(locale = 'en-US') {
  return new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());
}

function isSubcontractorUser(user) {
  return String(user?.role_key || user?.role || '').trim().toLowerCase() === 'subcontractor';
}

function getProfilePath(user) {
  return isSubcontractorUser(user) ? '/profile/me' : '/profile';
}

export default function WorkspaceTopbar({ authUser, pathname }) {
  const isSubcontractor = isSubcontractorUser(authUser);
  const meta = useMemo(
    () => {
      if (isSubcontractor && pathname.startsWith('/input')) {
        return {
          title: 'ส่งคำขอ',
          description: 'อัปโหลดใบเสร็จและส่งรายการรายรับหรือรายจ่ายให้ผู้ดูแลตรวจสอบ',
        };
      }
      if (isSubcontractor && pathname.startsWith('/profile')) {
        return {
          title: 'โปรไฟล์ของฉัน',
          description: 'ข้อมูลติดต่อ บัญชีธนาคาร และข้อมูลสำหรับใช้ในระบบ',
        };
      }
      return routeMeta.find((item) => item.match(pathname)) || routeMeta[0];
    },
    [isSubcontractor, pathname],
  );

  return (
    <header className="workspace-topbar">
      <div>
        <h1 className="workspace-title">{meta.title}</h1>
        <p className="workspace-description">{meta.description}</p>
      </div>

      <div className="workspace-actions">
        <div className="workspace-date-pill">
          <Calendar size={14} strokeWidth={2} />
          <span>{formatDate(isSubcontractor ? 'th-TH' : 'en-US')}</span>
        </div>
        <NavLink to={getProfilePath(authUser)} className="workspace-profile-link">
          <UserRound size={16} strokeWidth={2} />
          <span>{authUser?.display_name || authUser?.email || (isSubcontractor ? 'โปรไฟล์' : 'Profile')}</span>
        </NavLink>
      </div>
    </header>
  );
}
