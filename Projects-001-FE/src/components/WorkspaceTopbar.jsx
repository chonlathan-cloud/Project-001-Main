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

function formatDate() {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());
}

function getProfilePath(user) {
  return user?.role === 'subcontractor' ? '/profile/me' : '/profile';
}

export default function WorkspaceTopbar({ authUser, pathname }) {
  const meta = useMemo(
    () => routeMeta.find((item) => item.match(pathname)) || routeMeta[0],
    [pathname],
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
          <span>{formatDate()}</span>
        </div>
        <NavLink to={getProfilePath(authUser)} className="workspace-profile-link">
          <UserRound size={16} strokeWidth={2} />
          <span>{authUser?.display_name || authUser?.email || 'Profile'}</span>
        </NavLink>
      </div>
    </header>
  );
}
