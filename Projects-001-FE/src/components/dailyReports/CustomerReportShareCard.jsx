import React, { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Link2,
  Link2Off,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';

import {
  getDailyReportShareLink,
  updateDailyReportShareLink,
} from '../../api';

const COPY_FEEDBACK_DURATION_MS = 2400;

function reportScopedLink(linkUrl, reportId) {
  if (!linkUrl || !reportId) return linkUrl || '';
  const [base, fragment = ''] = linkUrl.split('#', 2);
  const params = new URLSearchParams(fragment);
  params.set('report', reportId);
  return `${base}#${params.toString()}`;
}

export default function CustomerReportShareCard({
  projectId,
  reportId,
  refreshKey = '',
  onNotice,
}) {
  const [shareLink, setShareLink] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [copyState, setCopyState] = useState('idle');
  const currentLink = useMemo(
    () => reportScopedLink(shareLink?.link_url, reportId),
    [reportId, shareLink?.link_url],
  );

  useEffect(() => {
    if (!projectId) return undefined;
    let active = true;
    setCopyState('idle');
    setLoading(true);
    getDailyReportShareLink(projectId)
      .then((item) => {
        if (active) setShareLink(item);
      })
      .catch((error) => {
        if (active) onNotice?.({
          tone: 'warning',
          message: error.message || 'Unable to load the customer share link.',
        });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [onNotice, projectId, refreshKey]);

  useEffect(() => {
    if (copyState === 'idle') return undefined;
    const resetTimer = window.setTimeout(
      () => setCopyState('idle'),
      COPY_FEEDBACK_DURATION_MS,
    );
    return () => window.clearTimeout(resetTimer);
  }, [copyState]);

  const updateLink = async ({ enabled, rotate = false }) => {
    setCopyState('idle');
    setBusy(rotate ? 'rotate' : enabled ? 'enable' : 'disable');
    try {
      const updated = await updateDailyReportShareLink(projectId, { enabled, rotate });
      setShareLink(updated);
      onNotice?.({
        tone: enabled ? 'success' : 'warning',
        message: enabled
          ? rotate
            ? 'Customer report link rotated. The previous link no longer works.'
            : 'Customer report link enabled.'
          : 'Customer report link disabled. Existing copies no longer work.',
      });
    } catch (error) {
      onNotice?.({
        tone: 'danger',
        message: error.message || 'Unable to update the customer share link.',
      });
    } finally {
      setBusy('');
    }
  };

  const copyLink = async () => {
    setCopyState('idle');
    setBusy('copy');
    try {
      await navigator.clipboard.writeText(currentLink);
      setCopyState('copied');
      onNotice?.({ tone: 'success', message: 'Customer report link copied.' });
    } catch {
      setCopyState('error');
      onNotice?.({ tone: 'danger', message: 'Unable to copy the link. Select and copy it manually.' });
    } finally {
      setBusy('');
    }
  };

  const copyButtonLabel = busy === 'copy'
    ? 'Copying…'
    : copyState === 'copied'
      ? 'Copied!'
      : copyState === 'error'
        ? 'Copy failed'
        : 'Copy link';

  return (
    <section className="dr-card dr-share-card" aria-labelledby="customer-share-title">
      <header>
        <div className="dr-share-card-icon"><ShieldCheck /></div>
        <div>
          <span className="dr-eyebrow">LOGIN-FREE CUSTOMER ACCESS</span>
          <h3 id="customer-share-title">Customer report link</h3>
          <p>Anyone with this link can view this project’s published reports.</p>
        </div>
        {loading ? <LoaderCircle className="spin" /> : (
          <span className={`dr-share-status ${shareLink?.enabled ? 'active' : 'inactive'}`}>
            {shareLink?.enabled ? 'Active' : 'Disabled'}
          </span>
        )}
      </header>

      {!loading && shareLink?.enabled ? (
        <div className="dr-share-link-row">
          <label>
            <span>Report-specific link</span>
            <input value={currentLink} readOnly aria-label="Customer report share link" />
          </label>
          <button
            type="button"
            className={`dr-button ${copyState === 'error' ? 'danger' : 'primary'} dr-share-copy-button${copyState === 'copied' ? ' is-copied' : ''}`}
            onClick={copyLink}
            disabled={!currentLink || Boolean(busy)}
            aria-busy={busy === 'copy'}
          >
            {busy === 'copy'
              ? <LoaderCircle className="spin" aria-hidden="true" />
              : copyState === 'copied'
                ? <Check aria-hidden="true" />
                : <Copy aria-hidden="true" />}
            <span aria-live="polite" aria-atomic="true">{copyButtonLabel}</span>
          </button>
        </div>
      ) : null}

      {!loading && shareLink?.enabled && !shareLink?.rollout_enabled ? (
        <div className="dr-share-rollout-note">
          The link is prepared but public access remains off until
          <code>CUSTOMER_REPORT_PUBLIC_SHARE_ENABLED=true</code> is deployed.
        </div>
      ) : null}

      {!loading ? (
        <footer>
          <span>
            {shareLink?.enabled
              ? 'Rotate immediately if the link is shared outside the intended LINE group.'
              : 'Enable access before copying or sending a customer link.'}
          </span>
          <div>
            {shareLink?.enabled ? (
              <>
                <button
                  type="button"
                  className="dr-button secondary"
                  onClick={() => {
                    if (window.confirm('Rotate this link? Every previous copy will stop working.')) {
                      updateLink({ enabled: true, rotate: true });
                    }
                  }}
                  disabled={Boolean(busy)}
                >
                  {busy === 'rotate' ? <LoaderCircle className="spin" /> : <RefreshCw />} Rotate
                </button>
                <button
                  type="button"
                  className="dr-button danger"
                  onClick={() => {
                    if (window.confirm('Disable this customer link now?')) {
                      updateLink({ enabled: false });
                    }
                  }}
                  disabled={Boolean(busy)}
                >
                  {busy === 'disable' ? <LoaderCircle className="spin" /> : <Link2Off />} Disable
                </button>
              </>
            ) : (
              <button
                type="button"
                className="dr-button primary"
                onClick={() => updateLink({ enabled: true })}
                disabled={Boolean(busy)}
              >
                {busy === 'enable' ? <LoaderCircle className="spin" /> : <Link2 />} Enable secure link
              </button>
            )}
          </div>
        </footer>
      ) : null}
    </section>
  );
}
