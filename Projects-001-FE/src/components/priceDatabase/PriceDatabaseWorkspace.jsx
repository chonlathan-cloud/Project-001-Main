import React, { useCallback, useEffect, useState } from 'react';
import { Archive, BookOpen, ChevronLeft, ChevronRight, RefreshCw, Search } from 'lucide-react';

import { canAccessOwnerArea, getStoredAuthUser } from '../../auth';
import {
  getPriceDatabaseItem,
  getPriceDatabaseItems,
  updatePriceDatabaseReference,
} from '../../api';
import './priceDatabase.css';

const money = (value) => value == null
  ? '—'
  : new Intl.NumberFormat('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(Number(value));

const messageOf = (error) => error?.message || error?.detail || 'Could not complete the request.';

export default function PriceDatabaseWorkspace() {
  const canEdit = canAccessOwnerArea(getStoredAuthUser());
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('ACTIVE');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: 25 });
  const [selectedId, setSelectedId] = useState('');
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reference, setReference] = useState({
    project_id: '', price_kind: 'MATERIAL_COST', amount: '', tax_basis: 'EXCLUSIVE_VAT', reason: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getPriceDatabaseItems({ query, status, page, pageSize: 25 });
      setResult(data);
      if (!selectedId && data.items?.[0]) setSelectedId(data.items[0].id);
    } catch (requestError) {
      setError(messageOf(requestError));
    } finally {
      setLoading(false);
    }
  }, [page, query, selectedId, status]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let active = true;
    getPriceDatabaseItem(selectedId)
      .then((data) => { if (active) setDetail(data); })
      .catch((requestError) => { if (active) setError(messageOf(requestError)); });
    return () => { active = false; };
  }, [selectedId]);

  const submitReference = async (event) => {
    event.preventDefault();
    if (!detail || !canEdit) return;
    setBusy(true);
    setError('');
    try {
      await updatePriceDatabaseReference(detail.item.id, {
        ...reference,
        expected_item_version: detail.item.version,
        effective_date: new Date().toISOString().slice(0, 10),
      });
      setReference((current) => ({ ...current, amount: '', reason: '' }));
      setDetail(await getPriceDatabaseItem(detail.item.id));
      await load();
    } catch (requestError) {
      setError(messageOf(requestError));
    } finally {
      setBusy(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil((result.total || 0) / 25));

  return (
    <div className="price-db-workspace">
      <header className="price-db-header">
        <div>
          <span className="price-db-eyebrow">INTERNAL REFERENCE LIBRARY</span>
          <h1>Price Database</h1>
          <p>Versioned reference prices with project and event provenance. Nothing updates a BOQ automatically.</p>
        </div>
        <button type="button" className="price-db-button secondary" onClick={load} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </header>

      {!canEdit ? (
        <div className="price-db-notice">Admin access is read-only. Catalog promotion and reference updates require an Owner.</div>
      ) : null}
      {error ? <div className="price-db-error" role="alert">{error}</div> : null}

      <section className="price-db-toolbar" aria-label="Price database filters">
        <label className="price-db-search">
          <Search size={17} />
          <span className="sr-only">Search catalog</span>
          <input
            value={query}
            onChange={(event) => { setQuery(event.target.value); setPage(1); }}
            placeholder="Search code, item or specification"
          />
        </label>
        <label>
          <span>Status</span>
          <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
            <option value="ACTIVE">Active</option>
            <option value="ARCHIVED">Archived</option>
          </select>
        </label>
      </section>

      <div className="price-db-grid">
        <section className="price-db-list" aria-label="Catalog items">
          <div className="price-db-list-heading">
            <strong>{result.total || 0} items</strong>
            <span>Page {page} of {totalPages}</span>
          </div>
          {loading ? <div className="price-db-empty">Loading catalog…</div> : null}
          {!loading && !result.items?.length ? (
            <div className="price-db-empty"><BookOpen size={22} />No catalog items match these filters.</div>
          ) : null}
          {result.items?.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`price-db-row${selectedId === item.id ? ' selected' : ''}`}
              onClick={() => setSelectedId(item.id)}
            >
              <span><strong>{item.code}</strong><small>{item.category || 'Uncategorized'}</small></span>
              <span><b>{item.name}</b><small>{item.unit} · {item.distinct_sample_count} distinct samples</small></span>
              <span className={`price-db-status ${item.status.toLowerCase()}`}>
                {item.status === 'ARCHIVED' ? <Archive size={13} /> : null}{item.status}
              </span>
            </button>
          ))}
          <div className="price-db-pagination">
            <button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1} aria-label="Previous page"><ChevronLeft size={17} /></button>
            <button type="button" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={page >= totalPages} aria-label="Next page"><ChevronRight size={17} /></button>
          </div>
        </section>

        <aside className="price-db-detail" aria-label="Catalog price history">
          {!detail ? <div className="price-db-empty">Select an item to inspect its history.</div> : (
            <>
              <div className="price-db-detail-title">
                <span>{detail.item.code} · v{detail.item.version}</span>
                <h2>{detail.item.name}</h2>
                <p>{detail.item.specification || 'No specification'} · {detail.item.unit}</p>
              </div>
              <div className="price-db-reference-table">
                <h3>Current references</h3>
                {detail.item.current_prices.length ? detail.item.current_prices.map((price) => (
                  <div key={price.id}><span>{price.price_kind}</span><strong>{money(price.amount)} THB</strong><small>{price.tax_basis} · v{price.version}</small></div>
                )) : <p>No reference price has been promoted.</p>}
              </div>
              <div className="price-db-history">
                <h3>Business-event observations</h3>
                <p>{detail.distinct_sample_count} distinct samples · {detail.observations.length} recorded events</p>
                {detail.observations.slice(0, 12).map((row) => (
                  <div className="price-db-history-row" key={row.id}>
                    <span><b>{row.observation_kind}</b><small>{row.source_event_type} · project {row.project_id.slice(0, 8)} · {row.observed_at.slice(0, 10)}</small></span>
                    <span><strong>{money(row.unit_rate)}</strong><small>{row.quantity || '—'} {row.unit || ''}</small></span>
                  </div>
                ))}
              </div>
              {canEdit ? (
                <form className="price-db-reference-form" onSubmit={submitReference}>
                  <h3>Explicit reference update</h3>
                  <label>Project ID<input required value={reference.project_id} onChange={(event) => setReference({ ...reference, project_id: event.target.value })} /></label>
                  <label>Price dimension<select value={reference.price_kind} onChange={(event) => setReference({ ...reference, price_kind: event.target.value })}><option>MATERIAL_COST</option><option>LABOR_COST</option><option>MATERIAL_SELL</option><option>LABOR_SELL</option></select></label>
                  <label>Reference rate<input required min="0" step="0.0001" type="number" value={reference.amount} onChange={(event) => setReference({ ...reference, amount: event.target.value })} /></label>
                  <label>Tax basis<select value={reference.tax_basis} onChange={(event) => setReference({ ...reference, tax_basis: event.target.value })}><option>EXCLUSIVE_VAT</option><option>INCLUSIVE_VAT</option><option>NO_VAT</option><option>UNKNOWN</option></select></label>
                  <label>Reason<textarea required rows="2" value={reference.reason} onChange={(event) => setReference({ ...reference, reason: event.target.value })} /></label>
                  <button className="price-db-button primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Create new reference version'}</button>
                </form>
              ) : null}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
