import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Eye,
  EyeOff,
  ImagePlus,
  LoaderCircle,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

import {
  getDailyReport,
  getDailyReportMediaUrl,
  removeDailyReportSupplementalMedia,
  updateDailyReportMediaVisibility,
  uploadDailyReportSupplementalMedia,
} from '../../api';
import CustomerPhotoLightbox from './CustomerPhotoLightbox';

export default function DailyReportEvidenceGallery({
  report,
  editable,
  onReportChange,
  onNotice,
}) {
  const fileInputRef = useRef(null);
  const [accessById, setAccessById] = useState({});
  const [loadingIds, setLoadingIds] = useState(new Set());
  const [busyId, setBusyId] = useState('');
  const [uploadProgress, setUploadProgress] = useState(null);
  const [activePhotoIndex, setActivePhotoIndex] = useState(null);

  const media = useMemo(
    () => (report?.media || []).filter((item) => item.status !== 'REMOVED'),
    [report?.media],
  );
  const includedCount = media.filter((item) => item.included_in_customer_report).length;

  useEffect(() => {
    let active = true;
    const imageMedia = media.filter((item) => String(item.content_type || '').startsWith('image/'));
    setLoadingIds(new Set(imageMedia.map((item) => item.id)));
    Promise.allSettled(
      imageMedia.map(async (item) => [item.id, await getDailyReportMediaUrl(item.id)]),
    ).then((results) => {
      if (!active) return;
      const nextAccess = {};
      results.forEach((result) => {
        if (result.status === 'fulfilled') {
          const [mediaId, access] = result.value;
          nextAccess[mediaId] = access;
        }
      });
      setAccessById(nextAccess);
      setLoadingIds(new Set());
    });
    return () => {
      active = false;
    };
  }, [media]);

  const photos = useMemo(
    () => media
      .filter((item) => accessById[item.id]?.url)
      .map((item) => ({
        id: item.id,
        url: accessById[item.id].url,
        thumbnailUrl: accessById[item.id].thumbnail_url || accessById[item.id].url,
        fileName: item.file_name,
        alt: `${item.source_type === 'ADMIN_SUPPLEMENTAL' ? 'Admin supplemental' : 'Subcontractor'} evidence`,
      })),
    [accessById, media],
  );

  const openPhoto = (mediaId) => {
    const index = photos.findIndex((item) => item.id === mediaId);
    if (index >= 0) setActivePhotoIndex(index);
  };

  const updateVisibility = async (item) => {
    setBusyId(`visibility-${item.id}`);
    try {
      const updated = await updateDailyReportMediaVisibility(
        report.id,
        item.id,
        !item.included_in_customer_report,
      );
      onReportChange(updated);
      onNotice({
        tone: 'success',
        message: item.included_in_customer_report
          ? 'Photo kept as internal evidence and removed from the customer report.'
          : 'Photo added back to the customer report.',
      });
    } catch (error) {
      onNotice({ tone: 'danger', message: error.message || 'Unable to update photo visibility.' });
    } finally {
      setBusyId('');
    }
  };

  const upload = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (files.length === 0) return;

    setBusyId('upload');
    setUploadProgress({ current: 1, total: files.length });
    let uploadedCount = 0;
    const failures = [];

    try {
      for (let index = 0; index < files.length; index += 1) {
        setUploadProgress({ current: index + 1, total: files.length });
        try {
          await uploadDailyReportSupplementalMedia(report.id, files[index]);
          uploadedCount += 1;
        } catch (error) {
          failures.push({
            fileName: files[index].name,
            message: error.message || 'Upload failed.',
          });
        }
      }

      if (uploadedCount > 0) {
        onReportChange(await getDailyReport(report.id));
      }

      if (failures.length === 0) {
        onNotice({
          tone: 'success',
          message: `${uploadedCount} supplemental photo${uploadedCount === 1 ? '' : 's'} added and selected for the customer report.`,
        });
      } else if (uploadedCount > 0) {
        onNotice({
          tone: 'warning',
          message: `${uploadedCount} photo${uploadedCount === 1 ? '' : 's'} uploaded. ${failures.length} failed: ${failures.map((item) => item.fileName).join(', ')}`,
        });
      } else {
        onNotice({
          tone: 'danger',
          message: failures[0]?.message || 'Unable to upload supplemental evidence.',
        });
      }
    } catch (error) {
      onNotice({
        tone: uploadedCount > 0 ? 'warning' : 'danger',
        message: uploadedCount > 0
          ? `${uploadedCount} photo${uploadedCount === 1 ? '' : 's'} uploaded, but the gallery could not be refreshed. Please refresh the page.`
          : error.message || 'Unable to upload supplemental evidence.',
      });
    } finally {
      setBusyId('');
      setUploadProgress(null);
    }
  };

  const removeSupplemental = async (item) => {
    if (!window.confirm('Remove this supplemental photo from the report? The audit record will remain.')) return;
    setBusyId(`remove-${item.id}`);
    try {
      const updated = await removeDailyReportSupplementalMedia(report.id, item.id);
      onReportChange(updated);
      onNotice({ tone: 'success', message: 'Supplemental photo removed from the working report.' });
    } catch (error) {
      onNotice({ tone: 'danger', message: error.message || 'Unable to remove supplemental evidence.' });
    } finally {
      setBusyId('');
    }
  };

  return (
    <section className="dr-card dr-evidence-gallery">
      <header>
        <div>
          <span className="dr-eyebrow">CUSTOMER EVIDENCE</span>
          <h3>Choose the photos customers will see</h3>
          <p>Original subcontractor evidence stays private and auditable even when excluded.</p>
        </div>
        <div className="dr-evidence-summary">
          <strong>{includedCount} / {media.length}</strong>
          <span>selected</span>
        </div>
      </header>

      {editable ? (
        <div className="dr-evidence-toolbar">
          <div><ShieldCheck /><span>Excluding a photo does not delete the original.</span></div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
            multiple
            onChange={upload}
            hidden
          />
          <button
            type="button"
            className="dr-button secondary"
            onClick={() => fileInputRef.current?.click()}
            disabled={Boolean(busyId)}
          >
            {busyId === 'upload' ? <LoaderCircle className="spin" /> : <ImagePlus />}
            <span aria-live="polite">
              {busyId === 'upload' && uploadProgress
                ? `Uploading ${uploadProgress.current}/${uploadProgress.total}`
                : 'Add photos'}
            </span>
          </button>
        </div>
      ) : null}

      {media.length ? (
        <div className="dr-evidence-grid">
          {media.map((item, index) => {
            const access = accessById[item.id];
            const included = Boolean(item.included_in_customer_report);
            const supplemental = item.source_type === 'ADMIN_SUPPLEMENTAL';
            return (
              <article key={item.id} className={included ? 'is-included' : 'is-excluded'}>
                <button
                  type="button"
                  className="dr-evidence-preview"
                  onClick={() => openPhoto(item.id)}
                  disabled={!access?.url}
                  aria-label={`Open evidence ${index + 1}`}
                >
                  {loadingIds.has(item.id) ? (
                    <LoaderCircle className="spin" />
                  ) : access?.url ? (
                    <img
                      src={access.thumbnail_url || access.url}
                      alt=""
                      loading="lazy"
                      onError={(event) => {
                        if (event.currentTarget.src !== access.url) event.currentTarget.src = access.url;
                      }}
                    />
                  ) : (
                    <EyeOff />
                  )}
                  {!included ? <span className="dr-evidence-excluded-badge">ไม่ส่งให้ลูกค้า</span> : null}
                </button>
                <div className="dr-evidence-meta">
                  <span>{supplemental ? 'Added by Admin/Owner' : 'Original subcontractor evidence'}</span>
                  <strong>{item.file_name || `Evidence ${index + 1}`}</strong>
                  <small>{(Number(item.size_bytes || 0) / 1024 / 1024).toFixed(1)} MB</small>
                </div>
                {editable ? (
                  <footer>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={included}
                      onClick={() => updateVisibility(item)}
                      disabled={Boolean(busyId)}
                    >
                      {busyId === `visibility-${item.id}`
                        ? <LoaderCircle className="spin" />
                        : included ? <Eye /> : <EyeOff />}
                      {included ? 'ส่งให้ลูกค้า' : 'เก็บภายใน'}
                    </button>
                    {supplemental ? (
                      <button
                        type="button"
                        className="danger"
                        onClick={() => removeSupplemental(item)}
                        disabled={Boolean(busyId)}
                        aria-label={`Remove ${item.file_name}`}
                      >
                        {busyId === `remove-${item.id}` ? <LoaderCircle className="spin" /> : <Trash2 />}
                      </button>
                    ) : null}
                  </footer>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="dr-empty-state">
          <ImagePlus />
          <strong>No evidence available</strong>
          <span>Add at least one customer-facing photo before publishing.</span>
        </div>
      )}

      {activePhotoIndex !== null && photos[activePhotoIndex] ? (
        <CustomerPhotoLightbox
          photos={photos}
          activeIndex={activePhotoIndex}
          onIndexChange={setActivePhotoIndex}
          onClose={() => setActivePhotoIndex(null)}
        />
      ) : null}
    </section>
  );
}
