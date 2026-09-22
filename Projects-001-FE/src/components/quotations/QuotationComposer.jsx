import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  Download,
  Eye,
  FileImage,
  ImagePlus,
  RefreshCw,
  Save,
  Send,
  Trash2,
  Upload,
} from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  createNativeBoqPreview,
  deleteNativeBoqMedia,
  exportNativeBoqQuotation,
  getNativeBoqExportDownload,
  getNativeBoqMediaCandidates,
  getNativeBoqMediaSignedUrl,
  getNativeBoqPreview,
  getNativeBoqRevision,
  importNativeBoqMedia,
  issueNativeBoqQuotation,
  saveNativeBoqDraft,
  uploadNativeBoqMedia,
} from '../../api';
import { canAccessOwnerArea, getStoredAuthUser } from '../../auth';
import { BOQ_V2_ENABLED } from '../../config/features';
import Loading from '../Loading';
import { buildSavePayload, normalizeQuotationDraft, parseRevisionDraft } from '../boq/boqDraftState';
import QuotationDocumentPreview from './QuotationDocumentPreview';
import {
  addMediaToVisualPages,
  draftDocumentFromRevision,
  moveDocumentSection,
  moveVisualPage,
  normalizeDocumentSections,
  removeVisualEntry,
  removeVisualPage,
  toggleDocumentSection,
  updateVisualEntry,
  updateVisualPage,
} from './quotationDocumentState';
import './quotation.css';

function domainMessage(error) {
  return error?.payload?.detail?.message || error?.detail || error?.message || 'Quotation request failed.';
}

function paymentScheduleUpdate(schedule, index, updates) {
  return schedule.map((item, itemIndex) => itemIndex === index ? { ...item, ...updates } : item);
}

function SectionFields({ quotation, mutable, onChange }) {
  return (
    <div className="quotation-composer-fields">
      <label className="quotation-field-wide"><span>ชื่อเอกสาร / Document title</span><input value={quotation.title || ''} onChange={(event) => onChange({ title: event.target.value })} disabled={!mutable} /></label>
      <label><span>ลูกค้า / Customer</span><input value={quotation.customer_name || ''} onChange={(event) => onChange({ customer_name: event.target.value })} disabled={!mutable} /></label>
      <label><span>Tax ID</span><input value={quotation.customer_tax_id || ''} onChange={(event) => onChange({ customer_tax_id: event.target.value })} disabled={!mutable} /></label>
      <label className="quotation-field-wide"><span>ที่อยู่ / Address</span><textarea rows="3" value={quotation.customer_address || ''} onChange={(event) => onChange({ customer_address: event.target.value })} disabled={!mutable} /></label>
      <label><span>ผู้ติดต่อ / Contact</span><input value={quotation.customer_contact || ''} onChange={(event) => onChange({ customer_contact: event.target.value })} disabled={!mutable} /></label>
      <label><span>วันที่ / Date</span><input type="date" value={quotation.quotation_date || ''} onChange={(event) => onChange({ quotation_date: event.target.value })} disabled={!mutable} /></label>
      <label><span>ใช้ได้ถึง / Valid until</span><input type="date" value={quotation.valid_until || ''} onChange={(event) => onChange({ valid_until: event.target.value })} disabled={!mutable} /></label>
      <label><span>VAT (%)</span><input type="number" min="0" max="100" step="0.0001" value={quotation.vat_rate || '7.0000'} onChange={(event) => onChange({ vat_rate: event.target.value })} disabled={!mutable} /></label>
      <label><span>ส่วนลด / Discount</span><div className="quotation-split-field"><select value={quotation.discount_type || 'NONE'} onChange={(event) => onChange({ discount_type: event.target.value, discount_value: event.target.value === 'NONE' ? '0.0000' : quotation.discount_value })} disabled={!mutable}><option value="NONE">None</option><option value="PERCENT">Percent</option><option value="FIXED">Fixed THB</option></select><input type="number" min="0" value={quotation.discount_value || '0.0000'} onChange={(event) => onChange({ discount_value: event.target.value })} disabled={!mutable || quotation.discount_type === 'NONE'} aria-label="Discount value" /></div></label>
    </div>
  );
}

