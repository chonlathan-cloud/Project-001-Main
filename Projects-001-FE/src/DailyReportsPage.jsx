import React from 'react';

import { getStoredAuthUser, isAdminPortalUser } from './auth';
import DailyReportReviewWorkspace from './components/dailyReports/DailyReportReviewWorkspace';
import SubcontractorDailyReportWorkspace from './components/dailyReports/SubcontractorDailyReportWorkspace';
import './daily-reports.css';

export default function DailyReportsPage() {
  const user = getStoredAuthUser();
  return isAdminPortalUser(user)
    ? <DailyReportReviewWorkspace />
    : <SubcontractorDailyReportWorkspace />;
}
