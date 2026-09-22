import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Maximize2, Minus, Plus } from 'lucide-react';

import { chunkScopeRows, enabledSections } from './quotationDocumentState';

const numberFormat = new Intl.NumberFormat('th-TH', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function money(value) {
  const number = Number(value || 0);
  return numberFormat.format(Number.isFinite(number) ? number : 0);
}

function bilingualTitle(section, fallbackTh, fallbackEn) {
  return (
    <>
      <span>{section?.title_th || fallbackTh}</span>
      <small>{section?.title_en || fallbackEn}</small>
    </>
  );
}

function PageFrame({ document, pageNumber, pageCount, children, className = '' }) {
  return (
    <article className={`quotation-a4-page ${className}`} aria-label={`Quotation page ${pageNumber} of ${pageCount}`}>
      <header className="quotation-a4-brand">
        <div className="quotation-a4-mark" aria-hidden="true">R</div>
        <div><strong>RAYADEE</strong><span>BETTER SPACE. BETTER BUSINESS.</span></div>
        <div className="quotation-a4-identity">
          <strong>{document.document?.number || 'DRAFT'}</strong>
          <span>{document.project?.name || 'Project'}</span>
        </div>
      </header>
      <div className="quotation-a4-content">{children}</div>
      <footer className="quotation-a4-footer">
        <span>RAYADEE · Client Quotation</span>
        <span>{document.document?.number || 'Draft'} · R{document.revision?.number || 1}</span>
        <span>Page {pageNumber} / {pageCount}</span>
      </footer>
    </article>
  );
}

function SummaryPage({ document, section }) {
  const quotation = document.quotation || {};
  const calculation = document.calculation || {};
  const summaryRows = (document.scope || []).filter((node) => (
    node.inclusion_state !== 'EXCLUDED' && Number(node.depth || 0) === 0
  ));
  return (
    <>
      <div className="quotation-summary-heading">
        <div>
          <p>QUOTATION</p>
          <h2>{quotation.title || section?.title_th || 'ใบเสนอราคา'}</h2>
          <span>{section?.title_en || 'Quotation Summary'}</span>
        </div>
        <dl>
          <div><dt>No.</dt><dd>{document.document?.number || '—'}</dd></div>
          <div><dt>Revision</dt><dd>R{document.revision?.number || 1}</dd></div>
          <div><dt>Date</dt><dd>{quotation.quotation_date || '—'}</dd></div>
          <div><dt>Valid until</dt><dd>{quotation.valid_until || '—'}</dd></div>
        </dl>
      </div>
      <div className="quotation-summary-parties">
        <div><span>โครงการ / PROJECT</span><strong>{document.project?.name || '—'}</strong></div>
        <div>
          <span>ลูกค้า / CUSTOMER</span>
          <strong>{quotation.customer_name || '—'}</strong>
          <p>{quotation.customer_address || '—'}</p>
          <p>{quotation.customer_tax_id ? `Tax ID ${quotation.customer_tax_id}` : ''}{quotation.customer_contact ? ` · ${quotation.customer_contact}` : ''}</p>
        </div>
      </div>
      <table className="quotation-document-table quotation-summary-table">
        <thead><tr><th>#</th><th>Scope / ขอบเขตงาน</th><th>Material</th><th>Labor</th><th>Total</th></tr></thead>
        <tbody>
          {summaryRows.length ? summaryRows.map((row, index) => (
            <tr key={row.logical_id || row.id || index}>
              <td>{index + 1}</td><td>{row.description || '—'}</td><td>—</td><td>—</td><td>{money(row.sell_total)}</td>
            </tr>
          )) : <tr><td colSpan="5" className="quotation-empty-cell">No BOQ scope / ยังไม่มีรายการ BOQ</td></tr>}
        </tbody>
      </table>
      <div className="quotation-summary-bottom">
        <div>
          <h3>Payment schedule / เงื่อนไขการชำระเงิน</h3>
          {(quotation.payment_schedule || []).slice(0, 4).map((item, index) => {
            const amount = item.amount ?? item.fixed_amount ?? (
              Number(calculation.grand_total || 0) * Number(item.percentage || 0) / 100
            );
            return <p key={`${item.label}-${index}`}><span>{item.label}</span><strong>{money(amount)} THB</strong></p>;
          })}
        </div>
        <dl className="quotation-document-totals">
          <div><dt>Subtotal</dt><dd>{money(calculation.subtotal)}</dd></div>
          <div><dt>Discount</dt><dd>{money(calculation.discount_amount)}</dd></div>
          <div><dt>Net ex VAT</dt><dd>{money(calculation.net_sell_ex_vat)}</dd></div>
          <div><dt>VAT {calculation.vat_rate || 0}%</dt><dd>{money(calculation.vat_amount)}</dd></div>
          <div><dt>Grand total</dt><dd>{money(calculation.grand_total)} THB</dd></div>
        </dl>
      </div>
    </>
  );
}

function DetailedBoqPage({ rows, section, continuation }) {
  return (
    <>
      <h2 className="quotation-section-title">
        {bilingualTitle(section, 'รายละเอียด BOQ', `Detailed BOQ${continuation ? ' — Continued' : ''}`)}
      </h2>
      <table className="quotation-document-table quotation-detail-table">
        <thead>
          <tr><th>Code</th><th>Description / รายละเอียด</th><th>Qty</th><th>Unit</th><th>Material / Unit</th><th>Labor / Unit</th><th>Total</th></tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((row, index) => (
            row.node_kind === 'ITEM' ? (
              <tr key={row.logical_id || row.id || index}>
                <td>{row.item_code || row.display_path || index + 1}</td>
                <td><strong>{row.description || '—'}</strong>{row.specification ? <small>{row.specification}</small> : null}</td>
                <td>{money(row.quantity)}</td><td>{row.unit || '—'}</td>
                <td>{money(row.sell_material_unit_rate)}</td><td>{money(row.sell_labor_unit_rate)}</td><td>{money(row.sell_total)}</td>
              </tr>
            ) : (
              <tr className="quotation-group-row" key={row.logical_id || row.id || index}>
                <td>{row.display_path || ''}</td><td colSpan="6">{row.description || row.node_kind}</td>
              </tr>
            )
          )) : <tr><td colSpan="7" className="quotation-empty-cell">No BOQ scope / ยังไม่มีรายการ BOQ</td></tr>}
        </tbody>
      </table>
    </>
  );
}