function PaymentEditor({ quotation, mutable, onChange }) {
  const schedule = quotation.payment_schedule || [];
  return (
    <div className="quotation-payment-editor">
      {schedule.map((item, index) => (
        <div className="quotation-composer-payment-row" key={`${item.label}-${index}`}>
          <span>{index + 1}</span>
          <input value={item.label || ''} onChange={(event) => onChange({ payment_schedule: paymentScheduleUpdate(schedule, index, { label: event.target.value }) })} disabled={!mutable} aria-label={`Payment milestone ${index + 1}`} />
          <input type="number" min="0" max="100" value={item.percentage ?? ''} onChange={(event) => onChange({ payment_schedule: paymentScheduleUpdate(schedule, index, { percentage: event.target.value, fixed_amount: null }) })} disabled={!mutable} aria-label={`Payment percentage ${index + 1}`} />
          <span>%</span>
          {mutable ? <button type="button" onClick={() => onChange({ payment_schedule: schedule.filter((_, itemIndex) => itemIndex !== index) })} aria-label={`Remove milestone ${index + 1}`}><Trash2 size={15} /></button> : null}
        </div>
      ))}
      {mutable ? <button type="button" className="quotation-inline-action" onClick={() => onChange({ payment_schedule: [...schedule, { label: '', percentage: '', fixed_amount: null }] })}>+ เพิ่มงวด / Add milestone</button> : null}
      <p className="quotation-editor-hint">Percentage milestones must total exactly 100% before saving.</p>
    </div>
  );
}

function MediaLibrary({ assets, mediaUrls, usedIds, mutable, busy, onAdd, onDelete }) {
  return (
    <div className="quotation-media-library">
      {assets.map((asset) => (
        <article key={asset.id}>
          {mediaUrls[String(asset.id)] ? <img src={mediaUrls[String(asset.id)]} alt={asset.original_filename || 'Quotation asset'} /> : <div className="quotation-media-placeholder"><FileImage size={22} /></div>}
          <div><strong>{asset.original_filename || 'Quotation image'}</strong><span>{asset.width} × {asset.height} · {Math.max(1, Math.round(asset.size_bytes / 1024))} KB</span></div>
          {mutable ? <div><button type="button" onClick={() => onAdd(asset.id)} disabled={busy || usedIds.has(String(asset.id))}>{usedIds.has(String(asset.id)) ? 'Added' : 'Add to page'}</button><button type="button" onClick={() => onDelete(asset.id)} disabled={busy || usedIds.has(String(asset.id))} aria-label={`Delete ${asset.original_filename || 'image'}`}><Trash2 size={14} /></button></div> : null}
        </article>
      ))}
      {!assets.length ? <div className="quotation-media-empty"><ImagePlus size={24} /><p>Upload or import project photos to compose visual pages.</p></div> : null}
    </div>
  );
}

