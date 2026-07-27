import React, { useCallback, useEffect, useState } from 'react';

import CustomerReportWorkspace from './CustomerReportWorkspace';

function readShareState() {
  if (typeof window === 'undefined') return { shareToken: '', reportId: '' };
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  return {
    shareToken: params.get('access') || '',
    reportId: params.get('report') || '',
  };
}

export default function SharedCustomerReportWorkspace() {
  const [shareState, setShareState] = useState(readShareState);

  useEffect(() => {
    const previousTitle = document.title;
    const existingRobots = document.querySelector('meta[name="robots"]');
    const existingReferrer = document.querySelector('meta[name="referrer"]');
    const previousRobots = existingRobots?.getAttribute('content');
    const previousReferrer = existingReferrer?.getAttribute('content');
    const robots = existingRobots || document.createElement('meta');
    const referrer = existingReferrer || document.createElement('meta');

    robots.setAttribute('name', 'robots');
    robots.setAttribute('content', 'noindex, nofollow, noarchive');
    referrer.setAttribute('name', 'referrer');
    referrer.setAttribute('content', 'no-referrer');
    if (!existingRobots) document.head.appendChild(robots);
    if (!existingReferrer) document.head.appendChild(referrer);
    document.title = 'รายงานความคืบหน้าโครงการ | RAYADEE';

    const handleHashChange = () => setShareState(readShareState());
    window.addEventListener('hashchange', handleHashChange);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      document.title = previousTitle;
      if (existingRobots) robots.setAttribute('content', previousRobots || '');
      else robots.remove();
      if (existingReferrer) referrer.setAttribute('content', previousReferrer || '');
      else referrer.remove();
    };
  }, []);

  const selectReport = useCallback((reportId) => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    if (reportId) params.set('report', reportId);
    else params.delete('report');
    const nextHash = params.toString();
    window.history.replaceState(
      window.history.state,
      '',
      `${window.location.pathname}${window.location.search}${nextHash ? `#${nextHash}` : ''}`,
    );
    setShareState(readShareState());
  }, []);

  return (
    <CustomerReportWorkspace
      publicAccess
      shareToken={shareState.shareToken}
      selectedReportId={shareState.reportId}
      onSelectedReportChange={selectReport}
    />
  );
}
