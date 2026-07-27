import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
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
  ShieldCheck,
} from 'lucide-react';

import {
  acknowledgeCustomerDailyReport,
  askCustomerDailyReportQuestion,
  getCustomerDailyReport,
  getCustomerDailyReports,
  getDailyReportMediaUrl,
  getSharedCustomerDailyReport,
  getSharedCustomerDailyReports,
  getSharedDailyReportMediaUrl,
} from '../../api';
import { clearAuthSession, getStoredAuthUser } from '../../auth';
import { logoutLineClient } from '../../liffClient';
import logoImage from '../../assets/Logo.png';
import {
  DailyReportNotice,
  DailyReportStatusBadge,
} from './dailyReportUi';
import { formatReportDate } from './dailyReportUtils';
import CustomerPhotoLightbox from './CustomerPhotoLightbox';

export default function CustomerReportWorkspace({
  publicAccess = false,
  shareToken = '',
  selectedReportId = '',
  onSelectedReportChange = null,
}) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const authUser = useMemo(() => getStoredAuthUser(), []);
  const didAutoSelectRef = useRef(false);
  const photoButtonRefs = useRef(new Map());
  const [reports, setReports] = useState([]);
  const [report, setReport] = useState(null);
  const [mediaUrls, setMediaUrls] = useState({});
  const [loadedPhotoIds, setLoadedPhotoIds] = useState(() => new Set());
  const [activePhotoIndex, setActivePhotoIndex] = useState(null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState(null);
  const [accessError, setAccessError] = useState('');
  const selectedId = publicAccess ? selectedReportId : (searchParams.get('report') || '');
  const selectReport = (reportId) => {
    if (publicAccess) {
      onSelectedReportChange?.(reportId);
      return;
    }
    setSearchParams(reportId ? { report: reportId } : {});
  };
  const photos = useMemo(
    () => (report?.media || [])
      .map((media) => {
        const access = mediaUrls[media.id];
        const url = typeof access === 'string' ? access : access?.url;
        const thumbnailUrl = typeof access === 'string'
          ? access
          : (access?.thumbnail_url || access?.thumbnailUrl || url);
        return {
          id: media.id,
          url,
          thumbnailUrl,
          fileName: media.file_name || '',
          sizeBytes: media.size_bytes || 0,
          alt: media.file_name || 'รูปภาพหน้างาน',
        };
      })
      .filter((photo) => Boolean(photo.url)),
    [mediaUrls, report],
  );

  useEffect(() => {
    let active = true;
    setAccessError('');
    if (publicAccess && !shareToken) {
      setReports([]);
      setReport(null);
      setLoading(false);
      setAccessError('ลิงก์รายงานนี้ไม่สมบูรณ์ กรุณาเปิดลิงก์ล่าสุดจากกลุ่ม LINE ของโครงการ');
      return () => { active = false; };
    }
    setLoading(true);
    const request = publicAccess
      ? getSharedCustomerDailyReports(shareToken)
      : getCustomerDailyReports();
    request
      .then((items) => {
        if (!active) return;
        setReports(items);
        if (!selectedId && items[0]?.id && !didAutoSelectRef.current) {
          didAutoSelectRef.current = true;
          if (publicAccess) onSelectedReportChange?.(items[0].id);
          else setSearchParams({ report: items[0].id }, { replace: true });
        }
      })
      .catch((error) => {
        console.error('Unable to load customer project reports.', error);
        if (!active) return;
        if (publicAccess && [401, 403, 404].includes(error?.status)) {
          setAccessError('ลิงก์นี้หมดอายุหรือถูกปิดใช้งานแล้ว กรุณาเปิดลิงก์ล่าสุดจากกลุ่ม LINE ของโครงการ');
        } else {
          setNotice({ tone: 'danger', message: 'ไม่สามารถโหลดรายงานโครงการได้ กรุณาลองใหม่อีกครั้ง' });
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [onSelectedReportChange, publicAccess, selectedId, setSearchParams, shareToken]);

  useEffect(() => {
    setActivePhotoIndex(null);
    setMediaUrls({});
    setLoadedPhotoIds(new Set());
    if (!selectedId) {
      setReport(null);
      return;
    }
    let active = true;
    setLoading(true);
    const request = publicAccess
      ? getSharedCustomerDailyReport(shareToken, selectedId)
      : getCustomerDailyReport(selectedId);
    request
      .then(async (item) => {
        if (!active) return;
        setReport(item);
        const photoMedia = (item.media || []).filter((media) => media.content_type?.startsWith('image/'));
        const urlEntries = await Promise.all(
          photoMedia.slice(0, 8).map(async (media) => {
            try {
              const access = publicAccess
                ? await getSharedDailyReportMediaUrl(shareToken, media.id)
                : await getDailyReportMediaUrl(media.id);
              return [media.id, access];
            } catch {
              return [media.id, ''];
            }
          }),
        );
        if (active) setMediaUrls(Object.fromEntries(urlEntries));
      })
      .catch((error) => {
        console.error('Unable to open customer project report.', error);
        if (active) setNotice({ tone: 'danger', message: 'ไม่สามารถเปิดรายงานฉบับนี้ได้ กรุณาลองใหม่อีกครั้ง' });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [publicAccess, selectedId, shareToken]);

  useEffect(() => {
    if (activePhotoIndex !== null && activePhotoIndex >= photos.length) {
      setActivePhotoIndex(null);
    }
  }, [activePhotoIndex, photos.length]);

  const closePhotoViewer = () => {
    const photoId = photos[activePhotoIndex]?.id;
    setActivePhotoIndex(null);
    window.requestAnimationFrame(() => photoButtonRefs.current.get(photoId)?.focus());
  };

  const markPhotoLoaded = (photoId) => {
    setLoadedPhotoIds((current) => {
      if (current.has(photoId)) return current;
      const next = new Set(current);
      next.add(photoId);
      return next;
    });
  };

  const acknowledge = async () => {
    setBusy('ack');
    try {
      await acknowledgeCustomerDailyReport(report.id);
      setNotice({
        tone: 'success',
        message: 'รับทราบรายงานแล้ว การรับทราบหมายถึงได้รับข้อมูลเท่านั้น ไม่ใช่การอนุมัติงานหรือเปลี่ยนแปลงสัญญา',
      });
    } catch (error) {
      console.error('Unable to acknowledge customer project report.', error);
      setNotice({ tone: 'danger', message: 'ไม่สามารถรับทราบรายงานได้ กรุณาลองใหม่อีกครั้ง' });
    } finally {
      setBusy('');
    }
  };

  const askQuestion = async () => {
    if (question.trim().length < 3) {
      setNotice({ tone: 'danger', message: 'กรุณาพิมพ์คำถามอย่างน้อย 3 ตัวอักษร' });
      return;
    }
    setBusy('question');
    try {
      await askCustomerDailyReportQuestion(report.id, question.trim());
      setQuestion('');
      setNotice({ tone: 'success', message: 'ส่งคำถามให้ทีมงานโครงการแล้ว' });
    } catch (error) {
      console.error('Unable to send customer project report question.', error);
      setNotice({ tone: 'danger', message: 'ไม่สามารถส่งคำถามได้ กรุณาลองใหม่อีกครั้ง' });
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
    <div className="dr-customer-shell" lang="th">
      <header className="dr-customer-header">
        <img src={logoImage} alt="RAYADEE" />
        <div>
          <strong>ความคืบหน้าโครงการ</strong>
          <span>{publicAccess ? 'รายงานสำหรับลูกค้า' : (authUser?.display_name || 'ลูกค้า')}</span>
        </div>
        {publicAccess ? (
          <span className="dr-customer-access-badge"><ShieldCheck /> เปิดผ่านลิงก์โครงการ</span>
        ) : (
          <button type="button" onClick={signOut} aria-label="ออกจากระบบ" title="ออกจากระบบ"><LogOut /></button>
        )}
      </header>

      <main className="dr-customer-main">
        <DailyReportNotice tone={notice?.tone}>{notice?.message}</DailyReportNotice>
        {loading ? <div className="dr-card dr-loading"><LoaderCircle className="spin" /> กำลังโหลดรายงาน…</div> : null}

        {!loading && accessError ? (
          <section className="dr-card dr-shared-link-error" role="alert">
            <ShieldCheck />
            <strong>ไม่สามารถเปิดรายงานจากลิงก์นี้ได้</strong>
            <span>{accessError}</span>
          </section>
        ) : null}

        {!loading && !accessError && reports.length === 0 ? (
          <section className="dr-card dr-empty-state large">
            <HardHat />
            <strong>ยังไม่มีรายงานที่เผยแพร่</strong>
            <span>เมื่อผู้ดูแลตรวจสอบและเผยแพร่รายงานแล้ว รายงานจะแสดงที่หน้านี้</span>
          </section>
        ) : null}

        {!loading && report ? (
          <>
            <button type="button" className="dr-customer-back" onClick={() => selectReport('')}>
              <ArrowLeft /> รายงานประจำวันทั้งหมด
            </button>
            <section className="dr-card dr-customer-report">
              <div className="dr-customer-title">
                <div>
                  <span className="dr-eyebrow">รายงานความคืบหน้าที่อนุมัติแล้ว</span>
                  <h1>{report.project_name || report.title || 'รายงานโครงการ'}</h1>
                  <p><CalendarDays /> {formatReportDate(report.report_date, 'th-TH')} · ฉบับที่ {report.published_version || 1}</p>
                </div>
                <DailyReportStatusBadge status={report.status} locale="th" />
              </div>

              <div className="dr-customer-kpis">
                <div><span>ความคืบหน้า</span><strong>{report.progress_percent == null ? '—' : `${report.progress_percent}%`}</strong></div>
                <div><span>ทีมงานหน้างาน</span><strong>{report.manpower_total || 0}</strong><small>คน</small></div>
                <div><span>เรื่องที่ต้องติดตาม</span><strong>{report.issues?.length || 0}</strong></div>
              </div>

              {report.reporting_company_name ? (
                <div className="dr-customer-company">
                  <Building2 />
                  <span>
                    <small>บริษัทผู้จัดทำรายงาน</small>
                    <strong>{report.reporting_company_name}</strong>
                  </span>
                </div>
              ) : null}

              <article className="dr-customer-section">
                <div className="dr-customer-section-icon"><HardHat /></div>
                <div>
                  <h2>งานที่ทำวันนี้</h2>
                  <p className="dr-preserve-lines">{report.summary || 'ยังไม่มีรายละเอียดงานวันนี้'}</p>
                </div>
              </article>

              {(report.issues || []).length > 0 ? (
                <article className="dr-customer-section issues">
                  <div className="dr-customer-section-icon"><AlertTriangle /></div>
                  <div>
                    <h2>เรื่องที่ต้องติดตาม</h2>
                    <div className="dr-customer-issues">
                      {report.issues.map((issue, index) => (
                        <div key={`${issue.title}-${index}`}>
                          <strong>{issue.title || 'ประเด็นหน้างาน'}</strong>
                          <span>{issue.detail || 'ทีมงานโครงการกำลังติดตามเรื่องนี้'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </article>
              ) : (
                <article className="dr-customer-section positive">
                  <div className="dr-customer-section-icon"><CheckCircle2 /></div>
                  <div><h2>ไม่พบปัญหาที่ต้องแจ้ง</h2><p>รายงานฉบับนี้ไม่มีปัญหาที่กระทบลูกค้า</p></div>
                </article>
              )}

              <article className="dr-customer-section">
                <div className="dr-customer-section-icon"><CalendarDays /></div>
                <div>
                  <h2>แผนงานวันถัดไป</h2>
                  <p className="dr-preserve-lines">{report.tomorrow_plan || 'ยังไม่ได้ระบุแผนงานวันถัดไป'}</p>
                </div>
              </article>

              {report.customer_note ? (
                <div className="dr-customer-note"><strong>หมายเหตุจากทีมงานโครงการ</strong><span>{report.customer_note}</span></div>
              ) : null}

              {photos.length > 0 ? (
                <section className="dr-customer-photos">
                  <div className="dr-inline-heading"><h2><Camera /> รูปภาพหน้างาน</h2><span>รูปประกอบรายงานที่อนุมัติแล้ว</span></div>
                  <div>
                    {photos.map((photo, index) => (
                      <button
                        type="button"
                        key={photo.id}
                        className={loadedPhotoIds.has(photo.id) ? 'is-loaded' : 'is-loading'}
                        ref={(node) => {
                          if (node) photoButtonRefs.current.set(photo.id, node);
                          else photoButtonRefs.current.delete(photo.id);
                        }}
                        onClick={() => setActivePhotoIndex(index)}
                        aria-label={`ดูรูปที่ ${index + 1} จาก ${photos.length}: ${photo.alt}`}
                        aria-haspopup="dialog"
                        aria-busy={!loadedPhotoIds.has(photo.id)}
                      >
                        <img
                          src={photo.thumbnailUrl || photo.url}
                          alt={photo.alt}
                          loading="lazy"
                          decoding="async"
                          fetchPriority="low"
                          onLoad={() => markPhotoLoaded(photo.id)}
                          onError={(event) => {
                            const image = event.currentTarget;
                            if (image.dataset.fallback !== 'original' && photo.thumbnailUrl !== photo.url) {
                              image.dataset.fallback = 'original';
                              image.src = photo.url;
                              return;
                            }
                            markPhotoLoaded(photo.id);
                          }}
                        />
                        <span aria-hidden="true">{index + 1}</span>
                      </button>
                    ))}
                  </div>
                </section>
              ) : null}

              {publicAccess ? (
                <footer className="dr-customer-line-help">
                  <MessageCircleQuestion />
                  <span>
                    <strong>มีคำถามเกี่ยวกับรายงาน?</strong>
                    กลับไปสอบถามทีมงานในกลุ่ม LINE ของโครงการ เพื่อให้ทุกคนเห็นบริบทเดียวกัน
                  </span>
                </footer>
              ) : (
                <footer className="dr-customer-actions">
                  <div>
                    <Check />
                    <span><strong>รับทราบรายงาน</strong>เป็นการยืนยันว่าได้รับข้อมูลแล้ว ไม่ใช่การอนุมัติงานหรือเปลี่ยนแปลงสัญญา</span>
                    <button type="button" className="dr-button primary" onClick={acknowledge} disabled={Boolean(busy)}>
                      {busy === 'ack' ? <LoaderCircle className="spin" /> : <CheckCircle2 />} ยืนยันว่าได้รับรายงานแล้ว
                    </button>
                  </div>
                  <div>
                    <MessageCircleQuestion />
                    <span><strong>สอบถามทีมงานโครงการ</strong>ทีมงานจะเห็นว่าคำถามนี้เกี่ยวกับรายงานฉบับนี้</span>
                    <textarea
                      rows="3"
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      placeholder="พิมพ์คำถามเกี่ยวกับรายงานนี้…"
                      aria-label="คำถามถึงทีมงานโครงการ"
                    />
                    <button type="button" className="dr-button secondary" onClick={askQuestion} disabled={Boolean(busy)}>
                      {busy === 'question' ? <LoaderCircle className="spin" /> : <Send />} ส่งคำถาม
                    </button>
                  </div>
                </footer>
              )}
            </section>

            {reports.length > 1 ? (
              <section className="dr-card dr-customer-history">
                <div className="dr-inline-heading"><h2>รายงานก่อนหน้า</h2><span>{reports.length} ฉบับ</span></div>
                {reports.filter((item) => item.id !== report.id).slice(0, 6).map((item) => (
                  <button type="button" key={item.id} onClick={() => selectReport(item.id)}>
                    <span><strong>{item.project_name || item.project_id}</strong>{formatReportDate(item.report_date, 'th-TH')}</span>
                    <ChevronRight />
                  </button>
                ))}
              </section>
            ) : null}
          </>
        ) : null}

        {!loading && !report && reports.length > 0 ? (
          <section className="dr-card dr-customer-history">
            <div className="dr-inline-heading"><h2>รายงานที่อนุมัติแล้ว</h2><span>{reports.length} ฉบับ</span></div>
            {reports.map((item) => (
              <button type="button" key={item.id} onClick={() => selectReport(item.id)}>
                <span><strong>{item.project_name || item.project_id}</strong>{formatReportDate(item.report_date, 'th-TH')}</span>
                <div><DailyReportStatusBadge status={item.status} locale="th" /><ChevronRight /></div>
              </button>
            ))}
          </section>
        ) : null}
      </main>

      {activePhotoIndex !== null ? (
        <CustomerPhotoLightbox
          photos={photos}
          activeIndex={activePhotoIndex}
          onIndexChange={setActivePhotoIndex}
          onClose={closePhotoViewer}
        />
      ) : null}
    </div>
  );
}
