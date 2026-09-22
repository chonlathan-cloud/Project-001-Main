import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, FileText, RefreshCw, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

import { getNativeBoqQuotations } from '../../api';
import { BOQ_V2_ENABLED } from '../../config/features';
import Loading from '../Loading';
import './quotation.css';

const PAGE_SIZE = 25;

function formatMoney(value) {
  return new Intl.NumberFormat('th-TH', {
    style: 'currency',
    currency: 'THB',
    minimumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('th-TH', { dateStyle: 'medium' }).format(date);
}

function errorMessage(error) {
  return error?.payload?.detail?.message || error?.message || 'Unable to load quotations.';
}

export default function QuotationCenter() {
  const [filters, setFilters] = useState({ search: '', status: '', documentKind: '', dateFrom: '', dateTo: '' });
  const [applied, setApplied] = useState(filters);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await getNativeBoqQuotations({ ...applied, limit: PAGE_SIZE, offset }));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [applied, offset]);

  useEffect(() => { load(); }, [load]);

  const submit = (event) => {
    event.preventDefault();
    setOffset(0);
    setApplied({ ...filters });
  };

  if (!BOQ_V2_ENABLED) {
    return <section className="boq-empty-state"><h2>Quotation Center is disabled</h2></section>;
  }

  return (
    <main className="quotation-center-page">
      <header className="quotation-center-header">
        <div>
          <span className="boq-eyebrow">QUOTATION CENTER</span>
          <h1>ใบเสนอราคา <small>Quotations</small></h1>
          <p>ค้นหา เปิด และติดตามเอกสารจากทุกโครงการ</p>
        </div>
        <span className="quotation-result-count">{result?.total || 0} documents</span>
      </header>

      <form className="quotation-center-filters" onSubmit={submit}>
        <label className="quotation-search-field">
          <span>Search</span>
          <div><Search size={16} /><input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="เลขที่เอกสาร โครงการ หรือลูกค้า" /></div>
        </label>
        <label><span>Status</span><select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All statuses</option><option>DRAFT</option><option>ISSUED</option><option>ACCEPTED</option><option>REJECTED</option><option>WITHDRAWN</option><option>SUPERSEDED</option></select></label>
        <label><span>Document kind</span><select value={filters.documentKind} onChange={(event) => setFilters({ ...filters, documentKind: event.target.value })}><option value="">All kinds</option><option value="MAIN">Main</option><option value="ALTERNATIVE">Alternative</option><option value="CHANGE_ORDER">Change order</option></select></label>
        <label><span>From</span><input type="date" value={filters.dateFrom} onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })} /></label>
        <label><span>To</span><input type="date" value={filters.dateTo} onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })} /></label>
        <button type="submit" className="boq-button boq-button-primary">Apply filters</button>
      </form>

      {error ? (
        <section className="boq-notice boq-notice-danger" role="alert">
          <FileText size={18} /><div><strong>Quotation list unavailable</strong><p>{errorMessage(error)}</p></div>
          <button type="button" className="boq-button boq-button-secondary" onClick={load}><RefreshCw size={15} /> Retry</button>
        </section>
      ) : null}

      {loading && !result ? <Loading /> : (
        <section className="quotation-center-table-shell" aria-busy={loading}>
          <table className="quotation-center-table">
            <thead><tr><th>Quotation</th><th>Project / Customer</th><th>Kind</th><th>Revision</th><th>Status</th><th>Date</th><th>Total</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {(result?.items || []).map((item) => (
                <tr key={item.document_id}>
                  <td><strong>{item.document_number}</strong><span>{item.quotation_title || 'Untitled quotation'}</span></td>
                  <td><strong>{item.project_name}</strong><span>{item.customer_name || 'No customer'}</span></td>
                  <td>{item.document_kind}{item.direction ? ` · ${item.direction}` : ''}</td>
                  <td>R{item.revision_number} <small>v{item.version}</small></td>
                  <td><span className={`quotation-status quotation-status-${String(item.status).toLowerCase()}`}>{item.status}</span></td>
                  <td>{formatDate(item.quotation_date || item.updated_at)}</td>
                  <td className="quotation-number">{formatMoney(item.grand_total)}</td>
                  <td><Link className="quotation-open-link" to={`/quotations/${item.document_id}?revision_id=${item.revision_id}`}>Open <ArrowRight size={14} /></Link></td>
                </tr>
              ))}
              {!loading && !(result?.items || []).length ? <tr><td colSpan="8" className="quotation-empty-cell">No quotations match these filters.</td></tr> : null}
            </tbody>
          </table>
        </section>
      )}

      <footer className="quotation-pagination">
        <span>{result?.total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, result.total)} of ${result.total}` : '0 results'}</span>
        <div>
          <button type="button" onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))} disabled={offset === 0 || loading}><ArrowLeft size={15} /> Previous</button>
          <button type="button" onClick={() => setOffset((current) => current + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= (result?.total || 0) || loading}>Next <ArrowRight size={15} /></button>
        </div>
      </footer>
    </main>
  );
}
