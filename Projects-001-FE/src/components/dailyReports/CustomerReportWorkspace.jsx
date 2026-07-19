import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  HardHat,
  LoaderCircle,
  LogOut,
  MessageCircleQuestion,
  Send,
} from 'lucide-react';

import {
  acknowledgeCustomerDailyReport,
  askCustomerDailyReportQuestion,
  getCustomerDailyReport,
  getCustomerDailyReports,
  getDailyReportMediaUrl,
} from '../../api';
import { clearAuthSession, getStoredAuthUser } from '../../auth';
import { logoutLineClient } from '../../liffClient';
import logoImage from '../../assets/Logo.png';
import {
  DailyReportNotice,
  DailyReportStatusBadge,
} from './dailyReportUi';
import { formatReportDate } from './dailyReportUtils';

export default function CustomerReportWorkspace() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const authUser = useMemo(() => getStoredAuthUser(), []);
  const didAutoSelectRef = useRef(false);
  const [reports, setReports] = useState([]);
  const [report, setReport] = useState(null);
  const [mediaUrls, setMediaUrls] = useState({});
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState(null);
  const selectedId = searchParams.get('report') || '';

  useEffect(() => {
    let active = true;
    setLoading(true);
    getCustomerDailyReports()
      .then((items) => {
        if (!active) return;
        setReports(items);
        if (!selectedId && items[0]?.id && !didAutoSelectRef.current) {
          didAutoSelectRef.current = true;
          setSearchParams({ report: items[0].id }, { replace: true });
        }
      })
      .catch((error) => {
        if (active) setNotice({ tone: 'danger', message: error.message || 'Unable to load project reports.' });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [selectedId, setSearchParams]);

  useEffect(() => {
    if (!selectedId) {
      setReport(null);
      return;
    }
    let active = true;
    setLoading(true);
    getCustomerDailyReport(selectedId)
      .then(async (item) => {
        if (!active) return;
        setReport(item);
        const photoMedia = (item.media || []).filter((media) => media.content_type?.startsWith('image/'));
        const urlEntries = await Promise.all(
          photoMedia.slice(0, 8).map(async (media) => {
            try {
              const access = await getDailyReportMediaUrl(media.id);
              return [media.id, access.url];
            } catch {
              return [media.id, ''];
            }
          }),
        );
        if (active) setMediaUrls(Object.fromEntries(urlEntries));
      })
      .catch((error) => {
        if (active) setNotice({ tone: 'danger', message: error.message || 'Unable to open this report.' });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [selectedId]);

  const acknowledge = async () => {
    setBusy('ack');
    try {
      await acknowledgeCustomerDailyReport(report.id);
      setNotice({
        tone: 'success',
        message: 'Acknowledged. This confirms receipt only; it is not contractual acceptance.',
      });
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to acknowledge this report.' });
    } finally {
      setBusy('');
    }
  };

  const askQuestion = async () => {
    if (question.trim().length < 3) {
      setNotice({ tone: 'danger', message: 'Please enter a clear question.' });
      return;
    }
    setBusy('question');
    try {
      await askCustomerDailyReportQuestion(report.id, question.trim());
      setQuestion('');
      setNotice({ tone: 'success', message: 'Your report-linked question was sent to the project team.' });
    } catch (error) {
      setNotice({ tone: 'danger', message: error.message || 'Unable to send the question.' });
    } finally {
      setBusy('');
    }
  };

  const signOut = async () => {
    clearAuthSession();
    await logoutLineClient().catch(() => null);
    navigate('/login?portal=customer', { replace: true });
  };

  return (
    <div className="dr-customer-shell">
      <header className="dr-customer-header">
        <img src={logoImage} alt="RAYADEE" />
        <div><strong>Project progress</strong><span>{authUser?.display_name || 'Customer'}</span></div>
        <button type="button" onClick={signOut} aria-label="Sign out"><LogOut /></button>
      </header>

      <main className="dr-customer-main">
        <DailyReportNotice tone={notice?.tone}>{notice?.message}</DailyReportNotice>
        {loading ? <div className="dr-card dr-loading"><LoaderCircle className="spin" /> Loading approved report…</div> : null}

        {!loading && reports.length === 0 ? (
          <section className="dr-card dr-empty-state large">
            <HardHat />
            <strong>No published reports yet</strong>
            <span>The latest Admin/Owner-approved progress report will appear here.</span>
          </section>
        ) : null}

        {!loading && report ? (
          <>
            <button type="button" className="dr-customer-back" onClick={() => setSearchParams({})}>
              <ArrowLeft /> Approved daily reports
            </button>
            <section className="dr-card dr-customer-report">
              <div className="dr-customer-title">
                <div>
                  <span className="dr-eyebrow">APPROVED DAILY PROGRESS</span>
                  <h1>{report.project_name || report.title}</h1>
                  <p><CalendarDays /> {formatReportDate(report.report_date)} · Version {report.published_version}</p>
                </div>
                <DailyReportStatusBadge status={report.status} />
              </div>

              <div className="dr-customer-kpis">
                <div><span>Progress</span><strong>{report.progress_percent == null ? '—' : `${report.progress_percent}%`}</strong></div>
                <div><span>On site</span><strong>{report.manpower_total || 0}</strong><small>people</small></div>
                <div><span>Issues</span><strong>{report.issues?.length || 0}</strong></div>
              </div>

              <article className="dr-customer-section">
                <div className="dr-customer-section-icon"><HardHat /></div>
                <div>
                  <h2>Today’s progress</h2>
                  <p className="dr-preserve-lines">{report.summary}</p>
                </div>
              </article>

              {(report.issues || []).length > 0 ? (
                <article className="dr-customer-section issues">
                  <div className="dr-customer-section-icon"><AlertTriangle /></div>
                  <div>
                    <h2>Issues to note</h2>
                    <div className="dr-customer-issues">
                      {report.issues.map((issue, index) => (
                        <div key={`${issue.title}-${index}`}>
                          <strong>{issue.title || 'Site issue'}</strong>
                          <span>{issue.detail || 'The project team is monitoring this item.'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </article>
              ) : (
                <article className="dr-customer-section positive">
                  <div className="dr-customer-section-icon"><CheckCircle2 /></div>
                  <div><h2>No issues reported</h2><p>No customer-facing blockers were included in this approved report.</p></div>
                </article>
              )}

              <article className="dr-customer-section">
                <div className="dr-customer-section-icon"><CalendarDays /></div>
                <div>
                  <h2>Tomorrow’s plan</h2>
                  <p className="dr-preserve-lines">{report.tomorrow_plan || 'The next-day plan was not stated.'}</p>
                </div>
              </article>

              {report.customer_note ? (
                <div className="dr-customer-note"><strong>Project team note</strong><span>{report.customer_note}</span></div>
              ) : null}

              {Object.values(mediaUrls).some(Boolean) ? (
                <section className="dr-customer-photos">
                  <div className="dr-inline-heading"><h2><Camera /> Site photos</h2><span>Approved report evidence</span></div>
                  <div>
                    {(report.media || []).filter((media) => mediaUrls[media.id]).map((media) => (
                      <a href={mediaUrls[media.id]} target="_blank" rel="noreferrer" key={media.id}>
                        <img src={mediaUrls[media.id]} alt={media.file_name || 'Site evidence'} />
                      </a>
                    ))}
                  </div>
                </section>
              ) : null}

              <footer className="dr-customer-actions">
                <div>
                  <Check />
                  <span><strong>Acknowledge receipt</strong>This does not approve work or change the contract.</span>
                  <button type="button" className="dr-button primary" onClick={acknowledge} disabled={Boolean(busy)}>
                    {busy === 'ack' ? <LoaderCircle className="spin" /> : <CheckCircle2 />} I have seen this report
                  </button>
                </div>
                <div>
                  <MessageCircleQuestion />
                  <span><strong>Ask the project team</strong>Your question stays linked to this report.</span>
                  <textarea rows="3" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Type a question about this update…" />
                  <button type="button" className="dr-button secondary" onClick={askQuestion} disabled={Boolean(busy)}>
                    {busy === 'question' ? <LoaderCircle className="spin" /> : <Send />} Send question
                  </button>
                </div>
              </footer>
            </section>

            {reports.length > 1 ? (
              <section className="dr-card dr-customer-history">
                <div className="dr-inline-heading"><h2>Previous reports</h2><span>{reports.length}</span></div>
                {reports.filter((item) => item.id !== report.id).slice(0, 6).map((item) => (
                  <button type="button" key={item.id} onClick={() => setSearchParams({ report: item.id })}>
                    <span><strong>{item.project_name || item.project_id}</strong>{formatReportDate(item.report_date)}</span>
                    <ChevronRight />
                  </button>
                ))}
              </section>
            ) : null}
          </>
        ) : null}

        {!loading && !report && reports.length > 0 ? (
          <section className="dr-card dr-customer-history">
            <div className="dr-inline-heading"><h2>Approved reports</h2><span>{reports.length}</span></div>
            {reports.map((item) => (
              <button type="button" key={item.id} onClick={() => setSearchParams({ report: item.id })}>
                <span><strong>{item.project_name || item.project_id}</strong>{formatReportDate(item.report_date)}</span>
                <div><DailyReportStatusBadge status={item.status} /><ChevronRight /></div>
              </button>
            ))}
          </section>
        ) : null}
      </main>
    </div>
  );
}
