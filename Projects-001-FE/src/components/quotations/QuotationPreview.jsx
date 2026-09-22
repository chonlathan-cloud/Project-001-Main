import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Copy, Download, FileWarning, RefreshCw } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import {
  exportNativeBoqQuotation,
  getNativeBoqExportDownload,
  getNativeBoqMediaSignedUrl,
  getNativeBoqPreview,
} from '../../api';
import { BOQ_V2_ENABLED } from '../../config/features';
import Loading from '../Loading';
import '../boq/boqWorkspace.css';
import QuotationDocumentPreview from './QuotationDocumentPreview';
import './quotation.css';

function errorMessage(error) {
  return error?.payload?.detail?.message || error?.message || 'Unable to load this quotation snapshot.';
}

export default function QuotationPreview() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const revisionId = searchParams.get('revision') || '';
  const snapshotId = searchParams.get('snapshot') || '';
  const [preview, setPreview] = useState(null);
  const [mediaUrls, setMediaUrls] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const backPath = useMemo(
    () => `/project/detail/${projectId}/boq${revisionId ? `?revision=${revisionId}` : ''}`,
    [projectId, revisionId],
  );

  const load = useCallback(async () => {
    if (!revisionId || !snapshotId) {
      setError(new Error('Revision and snapshot identity are required.'));
      return;
    }
    setError(null);
    try {
      const loaded = await getNativeBoqPreview(revisionId, snapshotId);
      setPreview(loaded);
      const media = loaded.document?.composition?.media_assets || [];
      const entries = await Promise.all(media.map(async (asset) => {
        try {
          const access = await getNativeBoqMediaSignedUrl(revisionId, asset.id);
          return [String(asset.id), access.preview_url];
        } catch {
          return [String(asset.id), null];
        }
      }));
      setMediaUrls(Object.fromEntries(entries));
    } catch (requestError) {
      setError(requestError);
    }
  }, [revisionId, snapshotId]);

  useEffect(() => { load(); }, [load]);

  const exportSnapshot = async (fileFormat) => {
    setBusy(true);
    setError(null);
    try {
      const artifact = await exportNativeBoqQuotation(revisionId, {
        snapshot_id: snapshotId,
        audience: 'CUSTOMER',
        file_format: fileFormat,
      });
      const download = await getNativeBoqExportDownload(revisionId, artifact.artifact_id);
      window.location.assign(download.download_url);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  };

  if (!BOQ_V2_ENABLED) return <section className="boq-empty-state"><h2>Native quotation preview is disabled</h2></section>;
  if (!preview && !error) return <Loading />;
  if (error && !preview) {
    return <section className="boq-empty-state boq-error-state" role="alert"><FileWarning size={30} /><h2>Quotation snapshot unavailable</h2><p>{errorMessage(error)}</p><div className="quotation-actions"><Link className="boq-button boq-button-secondary" to={backPath}><ArrowLeft size={16} /> Back</Link><button type="button" className="boq-button boq-button-primary" onClick={load}><RefreshCw size={16} /> Retry</button></div></section>;
  }

  const payload = preview.document;
  return (
    <main className="quotation-preview-page">
      <header className="quotation-preview-toolbar">
        <div><Link className="boq-back-link" to={backPath} aria-label="Back to quotation workspace"><ArrowLeft size={19} /></Link><div><span className="boq-eyebrow">ตัวอย่างฉบับตรึง / EXACT SNAPSHOT</span><h1>{payload.document?.number} · R{payload.revision?.number}</h1><p>Snapshot {preview.snapshot.snapshot_id} · {preview.snapshot.payload_sha256.slice(0, 12)}</p></div></div>
        <div className="quotation-actions"><button type="button" className="boq-button boq-button-secondary" onClick={() => navigator.clipboard.writeText(window.location.href)}><Copy size={16} /> Copy deep link</button><button type="button" className="boq-button boq-button-secondary" onClick={() => exportSnapshot('XLSX')} disabled={busy}><Download size={16} /> Excel</button><button type="button" className="boq-button boq-button-primary" onClick={() => exportSnapshot('PDF')} disabled={busy}><Download size={16} /> {busy ? 'Preparing…' : 'PDF'}</button></div>
      </header>
      {error ? <div className="boq-notice boq-notice-danger" role="alert">{errorMessage(error)}</div> : null}
      <QuotationDocumentPreview document={payload} mediaUrls={mediaUrls} />
    </main>
  );
}
