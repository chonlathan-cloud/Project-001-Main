import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Copy, Download, FileWarning, RefreshCw } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import {
  exportNativeBoqQuotation,
  getNativeBoqExportDownload,
  getNativeBoqPreview,
} from '../../api';
import { BOQ_V2_ENABLED } from '../../config/features';
import Loading from '../Loading';
import '../boq/boqWorkspace.css';
import './quotation.css';

function money(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat('th-TH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(number) ? number : 0);
}

function errorMessage(error) {
  return error?.payload?.detail?.message || error?.message || 'Unable to load this quotation snapshot.';
}

export default function QuotationPreview() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const revisionId = searchParams.get('revision') || '';
  const snapshotId = searchParams.get('snapshot') || '';
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const backPath = useMemo(
    () => `/project/detail/${projectId}/boq${revisionId ? `?revision=${revisionId}` : ''}`,
    [projectId, revisionId],
  );

  const load = async () => {
    if (!revisionId || !snapshotId) {
      setError(new Error('Revision and snapshot identity are required.'));
      return;
    }
    setError(null);
    try {
      setPreview(await getNativeBoqPreview(revisionId, snapshotId));
    } catch (requestError) {
      setError(requestError);
    }
  };

  useEffect(() => {
    load();
  // Snapshot identity is intentionally pinned to the URL.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revisionId, snapshotId]);

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

  if (!BOQ_V2_ENABLED) {
    return <section className="boq-empty-state"><h2>Native quotation preview is disabled</h2></section>;
  }
  if (!preview && !error) return <Loading />;
  if (error || !preview) {
    return (
      <section className="boq-empty-state boq-error-state" role="alert">
        <FileWarning size={30} />
        <h2>Quotation snapshot unavailable</h2>
        <p>{errorMessage(error)}</p>
        <div className="quotation-actions">
          <Link className="boq-button boq-button-secondary" to={backPath}><ArrowLeft size={16} /> Back</Link>
          <button type="button" className="boq-button boq-button-primary" onClick={load}><RefreshCw size={16} /> Retry</button>
        </div>
      </section>
    );
  }

  const payload = preview.document;
  const quotation = payload.quotation || {};
  const calculation = payload.calculation || {};
  const revision = payload.revision || {};
  const documentIdentity = payload.document || {};
  const scope = (payload.scope || []).filter((node) => node.inclusion_state !== 'EXCLUDED');

  return (
    <main className="quotation-preview-page">
      <header className="quotation-preview-toolbar">
        <div>
          <Link className="boq-back-link" to={backPath} aria-label="Back to quotation workspace"><ArrowLeft size={19} /></Link>
          <div>
            <span className="boq-eyebrow">PINNED SNAPSHOT</span>
            <h1>{documentIdentity.number} · R{revision.number}</h1>
            <p>Snapshot {preview.snapshot.snapshot_id} · {preview.snapshot.payload_sha256.slice(0, 12)}</p>
          </div>
        </div>
        <div className="quotation-actions">
          <button type="button" className="boq-button boq-button-secondary" onClick={() => navigator.clipboard.writeText(window.location.href)}>
            <Copy size={16} /> Copy deep link
          </button>
          <button type="button" className="boq-button boq-button-secondary" onClick={() => exportSnapshot('XLSX')} disabled={busy}>
            <Download size={16} /> Excel
          </button>
          <button type="button" className="boq-button boq-button-primary" onClick={() => exportSnapshot('PDF')} disabled={busy}>
            <Download size={16} /> {busy ? 'Preparing…' : 'PDF'}
          </button>
        </div>
      </header>

      {error ? <div className="boq-notice boq-notice-danger" role="alert">{errorMessage(error)}</div> : null}

      <article className="quotation-paper" aria-label="Customer quotation preview">
        <header className="quotation-paper-header">
          <div>
            <span>QUOTATION</span>
            <h2>{quotation.title || 'ใบเสนอราคา'}</h2>
          </div>
          <dl>
            <div><dt>No.</dt><dd>{documentIdentity.number}</dd></div>
            <div><dt>Revision</dt><dd>R{revision.number}</dd></div>
            <div><dt>Date</dt><dd>{quotation.quotation_date || '—'}</dd></div>
            <div><dt>Valid until</dt><dd>{quotation.valid_until || '—'}</dd></div>
          </dl>
        </header>
        <section className="quotation-addresses">
          <div><span>PROJECT</span><strong>{payload.project?.name || '—'}</strong></div>
          <div>
            <span>CUSTOMER</span>
            <strong>{quotation.customer_name || '—'}</strong>
            <p>{quotation.customer_address || '—'}</p>
            <p>Tax ID {quotation.customer_tax_id || '—'} · {quotation.customer_contact || '—'}</p>
          </div>
        </section>
        <div className="quotation-preview-table-shell">
          <table className="quotation-preview-table">
            <thead><tr><th>#</th><th>Scope</th><th>Qty</th><th>Unit</th><th>Material</th><th>Labor</th><th>Total</th></tr></thead>
            <tbody>
              {scope.map((node, index) => (
                node.node_kind === 'ITEM' ? (
                  <tr key={node.id || node.logical_id}>
                    <td>{index + 1}</td>
                    <td><strong>{node.description}</strong><small>{node.specification}</small></td>
                    <td>{money(node.quantity)}</td><td>{node.unit}</td>
                    <td>{money(node.sell_material_unit_rate)}</td>
                    <td>{money(node.sell_labor_unit_rate)}</td>
                    <td>{money(node.sell_total)}</td>
                  </tr>
                ) : (
                  <tr className="quotation-section-row" key={node.id || node.logical_id}>
                    <td colSpan="7">{node.description}</td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
        <section className="quotation-paper-footer">
          <div>
            <h3>Payment schedule</h3>
            {(quotation.payment_schedule || []).map((item) => (
              <p key={item.label}><span>{item.label}</span><strong>{money(item.amount)} THB</strong></p>
            ))}
            <h3>Commercial terms</h3>
            <ol>{(quotation.commercial_terms || []).map((term) => <li key={term}>{term}</li>)}</ol>
          </div>
          <dl className="quotation-preview-totals">
            <div><dt>Subtotal</dt><dd>{money(calculation.subtotal)}</dd></div>
            <div><dt>Discount</dt><dd>{money(calculation.discount_amount)}</dd></div>
            <div><dt>Net ex VAT</dt><dd>{money(calculation.net_sell_ex_vat)}</dd></div>
            <div><dt>VAT {calculation.vat_rate}%</dt><dd>{money(calculation.vat_amount)}</dd></div>
            <div><dt>Grand total</dt><dd>{money(calculation.grand_total)} THB</dd></div>
          </dl>
        </section>
      </article>
    </main>
  );
}
