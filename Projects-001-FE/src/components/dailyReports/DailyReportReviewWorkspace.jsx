import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  CalendarDays,
  Camera,
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
  X,
} from 'lucide-react';

import {
  getDailyReport,
  getDailyReportMediaUrl,
  getDailyReportLineDestination,
  getDailyReportLineDestinationCandidates,
  getDailyReportProjectSettings,
  getDailyReportProjects,
  getDailyReportQueue,
  publishDailyReport,
  requestDailyReportChanges,
  retryDailyReportDelivery,
  startDailyReportCorrection,
  updateDailyReportProjectSettings,
  updateDailyReportLineDestination,
  updateDailyReportDraft,
} from '../../api';
import { getStoredAuthUser, isOwnerUser } from '../../auth';
import {
  DailyReportNotice,
  DailyReportStatusBadge,
} from './dailyReportUi';
import { formatReportDate } from './dailyReportUtils';

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

  const editable = ['PENDING_REVIEW', 'CHANGES_REQUESTED', 'CORRECTION_DRAFT'].includes(report?.status);
  const issueCount = useMemo(() => draft.issues.filter((issue) => issue?.title).length, [draft.issues]);

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

  useEffect(() => {
    loadQueue({ preserveSelection: false });
  }, [loadQueue]);

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
    await loadQueue();
    if (selectedId) {
      const item = await getDailyReport(selectedId);
      setReport(item);
      setDraft(draftFromReport(item));
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

  const openMedia = async (mediaId) => {
    setBusy(`media-${mediaId}`);
    try {
      const access = await getDailyReportMediaUrl(mediaId);
      window.open(access.url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to open evidence.' });
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
          enabled: projectSettings.enabled,
          timezone: projectSettings.timezone,
          submission_due_time: projectSettings.submission_due_time,
          review_target_time: projectSettings.review_target_time,
          reminder_minutes_before: projectSettings.reminder_minutes_before,
        }),
        updateDailyReportLineDestination(settingsProjectId, {
          line_target_id: lineDestination?.line_target_id || null,
          target_type: lineDestination?.target_type || 'group',
          is_active: lineDestination?.status === 'ACTIVE',
        }),
      ]);
      setProjectSettings(updated);
      setLineDestination(updatedDestination);
      setNotice({ tone: 'success', message: 'Daily Report deadline settings saved.' });
      setShowSettings(false);
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to save project settings.' });
    } finally {
      setBusy('');
    }
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
              <Settings2 /> Deadlines
            </button>
          ) : null}
          <button type="button" className="dr-button secondary" onClick={refreshCurrent} disabled={loading}>
            <RefreshCw className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </section>

      <DailyReportNotice tone={notice?.tone}>{notice?.message}</DailyReportNotice>

      {showSettings ? (
        <section className="dr-card dr-settings-panel">
          <header>
            <div><span className="dr-eyebrow">OWNER CONFIGURATION</span><h3>Report deadlines and reminders</h3></div>
            <button type="button" onClick={() => setShowSettings(false)} aria-label="Close settings"><X /></button>
          </header>
          <div className="dr-form-grid">
            <label className="dr-field">
              <span>Project</span>
              <select
                value={settingsProjectId}
                onChange={(event) => {
                  setSettingsProjectId(event.target.value);
                  loadProjectSettings(event.target.value);
                }}
              >
                {settingsProjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="dr-field">
              <span>Timezone</span>
              <input
                value={projectSettings?.timezone || 'Asia/Bangkok'}
                onChange={(event) => setProjectSettings((current) => ({ ...current, timezone: event.target.value }))}
                disabled={!projectSettings}
              />
            </label>
            <label className="dr-field">
              <span>Subcontractor deadline</span>
              <input
                type="time"
                value={projectSettings?.submission_due_time || '17:00'}
                onChange={(event) => setProjectSettings((current) => ({ ...current, submission_due_time: event.target.value }))}
                disabled={!projectSettings}
              />
            </label>
            <label className="dr-field">
              <span>Review target</span>
              <input
                type="time"
                value={projectSettings?.review_target_time || '19:00'}
                onChange={(event) => setProjectSettings((current) => ({ ...current, review_target_time: event.target.value }))}
                disabled={!projectSettings}
              />
            </label>
            <label className="dr-field">
              <span>Reminder minutes before deadline</span>
              <input
                value={(projectSettings?.reminder_minutes_before || [120, 30]).join(', ')}
                onChange={(event) => setProjectSettings((current) => ({
                  ...current,
                  reminder_minutes_before: event.target.value
                    .split(',')
                    .map((item) => Number(item.trim()))
                    .filter((item) => Number.isFinite(item) && item >= 0),
                }))}
                disabled={!projectSettings}
              />
            </label>
            <label className="dr-settings-toggle">
              <input
                type="checkbox"
                checked={projectSettings?.enabled !== false}
                onChange={(event) => setProjectSettings((current) => ({ ...current, enabled: event.target.checked }))}
                disabled={!projectSettings}
              />
              <span><strong>Daily reporting enabled</strong>Create cycles and send configured reminders.</span>
            </label>
            <label className="dr-field">
              <span>Customer LINE target ID</span>
              <input
                value={lineDestination?.line_target_id || ''}
                onChange={(event) => setLineDestination((current) => ({ ...current, line_target_id: event.target.value }))}
                disabled={!lineDestination}
                placeholder="C… group ID, R… room ID, or U… user ID"
              />
            </label>
            <label className="dr-field">
              <span>Discovered LINE destination</span>
              <select
                value=""
                onChange={(event) => {
                  const candidate = lineDestinationCandidates.find(
                    (item) => item.line_target_id === event.target.value,
                  );
                  if (candidate) {
                    setLineDestination((current) => ({
                      ...current,
                      line_target_id: candidate.line_target_id,
                      target_type: candidate.target_type,
                    }));
                  }
                }}
                disabled={lineDestinationCandidates.length === 0}
              >
                <option value="">Select a group discovered by the LINE webhook</option>
                {lineDestinationCandidates.map((item) => (
                  <option key={item.line_target_id} value={item.line_target_id}>
                    {item.target_type} · {item.line_target_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="dr-field">
              <span>LINE destination type</span>
              <select
                value={lineDestination?.target_type || 'group'}
                onChange={(event) => setLineDestination((current) => ({ ...current, target_type: event.target.value }))}
                disabled={!lineDestination}
              >
                <option value="group">Project group</option>
                <option value="room">Multi-person room</option>
                <option value="user">Individual customer</option>
              </select>
            </label>
            <label className="dr-settings-toggle">
              <input
                type="checkbox"
                checked={lineDestination?.status === 'ACTIVE'}
                onChange={(event) => setLineDestination((current) => ({
                  ...current,
                  status: event.target.checked ? 'ACTIVE' : 'INACTIVE',
                }))}
                disabled={!lineDestination}
              />
              <span><strong>LINE delivery active</strong>Send the approved Flex summary to this destination.</span>
            </label>
          </div>
          <footer>
            <span>Cloud Scheduler should call the protected deadline tick endpoint at a short interval.</span>
            <button type="button" className="dr-button primary" onClick={saveProjectSettings} disabled={!projectSettings || busy === 'settings-save'}>
              {busy === 'settings-save' ? <LoaderCircle className="spin" /> : <Save />} Save settings
            </button>
          </footer>
        </section>
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

              <section className="dr-source-grid">
                <div className="dr-card">
                  <div className="dr-inline-heading"><h3>Source evidence</h3><span>Private signed access</span></div>
                  <div className="dr-media-grid">
                    {(report.media || []).map((media, index) => (
                      <button type="button" key={media.id} onClick={() => openMedia(media.id)}>
                        {busy === `media-${media.id}` ? <LoaderCircle className="spin" /> : <Camera />}
                        <span>Evidence {index + 1}</span>
                        <small>{media.media_type} · {(media.size_bytes / 1024 / 1024).toFixed(1)} MB</small>
                        <ArrowUpRight />
                      </button>
                    ))}
                  </div>
                  {(report.media || []).length === 0 ? <p className="dr-empty-copy">No evidence attached.</p> : null}
                </div>

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
