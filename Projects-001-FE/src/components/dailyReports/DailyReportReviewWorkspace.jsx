import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BellRing,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  FileCheck2,
  LoaderCircle,
  MessageSquareWarning,
  RefreshCw,
  Save,
  Send,
  Settings2,
  Users,
} from 'lucide-react';

import {
  getDailyReport,
  getDailyReportLineDestination,
  getDailyReportLineDestinationCandidates,
  getDailyReportNotifications,
  getDailyReportProjectSettings,
  getDailyReportProjects,
  getDailyReportQueue,
  publishDailyReport,
  markDailyReportNotificationRead,
  requestDailyReportChanges,
  retryDailyReportDelivery,
  startDailyReportCorrection,
  updateDailyReportProjectSettings,
  updateDailyReportLineDestination,
  updateDailyReportDraft,
} from '../../api';
import { getStoredAuthUser, isOwnerUser } from '../../auth';
import { requestSidebarBadgeRefresh } from '../sidebarBadgeEvents';
import {
  DailyReportNotice,
  DailyReportStatusBadge,
} from './dailyReportUi';
import { formatReportDate } from './dailyReportUtils';
import DailyReportSettingsDialog from './DailyReportSettingsDialog';
import DailyReportEvidenceGallery from './DailyReportEvidenceGallery';
import CustomerReportShareCard from './CustomerReportShareCard';

function draftFromReport(report) {
  return {
    title: report?.title || '',
    summary: report?.summary || '',
    progress_percent: report?.progress_percent ?? '',
    issues: Array.isArray(report?.issues) ? report.issues : [],
    tomorrow_plan: report?.tomorrow_plan || '',
    customer_note: report?.customer_note || '',
  };
}