function VisualPage({ page, section, mediaById, mediaUrls }) {
  const layoutClass = `quotation-visual-grid-${String(page.layout || 'TWO_UP').toLowerCase()}`;
  return (
    <>
      <h2 className="quotation-section-title">
        <span>{page.title_th || section?.title_th || 'รูปภาพและรายละเอียดงาน'}</span>
        <small>{page.title_en || section?.title_en || 'Visual / Work Detail'}</small>
      </h2>
      {(page.description_th || page.description_en) ? (
        <div className="quotation-visual-intro">
          <p>{page.description_th}</p><p>{page.description_en}</p>
        </div>
      ) : null}
      <div className={`quotation-visual-grid ${layoutClass}`}>
        {(page.entries || []).map((entry) => {
          const media = mediaById.get(String(entry.media_id)) || {};
          const src = mediaUrls[String(entry.media_id)] || media.preview_url;
          return (
            <figure key={entry.media_id}>
              {src ? <img src={src} alt={entry.caption_th || entry.caption_en || 'Quotation work detail'} /> : (
                <div className="quotation-missing-media">Image unavailable / ไม่พบรูปภาพ</div>
              )}
              <figcaption>
                {entry.caption_th ? <strong>{entry.caption_th}</strong> : null}
                {entry.caption_en ? <span>{entry.caption_en}</span> : null}
              </figcaption>
            </figure>
          );
        })}
      </div>
    </>
  );
}

function PaymentPage({ document, section }) {
  const quotation = document.quotation || {};
  const calculation = document.calculation || {};
  return (
    <>
      <h2 className="quotation-section-title">{bilingualTitle(section, 'เงื่อนไขการชำระเงิน', 'Payment Terms')}</h2>
      <table className="quotation-document-table quotation-payment-table">
        <thead><tr><th>งวด / No.</th><th>รายละเอียด / Milestone</th><th>%</th><th>จำนวนเงิน / Amount</th></tr></thead>
        <tbody>
          {(quotation.payment_schedule || []).map((item, index) => {
            const amount = item.amount ?? item.fixed_amount ?? (
              Number(calculation.grand_total || 0) * Number(item.percentage || 0) / 100
            );
            return (
              <tr key={`${item.label}-${index}`}><td>{index + 1}</td><td>{item.label}</td><td>{item.percentage == null ? '—' : `${item.percentage}%`}</td><td>{money(amount)} THB</td></tr>
            );
          })}
        </tbody>
        <tfoot><tr><th colSpan="2">Total / รวม</th><th>{(quotation.payment_schedule || []).reduce((sum, item) => sum + Number(item.percentage || 0), 0)}%</th><th>{money(calculation.grand_total)} THB</th></tr></tfoot>
      </table>
    </>
  );
}

function TermsPage({ document, section }) {
  return (
    <>
      <h2 className="quotation-section-title">{bilingualTitle(section, 'ข้อกำหนดและเงื่อนไข', 'Terms & Conditions')}</h2>
      <ol className="quotation-terms-list">
        {(document.quotation?.commercial_terms || []).map((term, index) => <li key={`${term}-${index}`}>{term}</li>)}
      </ol>
    </>
  );
}