function VisualEditor({ quotation, nodes, mediaUrls, mutable, busy, onChange, onUpload, onOpenCandidates, onDeleteMedia }) {
  const fileInputRef = useRef(null);
  const pages = quotation.visual_pages || [];
  const assets = quotation.media_assets || [];
  const usedIds = new Set(pages.flatMap((page) => page.entries.map((entry) => String(entry.media_id))));
  const addAsset = (mediaId) => onChange({
    visual_pages: addMediaToVisualPages(pages, mediaId),
    document_sections: toggleDocumentSection(quotation.document_sections, 'VISUAL', true),
  });
  return (
    <div className="quotation-visual-editor">
      <div className="quotation-visual-actions">
        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" multiple hidden onChange={(event) => onUpload([...event.target.files])} />
        <button type="button" className="boq-button boq-button-primary" onClick={() => fileInputRef.current?.click()} disabled={!mutable || busy}><Upload size={15} /> {busy ? 'Uploading…' : 'Upload photos'}</button>
        <button type="button" className="boq-button boq-button-secondary" onClick={onOpenCandidates} disabled={!mutable || busy}><ImagePlus size={15} /> Choose project photos</button>
        <span>JPEG, PNG, WebP, HEIC/HEIF · max 10 MB</span>
      </div>
      <MediaLibrary assets={assets} mediaUrls={mediaUrls} usedIds={usedIds} mutable={mutable} busy={busy} onAdd={addAsset} onDelete={onDeleteMedia} />
      <div className="quotation-visual-pages-editor">
        {pages.map((page, pageIndex) => (
          <section key={`visual-page-${pageIndex}`}>
            <header><strong>Visual page {pageIndex + 1}</strong><div><button type="button" onClick={() => onChange({ visual_pages: moveVisualPage(pages, pageIndex, 'up') })} disabled={!mutable || pageIndex === 0} aria-label="Move visual page up"><ArrowUp size={14} /></button><button type="button" onClick={() => onChange({ visual_pages: moveVisualPage(pages, pageIndex, 'down') })} disabled={!mutable || pageIndex === pages.length - 1} aria-label="Move visual page down"><ArrowDown size={14} /></button><button type="button" onClick={() => onChange({ visual_pages: removeVisualPage(pages, pageIndex) })} disabled={!mutable} aria-label="Delete visual page"><Trash2 size={14} /></button></div></header>
            <div className="quotation-visual-page-fields">
              <label><span>Layout</span><select value={page.layout} onChange={(event) => onChange({ visual_pages: updateVisualPage(pages, pageIndex, { layout: event.target.value, entries: page.entries.slice(0, { SINGLE: 1, TWO_UP: 2, FOUR_UP: 4 }[event.target.value]) }) })} disabled={!mutable}><option value="SINGLE">1 image</option><option value="TWO_UP">2 images</option><option value="FOUR_UP">4 images</option></select></label>
              <label><span>หัวข้อภาษาไทย</span><input value={page.title_th || ''} onChange={(event) => onChange({ visual_pages: updateVisualPage(pages, pageIndex, { title_th: event.target.value }) })} disabled={!mutable} /></label>
              <label><span>English heading</span><input value={page.title_en || ''} onChange={(event) => onChange({ visual_pages: updateVisualPage(pages, pageIndex, { title_en: event.target.value }) })} disabled={!mutable} /></label>
              <label className="quotation-field-wide"><span>คำอธิบาย / Description</span><textarea rows="2" value={page.description_th || ''} onChange={(event) => onChange({ visual_pages: updateVisualPage(pages, pageIndex, { description_th: event.target.value }) })} disabled={!mutable} /></label>
            </div>
            <div className="quotation-visual-entry-editor">
              {page.entries.map((entry) => (
                <article key={entry.media_id}>
                  {mediaUrls[String(entry.media_id)] ? <img src={mediaUrls[String(entry.media_id)]} alt="" /> : <div className="quotation-media-placeholder"><FileImage size={20} /></div>}
                  <div><input value={entry.caption_th || ''} onChange={(event) => onChange({ visual_pages: updateVisualEntry(pages, pageIndex, entry.media_id, { caption_th: event.target.value }) })} disabled={!mutable} placeholder="คำบรรยายภาษาไทย" /><input value={entry.caption_en || ''} onChange={(event) => onChange({ visual_pages: updateVisualEntry(pages, pageIndex, entry.media_id, { caption_en: event.target.value }) })} disabled={!mutable} placeholder="English caption" /><select value={entry.scope_logical_id || ''} onChange={(event) => onChange({ visual_pages: updateVisualEntry(pages, pageIndex, entry.media_id, { scope_logical_id: event.target.value || null }) })} disabled={!mutable}><option value="">Not linked to BOQ</option>{nodes.filter((node) => node.node_kind === 'ITEM').map((node) => <option key={node.logical_id} value={node.logical_id}>{node.display_path || node.item_code} · {node.description}</option>)}</select></div>
                  {mutable ? <button type="button" onClick={() => onChange({ visual_pages: removeVisualEntry(pages, pageIndex, entry.media_id) })} aria-label="Remove photo from page"><Trash2 size={15} /></button> : null}
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function CandidateDialog({ candidates, busy, onClose, onImport }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const previousFocus = document.activeElement;
    const dialog = dialogRef.current;
    dialog?.focus();
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !dialog) return;
      const focusable = [...dialog.querySelectorAll('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="quotation-modal-backdrop" role="presentation">
      <section ref={dialogRef} className="quotation-modal quotation-candidate-dialog" role="dialog" aria-modal="true" aria-labelledby="candidate-dialog-title" tabIndex="-1">
        <div><span className="boq-eyebrow">PROJECT MEDIA</span><h2 id="candidate-dialog-title">เลือกรูปจากโครงการ</h2><p>ระบบจะ copy เป็น quotation-owned private asset เพื่อรักษาประวัติเอกสาร</p></div>
        <div className="quotation-candidate-grid">
          {candidates.map((candidate) => <article key={`${candidate.origin_type}-${candidate.origin_id}`}><img src={candidate.preview_url} alt={candidate.file_name || 'Project media'} /><strong>{candidate.file_name || candidate.origin_type}</strong><span>{candidate.origin_type}</span><button type="button" onClick={() => onImport(candidate)} disabled={busy}>Import copy</button></article>)}
          {!candidates.length ? <p>No compatible Daily Report or Inspection photos were found.</p> : null}
        </div>
        <div className="quotation-modal-actions"><button type="button" className="boq-button boq-button-secondary" onClick={onClose}>Close</button></div>
      </section>
    </div>
  );
}

export default function QuotationComposer() {
  const { quotationId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const revisionId = searchParams.get('revision_id') || '';
  const snapshotId = searchParams.get('snapshot_id') || '';
  const [revision, setRevision] = useState(null);
  const [quotation, setQuotation] = useState(() => normalizeQuotationDraft());
  const [nodes, setNodes] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [mediaUrls, setMediaUrls] = useState({});
  const [activeSection, setActiveSection] = useState('SUMMARY');
  const [mobileMode, setMobileMode] = useState('edit');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState(null);
  const [candidates, setCandidates] = useState(null);
  const isOwner = canAccessOwnerArea(getStoredAuthUser());
  const mutable = Boolean(isOwner && revision?.status === 'DRAFT' && !snapshotId);

  const loadMediaUrls = useCallback(async (currentRevisionId, assets) => {
    const entries = await Promise.all((assets || []).map(async (asset) => {
      try {
        const access = await getNativeBoqMediaSignedUrl(currentRevisionId, asset.id);
        return [String(asset.id), access.preview_url];
      } catch {
        return [String(asset.id), null];
      }
    }));
    setMediaUrls(Object.fromEntries(entries));
  }, []);

  const load = useCallback(async () => {
    if (!revisionId) {
      setError(new Error('A revision_id is required for a stable quotation deep link.'));
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const currentRevision = await getNativeBoqRevision(revisionId);
      if (quotationId && String(currentRevision.document_id) !== quotationId) throw new Error('Revision does not belong to this quotation.');
      const normalized = normalizeQuotationDraft(currentRevision.quotation);
      setRevision(currentRevision);
      setQuotation(normalized);
      setNodes(parseRevisionDraft(currentRevision));
      setDirty(false);
      await loadMediaUrls(revisionId, normalized.media_assets);
      if (snapshotId) setSnapshot(await getNativeBoqPreview(revisionId, snapshotId));
      else setSnapshot(null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [loadMediaUrls, quotationId, revisionId, snapshotId]);

  useEffect(() => { load(); }, [load]);

  const change = (updates) => {
    setQuotation((current) => ({ ...current, ...updates }));
    setDirty(true);
    setError(null);
  };

  const save = async () => {
    if (!mutable || !dirty) return revision;
    setBusy(true);
    setError(null);
    try {
      const saved = await saveNativeBoqDraft(revision.revision_id, buildSavePayload(revision.version, nodes, quotation));
      const normalized = normalizeQuotationDraft(saved.quotation);
      setRevision(saved);
      setQuotation(normalized);
      setNodes(parseRevisionDraft(saved));
      setDirty(false);
      return saved;
    } catch (requestError) {
      setError(requestError);
      return null;
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const keydown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        save();
      }
    };
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  });

  const preview = async () => {
    if (dirty) { setError(new Error('Save the document before creating an exact snapshot.')); return; }
    setBusy(true);
    setError(null);
    try {
      const created = await createNativeBoqPreview(revision.revision_id, revision.version);
      navigate(`/quotations/${revision.document_id}?revision_id=${revision.revision_id}&snapshot_id=${created.snapshot.snapshot_id}`);
    } catch (requestError) { setError(requestError); } finally { setBusy(false); }
  };

  const issue = async () => {
    if (dirty) { setError(new Error('Save and review the latest preview before issuing.')); return; }
    setBusy(true);
    setError(null);
    try {
      const checkedPreview = await createNativeBoqPreview(revision.revision_id, revision.version);
      if (!window.confirm(`Issue ${revision.document_number} R${revision.revision_number} from the reviewed v${checkedPreview.snapshot.source_version} snapshot?`)) return;
      const issued = await issueNativeBoqQuotation(revision.revision_id, revision.version, { previewSnapshotId: checkedPreview.snapshot.snapshot_id });
      navigate(`/quotations/${issued.document_id}?revision_id=${issued.revision_id}&snapshot_id=${issued.issued_snapshot_id}`);
    } catch (requestError) { setError(requestError); } finally { setBusy(false); }
  };

  const exportSnapshot = async (fileFormat) => {
    const targetSnapshot = snapshotId || revision?.issued_snapshot_id;
    if (!targetSnapshot) { setError(new Error('Create or open an exact snapshot before exporting.')); return; }
    setBusy(true);
    setError(null);
    try {
      const artifact = await exportNativeBoqQuotation(revision.revision_id, { snapshot_id: targetSnapshot, audience: 'CUSTOMER', file_format: fileFormat });
      const download = await getNativeBoqExportDownload(revision.revision_id, artifact.artifact_id);
      window.location.assign(download.download_url);
    } catch (requestError) { setError(requestError); } finally { setBusy(false); }
  };

  const upload = async (files) => {
    if (!files.length || !mutable) return;
    if (dirty) { setError(new Error('Save document edits before uploading media.')); return; }
    setBusy(true);
    setError(null);
    let version = revision.version;
    const failures = [];
    for (const file of files) {
      try {
        const media = await uploadNativeBoqMedia(revision.revision_id, version, file);
        version = media.revision_version;
      } catch (requestError) {
        failures.push(`${file.name}: ${domainMessage(requestError)}`);
      }
    }
    await load();
    if (failures.length) setError(new Error(`Some uploads failed: ${failures.join(' · ')}`));
    setBusy(false);
  };

  const openCandidates = async () => {
    setBusy(true); setError(null);
    try { setCandidates(await getNativeBoqMediaCandidates(revision.revision_id)); }
    catch (requestError) { setError(requestError); }
    finally { setBusy(false); }
  };

  const importCandidate = async (candidate) => {
    if (dirty) { setError(new Error('Save document edits before importing media.')); return; }
    setBusy(true); setError(null);
    try {
      await importNativeBoqMedia(revision.revision_id, revision.version, candidate.origin_type, candidate.origin_id);
      setCandidates(null);
      await load();
    } catch (requestError) { setError(requestError); }
    finally { setBusy(false); }
  };

  const deleteMedia = async (mediaId) => {
    if (!window.confirm('Delete this unused draft image?')) return;
    setBusy(true); setError(null);
    try { await deleteNativeBoqMedia(revision.revision_id, mediaId, revision.version); await load(); }
    catch (requestError) { setError(requestError); }
    finally { setBusy(false); }
  };

  if (!BOQ_V2_ENABLED) return <section className="boq-empty-state"><h2>Quotation Composer is disabled</h2></section>;
  if (loading && !revision) return <Loading />;
  if (error && !revision) return <section className="boq-empty-state boq-error-state" role="alert"><AlertTriangle size={28} /><h2>Quotation unavailable</h2><p>{domainMessage(error)}</p><button type="button" className="boq-button boq-button-primary" onClick={load}><RefreshCw size={16} /> Retry</button></section>;

  const sections = normalizeDocumentSections(quotation.document_sections);
  const exactDocument = snapshot?.document;
  const activeDocument = exactDocument || draftDocumentFromRevision(revision, quotation);
  const activeDefinition = sections.find((section) => section.section_type === activeSection) || sections[0];

  return (
    <main className="quotation-composer-page">
      <header className="quotation-composer-toolbar">
        <div><Link to="/quotations" aria-label="Back to Quotation Center"><ArrowLeft size={18} /></Link><div><span className="boq-eyebrow">{snapshotId ? 'EXACT SNAPSHOT' : 'DOCUMENT COMPOSER'}</span><h1>{revision.document_number} <small>R{revision.revision_number} · {revision.status}</small></h1><p>{revision.project_name} · schema {activeDocument.schema_version || 'v1'}</p></div></div>
        <div className="quotation-composer-toolbar-actions">
          {dirty ? <span className="quotation-unsaved">Unsaved changes</span> : <span className="quotation-saved"><Check size={14} /> Saved</span>}
          {!snapshotId && mutable ? <button type="button" className="boq-button boq-button-secondary" onClick={save} disabled={!dirty || busy}><Save size={15} /> Save</button> : null}
          {!snapshotId ? <button type="button" className="boq-button boq-button-secondary" onClick={preview} disabled={busy || dirty}><Eye size={15} /> ดูตัวอย่างเอกสาร / Preview quotation</button> : <button type="button" className="boq-button boq-button-secondary" onClick={() => navigate(`/quotations/${revision.document_id}?revision_id=${revision.revision_id}`)}><ArrowLeft size={15} /> Back to composer</button>}
          {!snapshotId && mutable ? <button type="button" className="boq-button boq-button-primary" onClick={issue} disabled={busy || dirty}><Send size={15} /> Issue</button> : null}
          {snapshotId ? <><button type="button" className="boq-button boq-button-secondary" onClick={() => exportSnapshot('XLSX')} disabled={busy}><Download size={15} /> XLSX</button><button type="button" className="boq-button boq-button-primary" onClick={() => exportSnapshot('PDF')} disabled={busy}><Download size={15} /> PDF</button></> : null}
        </div>
      </header>

      {error ? <div className="boq-notice boq-notice-danger quotation-composer-error" role="alert"><AlertTriangle size={17} /><div><strong>Action could not be completed</strong><p>{domainMessage(error)}</p></div><button type="button" onClick={() => setError(null)} aria-label="Dismiss error">×</button></div> : null}

      {snapshotId ? (
        <div className="quotation-exact-banner"><Eye size={17} /><div><strong>ตัวอย่างฉบับตรึง / Exact snapshot</strong><p>Read-only snapshot {snapshotId} · source v{snapshot?.snapshot?.source_version}</p></div></div>
      ) : null}

      {!snapshotId ? <div className="quotation-mobile-mode" role="group" aria-label="Composer view"><button type="button" className={mobileMode === 'edit' ? 'active' : ''} onClick={() => setMobileMode('edit')}>Edit</button><button type="button" className={mobileMode === 'preview' ? 'active' : ''} onClick={() => setMobileMode('preview')}>Preview</button></div> : null}
      <div className={`quotation-composer-layout${snapshotId ? ' quotation-composer-exact' : ''} quotation-mobile-${mobileMode}`}>
        {!snapshotId ? <aside className="quotation-section-rail" aria-label="Document sections">
          <header><span>DOCUMENT PACKAGE</span><strong>Sections</strong></header>
          {sections.map((section, index) => (
            <article className={activeSection === section.section_type ? 'active' : ''} key={section.section_type}>
              <button type="button" onClick={() => setActiveSection(section.section_type)}><span>{index + 1}</span><span><strong>{section.title_th}</strong><small>{section.title_en}</small></span></button>
              <div><input type="checkbox" checked={section.enabled} onChange={(event) => change({ document_sections: toggleDocumentSection(sections, section.section_type, event.target.checked) })} disabled={!mutable || ['SUMMARY', 'DETAILED_BOQ'].includes(section.section_type)} aria-label={`Enable ${section.title_en}`} /><button type="button" onClick={() => change({ document_sections: moveDocumentSection(sections, section.section_type, 'up') })} disabled={!mutable || index <= 1 || section.section_type === 'ACCEPTANCE'} aria-label={`Move ${section.title_en} up`}><ArrowUp size={13} /></button><button type="button" onClick={() => change({ document_sections: moveDocumentSection(sections, section.section_type, 'down') })} disabled={!mutable || index >= sections.length - 2 || section.section_type === 'SUMMARY'} aria-label={`Move ${section.title_en} down`}><ArrowDown size={13} /></button></div>
            </article>
          ))}
        </aside> : null}

        {!snapshotId ? <section className="quotation-active-editor" aria-labelledby="quotation-editor-title">
          <header><div><span className="boq-eyebrow">SECTION {activeDefinition.position + 1}</span><h2 id="quotation-editor-title">{activeDefinition.title_th}<small>{activeDefinition.title_en}</small></h2></div>{!activeDefinition.enabled ? <span className="quotation-section-disabled">Excluded from output</span> : null}</header>
          {activeSection === 'SUMMARY' ? <SectionFields quotation={quotation} mutable={mutable} onChange={change} /> : null}
          {activeSection === 'DETAILED_BOQ' ? <div className="quotation-linked-boq"><strong>Source of truth: Native BOQ</strong><p>Scope, quantities and customer prices are edited in the BOQ workspace and rendered here without duplicating state.</p><Link className="boq-button boq-button-secondary" to={`/project/detail/${revision.project_id}/boq?revision=${revision.revision_id}`}>Open source BOQ</Link></div> : null}
          {activeSection === 'VISUAL' ? <VisualEditor quotation={quotation} nodes={nodes} mediaUrls={mediaUrls} mutable={mutable} busy={busy} onChange={change} onUpload={upload} onOpenCandidates={openCandidates} onDeleteMedia={deleteMedia} /> : null}
          {activeSection === 'PAYMENT_TERMS' ? <PaymentEditor quotation={quotation} mutable={mutable} onChange={change} /> : null}
          {activeSection === 'TERMS' ? <label className="quotation-terms-editor"><span>หนึ่งเงื่อนไขต่อบรรทัด / One term per line</span><textarea rows="14" value={(quotation.commercial_terms || []).join('\n')} onChange={(event) => change({ commercial_terms: event.target.value.split('\n').filter((line) => line.trim()) })} disabled={!mutable} /></label> : null}
          {activeSection === 'ACCEPTANCE' ? <div className="quotation-acceptance-editor"><strong>Printable acceptance placeholders</strong><p>ส่วนนี้แสดงช่องลายเซ็นบนเอกสารเท่านั้น การยอมรับในระบบยังใช้ lifecycle “Record acceptance” และไม่ใช่ digital signature.</p></div> : null}
        </section> : null}

        <div className="quotation-composer-preview-pane"><QuotationDocumentPreview document={activeDocument} mediaUrls={mediaUrls} mode="paged" /></div>
      </div>
      {candidates ? <CandidateDialog candidates={candidates} busy={busy} onClose={() => setCandidates(null)} onImport={importCandidate} /> : null}
    </main>
  );
}