export default function DailyReportReviewWorkspace() {
  const owner = isOwnerUser(getStoredAuthUser());
  const [reports, setReports] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [report, setReport] = useState(null);
  const [draft, setDraft] = useState(draftFromReport(null));
  const [statusFilter, setStatusFilter] = useState('');
  const [changeReason, setChangeReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settingsProjects, setSettingsProjects] = useState([]);
  const [settingsProjectId, setSettingsProjectId] = useState('');
  const [projectSettings, setProjectSettings] = useState(null);
  const [lineDestination, setLineDestination] = useState(null);
  const [lineDestinationCandidates, setLineDestinationCandidates] = useState([]);
  const [settingsBaseline, setSettingsBaseline] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [notificationsLoading, setNotificationsLoading] = useState(true);

  const editable = ['PENDING_REVIEW', 'CHANGES_REQUESTED', 'CORRECTION_DRAFT'].includes(report?.status);
  const issueCount = useMemo(() => draft.issues.filter((issue) => issue?.title).length, [draft.issues]);
  const settingsSnapshot = useMemo(
    () => JSON.stringify({ projectSettings, lineDestination }),
    [lineDestination, projectSettings],
  );
  const settingsDirty = Boolean(settingsBaseline && settingsSnapshot !== settingsBaseline);

  const loadQueue = useCallback(async ({ preserveSelection = true } = {}) => {
    setLoading(true);
    setNotice(null);
    try {
      const items = await getDailyReportQueue(statusFilter);
      setReports(items);
      setSelectedId((current) => (
        preserveSelection && items.some((item) => item.id === current)
          ? current
          : items[0]?.id || ''
      ));
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to load the review queue.' });
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const loadNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    try {
      const items = await getDailyReportNotifications({ unreadOnly: true });
      setNotifications(items);
    } catch (error) {
      setNotice({
        tone: 'warning',
        message: error.message || 'Unable to load Daily Report notifications.',
      });
    } finally {
      setNotificationsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue({ preserveSelection: false });
    loadNotifications();
  }, [loadNotifications, loadQueue]);

  useEffect(() => {
    if (!selectedId) {
      setReport(null);
      return;
    }
    let active = true;
    setDetailLoading(true);
    getDailyReport(selectedId)
      .then((item) => {
        if (!active) return;
        setReport(item);
        setDraft(draftFromReport(item));
      })
      .catch((error) => {
        if (active) setNotice({ tone: 'danger', message: error.message || 'Unable to load this report.' });
      })
      .finally(() => {
        if (active) setDetailLoading(false);
      });
    return () => { active = false; };
  }, [selectedId]);

  const refreshCurrent = async () => {
    await Promise.all([loadQueue(), loadNotifications()]);
    if (selectedId) {
      const item = await getDailyReport(selectedId);
      setReport(item);
      setDraft(draftFromReport(item));
    }
  };

  const openNotification = async (item) => {
    setBusy(`notification-${item.id}`);
    try {
      if (item.report_id) {
        setSelectedId(item.report_id);
      }
      await markDailyReportNotificationRead(item.id);
      setNotifications((current) => current.filter((notification) => notification.id !== item.id));
      requestSidebarBadgeRefresh();
    } catch (error) {
      setNotice({
        tone: 'danger',
        message: error.message || 'Unable to update this notification.',
      });
    } finally {
      setBusy('');
    }
  };

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));

  const save = async () => {
    setBusy('save');
    setNotice(null);
    try {
      const updated = await updateDailyReportDraft(report.id, {
        ...draft,
        progress_percent: draft.progress_percent === '' ? null : Number(draft.progress_percent),
      });
      setReport((current) => ({ ...current, ...updated }));
      setNotice({ tone: 'success', message: 'Customer-facing draft saved.' });
      await loadQueue();
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to save the draft.' });
    } finally {
      setBusy('');
    }
  };

  const requestChanges = async () => {
    if (changeReason.trim().length < 3) {
      setNotice({ tone: 'danger', message: 'Add a clear change-request reason.' });
      return;
    }
    setBusy('changes');
    setNotice(null);
    try {
      const updated = await requestDailyReportChanges(report.id, {
        reason: changeReason.trim(),
        submission_ids: report.source_submission_ids || [],
      });
      setReport((current) => ({ ...current, ...updated }));
      setChangeReason('');
      setNotice({ tone: 'success', message: 'Change request sent to the source subcontractor(s).' });
      await loadQueue();
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to request changes.' });
    } finally {
      setBusy('');
    }
  };

  const publish = async () => {
    setBusy('publish');
    setNotice(null);
    try {
      await updateDailyReportDraft(report.id, {
        ...draft,
        progress_percent: draft.progress_percent === '' ? null : Number(draft.progress_percent),
      });
      const updated = await publishDailyReport(report.id);
      setReport(updated);
      setDraft(draftFromReport(updated));
      setNotice({
        tone: updated.delivery_status === 'SENT' ? 'success' : 'warning',
        message: updated.delivery_status === 'SENT'
          ? 'Report published and the LINE summary was sent.'
          : 'Report published. LINE delivery is not configured or needs attention.',
      });
      await loadQueue();
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to publish the report.' });
    } finally {
      setBusy('');
    }
  };

  const beginCorrection = async () => {
    setBusy('correction');
    try {
      const updated = await startDailyReportCorrection(report.id);
      setReport((current) => ({ ...current, ...updated }));
      setNotice({ tone: 'success', message: 'Correction draft opened. The published version remains preserved.' });
      await loadQueue();
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to start a correction.' });
    } finally {
      setBusy('');
    }
  };

  const retryDelivery = async () => {
    setBusy('delivery');
    try {
      const updated = await retryDailyReportDelivery(report.id);
      setReport(updated);
      setNotice({
        tone: updated.delivery_status === 'SENT' ? 'success' : 'warning',
        message: updated.delivery_status === 'SENT'
          ? 'LINE delivery completed.'
          : 'LINE delivery still needs configuration or attention.',
      });
      await loadQueue();
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to retry LINE delivery.' });
    } finally {
      setBusy('');
    }
  };

  const loadProjectSettings = async (projectId) => {
    if (!projectId) return;
    setBusy('settings-load');
    try {
      const [settings, destination, candidates] = await Promise.all([
        getDailyReportProjectSettings(projectId),
        getDailyReportLineDestination(projectId),
        getDailyReportLineDestinationCandidates(),
      ]);
      setProjectSettings(settings);
      setLineDestination(destination);
      setLineDestinationCandidates(candidates);
      setSettingsBaseline(JSON.stringify({ projectSettings: settings, lineDestination: destination }));
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to load project settings.' });
    } finally {
      setBusy('');
    }
  };

  const openProjectSettings = async () => {
    setShowSettings(true);
    setBusy('settings-load');
    try {
      const projects = await getDailyReportProjects();
      setSettingsProjects(projects);
      const nextProjectId = settingsProjectId || projects[0]?.id || '';
      setSettingsProjectId(nextProjectId);
      if (nextProjectId) {
        const [settings, destination, candidates] = await Promise.all([
          getDailyReportProjectSettings(nextProjectId),
          getDailyReportLineDestination(nextProjectId),
          getDailyReportLineDestinationCandidates(),
        ]);
        setProjectSettings(settings);
        setLineDestination(destination);
        setLineDestinationCandidates(candidates);
        setSettingsBaseline(JSON.stringify({ projectSettings: settings, lineDestination: destination }));
      }
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to load project settings.' });
    } finally {
      setBusy('');
    }
  };

  const saveProjectSettings = async () => {
    setBusy('settings-save');
    try {
      const [updated, updatedDestination] = await Promise.all([
        updateDailyReportProjectSettings(settingsProjectId, {
          reporting_company_name: projectSettings.reporting_company_name,
          enabled: projectSettings.enabled,
          timezone: projectSettings.timezone,
          working_days: projectSettings.working_days,
          cycle_creation_time: projectSettings.cycle_creation_time,
          first_reminder_time: projectSettings.first_reminder_time,
          submission_due_time: projectSettings.submission_due_time,
          overdue_grace_minutes: projectSettings.overdue_grace_minutes,
          draft_time: projectSettings.draft_time,
          review_target_time: projectSettings.review_target_time,
          reminder_minutes_before: projectSettings.reminder_minutes_before,
        }),
        updateDailyReportLineDestination(settingsProjectId, {
          line_target_id: lineDestination?.line_target_id || null,
          is_active: lineDestination?.status === 'ACTIVE',
        }),
      ]);
      setProjectSettings(updated);
      setLineDestination(updatedDestination);
      setSettingsBaseline(JSON.stringify({
        projectSettings: updated,
        lineDestination: updatedDestination,
      }));
      setNotice({ tone: 'success', message: 'Daily Report project settings saved.' });
      setShowSettings(false);
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to save project settings.' });
    } finally {
      setBusy('');
    }
  };

  const closeProjectSettings = () => {
    if (settingsDirty && !window.confirm('Discard unsaved project report setting changes?')) return;
    setShowSettings(false);
  };

  const changeSettingsProject = (projectId) => {
    if (settingsDirty && !window.confirm('Discard changes and open another project?')) return;
    setSettingsProjectId(projectId);
    loadProjectSettings(projectId);
  };

  return (
    <div className="dr-workspace dr-review">
      <section className="dr-hero">
        <div>
          <span className="dr-eyebrow">ADMIN / OWNER REVIEW</span>
          <h2>Daily report control room</h2>
          <p>Verify source evidence, edit the customer draft, then publish deliberately.</p>
        </div>
        <div className="dr-hero-actions">
          {owner ? (
            <button type="button" className="dr-button secondary" onClick={openProjectSettings}>
              <Settings2 /> Deadline &amp; LINE
            </button>
          ) : null}
          <button type="button" className="dr-button secondary" onClick={refreshCurrent} disabled={loading}>
            <RefreshCw className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </section>

      <DailyReportNotice tone={notice?.tone}>{notice?.message}</DailyReportNotice>

      <section className="dr-card dr-staff-alerts" aria-labelledby="daily-report-alerts-title">
        <header>
          <div className="dr-staff-alerts-title">
            <BellRing />
            <div>
              <span className="dr-eyebrow">ADMIN / OWNER ALERTS</span>
              <h3 id="daily-report-alerts-title">รายการที่ต้องตรวจสอบ</h3>
            </div>
          </div>
          <span className="dr-alert-count">{notifications.length} รายการใหม่</span>
        </header>
        {notificationsLoading ? (
          <div className="dr-loading compact">
            <LoaderCircle className="spin" /> กำลังโหลดการแจ้งเตือน…
          </div>
        ) : null}
        {!notificationsLoading && notifications.length === 0 ? (
          <div className="dr-staff-alerts-empty">
            <CheckCircle2 />
            <span>ยังไม่มีรายการใหม่ที่ต้องดำเนินการ</span>
          </div>
        ) : null}
        {!notificationsLoading && notifications.length > 0 ? (
          <div className="dr-staff-alert-list">
            {notifications.map((item) => (
              <article key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.message}</p>
                  <span><CalendarDays /> {formatReportDate(item.report_date)}</span>
                </div>
                <button
                  type="button"
                  className="dr-button secondary"
                  onClick={() => openNotification(item)}
                  disabled={busy === `notification-${item.id}`}
                >
                  {busy === `notification-${item.id}` ? (
                    <LoaderCircle className="spin" />
                  ) : (
                    <CheckCircle2 />
                  )}
                  {item.report_id ? 'เปิดและรับทราบ' : 'รับทราบ'}
                </button>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      {showSettings ? (
        <DailyReportSettingsDialog
          projects={settingsProjects}
          projectId={settingsProjectId}
          settings={projectSettings}
          destination={lineDestination}
          candidates={lineDestinationCandidates}
          busy={busy}
          dirty={settingsDirty}
          onProjectChange={changeSettingsProject}
          onSettingsChange={(updates) => setProjectSettings((current) => ({ ...current, ...updates }))}
          onDestinationChange={(updates) => setLineDestination((current) => ({ ...current, ...updates }))}
          onClose={closeProjectSettings}
          onSave={saveProjectSettings}
        />
      ) : null}

      <div className="dr-review-layout">
        <aside className="dr-card dr-queue">
          <div className="dr-queue-head">
            <div><span className="dr-eyebrow">QUEUE</span><strong>{reports.length} reports</strong></div>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">All statuses</option>
              <option value="PENDING_REVIEW">Pending review</option>
              <option value="CHANGES_REQUESTED">Changes requested</option>
              <option value="PUBLISHED">Published</option>
            </select>
          </div>
          {loading ? <div className="dr-loading compact"><LoaderCircle className="spin" /> Loading…</div> : null}
          {!loading && reports.length === 0 ? (
            <div className="dr-empty-state">
              <FileCheck2 />
              <strong>No reports in this queue</strong>
              <span>Admins see only projects with an active membership. Owners see all projects.</span>
            </div>
          ) : null}
          <div className="dr-queue-list">
            {reports.map((item) => (
              <button
                type="button"
                key={item.id}
                className={selectedId === item.id ? 'active' : ''}
                onClick={() => setSelectedId(item.id)}
              >
                <div className="dr-queue-project">
                  <strong>{item.project_name || item.project_id}</strong>
                  <span><CalendarDays /> {formatReportDate(item.report_date)}</span>
                </div>
                <DailyReportStatusBadge status={item.status} />
                <ChevronRight className="dr-queue-arrow" />
              </button>
            ))}
          </div>
        </aside>

        <main className="dr-review-detail">
          {detailLoading ? <div className="dr-card dr-loading"><LoaderCircle className="spin" /> Loading report…</div> : null}
          {!detailLoading && !report ? (
            <div className="dr-card dr-empty-state large">
              <FileCheck2 />
              <strong>Select a report to begin review</strong>
              <span>Source submissions and private evidence will appear here.</span>
            </div>
          ) : null}

          {!detailLoading && report ? (
            <>
              <section className="dr-card dr-report-heading">
                <div>
                  <div className="dr-report-meta">
                    <DailyReportStatusBadge status={report.status} />
                    <span>{formatReportDate(report.report_date)}</span>
                    {report.published_version ? <span>Version {report.published_version}</span> : null}
                  </div>
                  <h3>{report.project_name || report.project_id}</h3>
                  <p>{report.source_submission_ids?.length || 0} source submission(s) · {report.media?.length || 0} evidence file(s)</p>
                </div>
                <div className="dr-report-kpis">
                  <div><span>Progress</span><strong>{draft.progress_percent === '' ? '—' : `${draft.progress_percent}%`}</strong></div>
                  <div><span>Manpower</span><strong>{report.manpower_total || 0}</strong></div>
                  <div><span>Issues</span><strong>{issueCount}</strong></div>
                </div>
              </section>

              {report.missing_subcontractor_ids?.length > 0 ? (
                <DailyReportNotice tone="warning">
                  <strong>{report.missing_subcontractor_ids.length} expected subcontractor report(s) are still missing.</strong>{' '}
                  Review completeness before publishing this consolidated update.
                </DailyReportNotice>
              ) : null}

              <DailyReportEvidenceGallery
                report={report}
                editable={editable}
                onReportChange={(updated) => setReport(updated)}
                onNotice={setNotice}
              />

              <section className="dr-source-grid dr-source-grid-single">
                <div className="dr-card">
                  <div className="dr-inline-heading"><h3>Source submissions</h3><span>{report.submissions?.length || 0}</span></div>
                  <div className="dr-source-list">
                    {(report.submissions || []).map((submission) => (
                      <article key={submission.id}>
                        <header>
                          <strong>{submission.subcontractor_name || submission.subcontractor_id}</strong>
                          <DailyReportStatusBadge status={submission.status} />
                        </header>
                        <p>{submission.work_summary}</p>
                        <footer><Users /> {submission.manpower_total || 0} people · {submission.media_ids?.length || 0} evidence</footer>
                      </article>
                    ))}
                  </div>
                </div>
              </section>

              <section className="dr-card dr-editor">
                <div className="dr-section-heading">
                  <FileCheck2 />
                  <div><h3>Customer-facing report</h3><p>This is the content customers will see after publication.</p></div>
                </div>
                <label className="dr-field full">
                  <span>Report title</span>
                  <input value={draft.title} onChange={(event) => updateDraft('title', event.target.value)} disabled={!editable} />
                </label>
                <label className="dr-field full">
                  <span>Progress summary</span>
                  <textarea rows="7" value={draft.summary} onChange={(event) => updateDraft('summary', event.target.value)} disabled={!editable} />
                </label>
                <div className="dr-form-grid">
                  <label className="dr-field">
                    <span>Progress (%)</span>
                    <input type="number" min="0" max="100" value={draft.progress_percent} onChange={(event) => updateDraft('progress_percent', event.target.value)} disabled={!editable} />
                  </label>
                  <label className="dr-field">
                    <span>Customer note</span>
                    <input value={draft.customer_note} onChange={(event) => updateDraft('customer_note', event.target.value)} disabled={!editable} placeholder="Optional reviewer note" />
                  </label>
                </div>
                <label className="dr-field full">
                  <span>Tomorrow’s plan</span>
                  <textarea rows="4" value={draft.tomorrow_plan} onChange={(event) => updateDraft('tomorrow_plan', event.target.value)} disabled={!editable} />
                </label>
                {draft.issues.length > 0 ? (
                  <div className="dr-approved-issues">
                    <h4><AlertTriangle /> Issues included in the report</h4>
                    {draft.issues.map((issue, index) => (
                      <article key={`${issue.title}-${index}`}>
                        <input
                          value={issue.title || ''}
                          onChange={(event) => updateDraft(
                            'issues',
                            draft.issues.map((item, issueIndex) => (
                              issueIndex === index ? { ...item, title: event.target.value } : item
                            )),
                          )}
                          disabled={!editable}
                          aria-label={`Issue ${index + 1} title`}
                        />
                        <textarea
                          rows="2"
                          value={issue.detail || ''}
                          onChange={(event) => updateDraft(
                            'issues',
                            draft.issues.map((item, issueIndex) => (
                              issueIndex === index ? { ...item, detail: event.target.value } : item
                            )),
                          )}
                          disabled={!editable}
                          aria-label={`Issue ${index + 1} detail`}
                        />
                        {editable ? (
                          <button
                            type="button"
                            onClick={() => updateDraft('issues', draft.issues.filter((_, issueIndex) => issueIndex !== index))}
                          >
                            Remove from customer report
                          </button>
                        ) : null}
                      </article>
                    ))}
                  </div>
                ) : null}

                {editable ? (
                  <div className="dr-editor-actions">
                    <button type="button" className="dr-button secondary" onClick={save} disabled={Boolean(busy)}>
                      {busy === 'save' ? <LoaderCircle className="spin" /> : <Save />} Save draft
                    </button>
                  </div>
                ) : null}
              </section>

              {(report.acknowledgements?.length > 0 || report.questions?.length > 0) ? (
                <section className="dr-card dr-customer-feedback">
                  <div className="dr-inline-heading">
                    <h3>Customer activity</h3>
                    <span>{report.acknowledgements?.length || 0} acknowledgement(s) · {report.questions?.length || 0} question(s)</span>
                  </div>
                  <div>
                    {(report.questions || []).map((item) => (
                      <article key={item.id}>
                        <MessageSquareWarning />
                        <span><strong>Customer question</strong>{item.question}</span>
                      </article>
                    ))}
                    {(report.acknowledgements || []).map((item) => (
                      <article key={item.id}>
                        <CheckCircle2 />
                        <span><strong>Report acknowledged</strong>{item.note || 'Customer confirmed receipt.'}</span>
                      </article>
                    ))}
                  </div>
                </section>
              ) : null}

              {editable && report.status !== 'CORRECTION_DRAFT' ? (
                <section className="dr-card dr-decision-panel">
                  <div className="dr-change-request">
                    <MessageSquareWarning />
                    <div>
                      <strong>Need source changes?</strong>
                      <p>The reason is shown to every selected subcontractor submission.</p>
                      <textarea rows="3" value={changeReason} onChange={(event) => setChangeReason(event.target.value)} placeholder="Explain exactly what needs to be corrected…" />
                      <button type="button" className="dr-button danger" onClick={requestChanges} disabled={Boolean(busy)}>
                        {busy === 'changes' ? <LoaderCircle className="spin" /> : <MessageSquareWarning />} Request changes
                      </button>
                    </div>
                  </div>
                  <div className="dr-publish-decision">
                    <CheckCircle2 />
                    <div>
                      <strong>Ready for the customer?</strong>
                      <p>Publication locks this version, records an audit event, and sends the approved LINE summary.</p>
                      <button type="button" className="dr-button primary" onClick={publish} disabled={Boolean(busy)}>
                        {busy === 'publish' ? <LoaderCircle className="spin" /> : <Send />} Publish report
                      </button>
                    </div>
                  </div>
                </section>
              ) : null}

              {report.status === 'CORRECTION_DRAFT' ? (
                <section className="dr-card dr-correction-banner">
                  <div><RefreshCw /><span><strong>Correction draft</strong> The previous published version remains in the audit history.</span></div>
                  <button type="button" className="dr-button primary" onClick={publish} disabled={Boolean(busy)}>
                    {busy === 'publish' ? <LoaderCircle className="spin" /> : <Send />} Publish corrected version
                  </button>
                </section>
              ) : null}

              <CustomerReportShareCard
                projectId={report.project_id}
                reportId={report.id}
                refreshKey={`${report.published_version || 0}-${report.delivery_status || ''}`}
                onNotice={setNotice}
              />

              {report.status === 'PUBLISHED' ? (
                <section className="dr-card dr-published-banner">
                  <div>
                    <CheckCircle2 />
                    <span>
                      <strong>Published version {report.published_version}</strong>
                      Delivery: {report.delivery_status || 'PENDING'}
                    </span>
                  </div>
                  <button type="button" className="dr-button secondary" onClick={beginCorrection} disabled={Boolean(busy)}>
                    {busy === 'correction' ? <LoaderCircle className="spin" /> : <RefreshCw />} Start correction
                  </button>
                  {report.delivery_status !== 'SENT' ? (
                    <button type="button" className="dr-button secondary" onClick={retryDelivery} disabled={Boolean(busy)}>
                      {busy === 'delivery' ? <LoaderCircle className="spin" /> : <Send />} Retry LINE
                    </button>
                  ) : null}
                </section>
              ) : null}
            </>
          ) : null}
        </main>
      </div>
    </div>
  );
}