function AcceptancePage({ section }) {
  return (
    <>
      <h2 className="quotation-section-title">{bilingualTitle(section, 'การยอมรับใบเสนอราคา', 'Acceptance')}</h2>
      <p className="quotation-acceptance-note">
        ลงนามเพื่อยืนยันการยอมรับขอบเขต ราคา และเงื่อนไขตามใบเสนอราคาฉบับนี้<br />
        Signatures below are printable placeholders for an internally recorded agreement and are not a digital signature.
      </p>
      <div className="quotation-signature-grid">
        <section><h3>จัดทำ / เสนอโดย<br /><small>Prepared / Proposed by</small></h3><div className="quotation-signature-line" /><p>ชื่อ / Name</p><div className="quotation-signature-line" /><p>ตำแหน่ง / Position</p><div className="quotation-signature-line" /><p>วันที่ / Date</p></section>
        <section><h3>ยอมรับ / อนุมัติโดย<br /><small>Accepted / Approved by</small></h3><div className="quotation-signature-line" /><p>ชื่อ / Name</p><div className="quotation-signature-line" /><p>ตำแหน่ง / Position</p><div className="quotation-signature-line" /><p>วันที่ / Date</p></section>
      </div>
    </>
  );
}

function buildPages(document, mediaUrls) {
  const sections = enabledSections(document);
  const mediaById = new Map((document.composition?.media_assets || document.quotation?.media_assets || [])
    .map((media) => [String(media.id), media]));
  const pages = [];
  sections.forEach((section) => {
    if (section.section_type === 'SUMMARY') {
      pages.push({ key: 'summary', content: <SummaryPage document={document} section={section} /> });
    } else if (section.section_type === 'DETAILED_BOQ') {
      chunkScopeRows(document.scope).forEach((rows, index) => pages.push({
        key: `boq-${index}`,
        content: <DetailedBoqPage rows={rows} section={section} continuation={index > 0} />,
      }));
    } else if (section.section_type === 'VISUAL') {
      (document.composition?.visual_pages || document.quotation?.visual_pages || []).forEach((page, index) => pages.push({
        key: `visual-${index}`,
        className: 'quotation-visual-page',
        content: <VisualPage page={page} section={section} mediaById={mediaById} mediaUrls={mediaUrls} />,
      }));
    } else if (section.section_type === 'PAYMENT_TERMS') {
      pages.push({ key: 'payment', content: <PaymentPage document={document} section={section} /> });
    } else if (section.section_type === 'TERMS') {
      pages.push({ key: 'terms', content: <TermsPage document={document} section={section} /> });
    } else if (section.section_type === 'ACCEPTANCE') {
      pages.push({ key: 'acceptance', content: <AcceptancePage section={section} /> });
    }
  });
  return pages;
}

export default function QuotationDocumentPreview({ document, mediaUrls = {}, mode = 'all' }) {
  const [pageIndex, setPageIndex] = useState(0);
  const [zoom, setZoom] = useState(0.76);
  const [stageWidth, setStageWidth] = useState(0);
  const stageRef = useRef(null);
  const pages = useMemo(() => buildPages(document, mediaUrls), [document, mediaUrls]);
  const compact = stageWidth > 0 && stageWidth <= 640;
  const fitZoom = stageWidth > 0 ? Math.max(0.35, Math.min(1.2, (stageWidth - 28) / 794)) : zoom;
  const effectiveZoom = compact ? fitZoom : zoom;
  const safePageIndex = Math.min(pageIndex, Math.max(0, pages.length - 1));
  const visiblePages = mode === 'paged' ? pages.slice(safePageIndex, safePageIndex + 1) : pages;

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(([entry]) => setStageWidth(entry.contentRect.width));
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="quotation-document-preview" aria-label="Quotation document preview">
      <div className="quotation-preview-controls" aria-label="Document controls">
        {mode === 'paged' ? (
          <div>
            <button type="button" onClick={() => setPageIndex(Math.max(0, safePageIndex - 1))} disabled={safePageIndex === 0} aria-label="Previous page"><ChevronLeft size={16} /></button>
            <span>Page {Math.min(safePageIndex + 1, pages.length)} / {pages.length}</span>
            <button type="button" onClick={() => setPageIndex(Math.min(pages.length - 1, safePageIndex + 1))} disabled={safePageIndex >= pages.length - 1} aria-label="Next page"><ChevronRight size={16} /></button>
          </div>
        ) : <span>{pages.length} pages</span>}
        <div>
          <button type="button" onClick={() => setZoom((value) => Math.max(0.5, value - 0.1))} disabled={compact} aria-label="Zoom out"><Minus size={15} /></button>
          <span>{compact ? 'Fit ' : ''}{Math.round(effectiveZoom * 100)}%</span>
          <button type="button" onClick={() => setZoom((value) => Math.min(1.2, value + 0.1))} disabled={compact} aria-label="Zoom in"><Plus size={15} /></button>
          <button type="button" onClick={() => setZoom(0.76)} disabled={compact} aria-label="Fit page"><Maximize2 size={15} /></button>
        </div>
      </div>
      <div ref={stageRef} className="quotation-page-stage">
        {visiblePages.map((page) => (
          <div className="quotation-page-scale" style={{ '--quotation-zoom': effectiveZoom }} key={page.key}>
            <PageFrame document={document} pageNumber={pages.indexOf(page) + 1} pageCount={pages.length} className={page.className}>
              {page.content}
            </PageFrame>
          </div>
        ))}
      </div>
    </section>
  );
}
