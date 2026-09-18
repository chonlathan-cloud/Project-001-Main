import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  Plus,
  RefreshCw,
  Store,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  createProjectVendor,
  createProjectVendorOffer,
  exportNativeBoqQuotation,
  getNativeBoqExportDownload,
  getProjectCostPlan,
  getProjectCostSelections,
  getProjectVendorOffers,
  getProjectVendors,
  getPriceDatabaseItems,
  openProjectWorkingCostPlan,
  publishProjectCostPlan,
  promotePriceDatabaseItem,
  reusePriceDatabaseItem,
  selectProjectVendorOffer,
} from '../../api';

const currency = new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' });
const money = (value) => value == null || value === '' ? '—' : currency.format(Number(value));
const errorText = (error) => error?.message || error?.detail || 'Could not complete the request.';

function componentLabel(node, component) {
  return `${node.item_code || node.description || 'Item'} · ${component.component_type}`;
}

export default function BoqVendorCostPanel({ projectId, revision, workspace, dirty, onPublished }) {
  const [open, setOpen] = useState(false);
  const [vendors, setVendors] = useState([]);
  const [offers, setOffers] = useState([]);
  const [selections, setSelections] = useState([]);
  const [costPlan, setCostPlan] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [vendorName, setVendorName] = useState('');
  const [publishReason, setPublishReason] = useState('');
  const [vendorExport, setVendorExport] = useState({
    audience: 'RFQ', vendor_id: '', component_id: '', file_format: 'XLSX',
  });
  const itemNodes = useMemo(() => revision.nodes.filter((node) => node.node_kind === 'ITEM'), [revision.nodes]);
  const [promotion, setPromotion] = useState({ node_id: '', code: '', name: '', unit: '', reason: '' });
  const [reuse, setReuse] = useState({ item_id: '', parent_logical_id: '', quantity: '1.0000' });
  const components = useMemo(
    () => revision.nodes.flatMap((node) => (node.components || []).map((component) => ({ node, component }))),
    [revision.nodes],
  );
  const [offer, setOffer] = useState({
    vendor_id: '', component_id: '', offered_quantity: '', unit: '', specification: '',
    unit_rate: '', quotation_reference: '', quotation_date: new Date().toISOString().slice(0, 10),
    valid_until: '', tax_basis: 'EXCLUSIVE_VAT', tax_rate: '7.0000',
    included_charges: '', discount_amount: '0', charges_amount: '0', notes: '',
  });

  const load = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    setError('');
    const [vendorResult, offerResult, selectionResult, planResult, catalogResult] = await Promise.allSettled([
      getProjectVendors(projectId),
      getProjectVendorOffers(projectId, revision.revision_id),
      getProjectCostSelections(projectId),
      getProjectCostPlan(projectId),
      getPriceDatabaseItems({ status: 'ACTIVE', pageSize: 100 }),
    ]);
    if (vendorResult.status === 'fulfilled') setVendors(vendorResult.value);
    if (offerResult.status === 'fulfilled') setOffers(offerResult.value);
    if (selectionResult.status === 'fulfilled') setSelections(selectionResult.value);
    if (planResult.status === 'fulfilled') setCostPlan(planResult.value);
    else setCostPlan(null);
    if (catalogResult.status === 'fulfilled') setCatalog(catalogResult.value.items || []);
    const failed = [vendorResult, offerResult, selectionResult].find((result) => result.status === 'rejected');
    if (failed) setError(errorText(failed.reason));
    setLoading(false);
  }, [open, projectId, revision.revision_id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const selected = components.find(({ component }) => component.id === offer.component_id);
    if (!selected) return;
    setOffer((current) => ({
      ...current,
      offered_quantity: selected.component.quantity,
      unit: selected.component.unit || selected.node.unit || '',
      specification: selected.component.specification || selected.node.specification || '',
    }));
  }, [components, offer.component_id]);

  const run = async (action) => {
    setBusy(true);
    setError('');
    try {
      await action();
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  };

  const addVendor = (event) => {
    event.preventDefault();
    if (!vendorName.trim()) return;
    run(async () => {
      const created = await createProjectVendor(projectId, { display_name: vendorName.trim() });
      setVendorName('');
      setOffer((current) => ({ ...current, vendor_id: created.id }));
    });
  };

  const addOffer = (event) => {
    event.preventDefault();
    const selected = components.find(({ component }) => component.id === offer.component_id);
    if (!selected || dirty) return;
    run(async () => {
      await createProjectVendorOffer(projectId, revision.revision_id, {
        vendor_id: offer.vendor_id,
        quotation_reference: offer.quotation_reference || null,
        quotation_date: offer.quotation_date,
        valid_until: offer.valid_until || null,
        currency: 'THB',
        tax_basis: offer.tax_basis,
        tax_rate: ['EXCLUSIVE_VAT', 'INCLUSIVE_VAT'].includes(offer.tax_basis) ? offer.tax_rate : null,
        discount_type: 'NONE', discount_value: '0', included_charges: offer.included_charges || null,
        charges_amount: offer.charges_amount || '0', notes: offer.notes || null,
        lines: [{
          component_id: selected.component.id,
          component_type: selected.component.component_type,
          offered_quantity: offer.offered_quantity,
          unit: offer.unit || null,
          specification: offer.specification || null,
          unit_rate: offer.unit_rate,
          discount_amount: offer.discount_amount || '0',
          charges_amount: offer.charges_amount || '0',
        }],
      });
      setOffer((current) => ({ ...current, unit_rate: '', quotation_reference: '', notes: '' }));
    });
  };

  const selectLine = (line, warnings) => {
    const reason = warnings.length
      ? window.prompt(`This offer has warnings (${warnings.join(', ')}). Record the reason for selecting it:`)
      : '';
    if (warnings.length && !reason?.trim()) return;
    run(() => selectProjectVendorOffer(projectId, {
      offer_line_id: line.id,
      expected_cost_plan_version: costPlan.expected_version,
      acknowledge_warning: warnings.length > 0,
      reason: reason || null,
    }));
  };

  const openWorking = () => run(async () => { setCostPlan(await openProjectWorkingCostPlan(projectId)); });

  const publish = () => {
    if (!costPlan || !publishReason.trim()) return;
    run(async () => {
      const result = await publishProjectCostPlan(projectId, {
        expected_version: costPlan.expected_version,
        expected_baseline_version: workspace.active_baseline_version,
        reason: publishReason.trim(),
      });
      setPublishReason('');
      onPublished?.(result);
    });
  };

  const promoteItem = (event) => {
    event.preventDefault();
    const node = itemNodes.find((item) => item.id === promotion.node_id);
    if (!node || dirty) return;
    run(async () => {
      await promotePriceDatabaseItem({
        source_node_id: node.id,
        observation_id: null,
        code: promotion.code || node.item_code,
        name: promotion.name || node.description,
        specification: node.specification || null,
        unit: promotion.unit || node.unit,
        category: null,
        tags: [],
        reason: promotion.reason,
      });
      setPromotion({ node_id: '', code: '', name: '', unit: '', reason: '' });
    });
  };

  const reuseItem = (event) => {
    event.preventDefault();
    if (!reuse.item_id || dirty || revision.status !== 'DRAFT') return;
    run(async () => {
      await reusePriceDatabaseItem(reuse.item_id, revision.revision_id, {
        expected_revision_version: revision.version,
        parent_logical_id: reuse.parent_logical_id || null,
        position: revision.nodes.filter((node) => (node.parent_logical_id || '') === reuse.parent_logical_id).length,
        quantity: reuse.quantity,
        inclusion_state: 'REQUIRED',
        use_reference_prices: true,
      });
      onPublished?.();
    });
  };

  const exportVendorScope = (event) => {
    event.preventDefault();
    if (!revision.issued_snapshot_id || !vendorExport.vendor_id) return;
    if (vendorExport.audience === 'RFQ' && !vendorExport.component_id) return;
    run(async () => {
      const artifact = await exportNativeBoqQuotation(revision.revision_id, {
        snapshot_id: revision.issued_snapshot_id,
        audience: vendorExport.audience,
        file_format: vendorExport.file_format,
        vendor_id: vendorExport.vendor_id,
        selected_component_ids: vendorExport.component_id ? [vendorExport.component_id] : [],
        ...(vendorExport.audience === 'VENDOR' && costPlan?.status === 'PUBLISHED'
          ? { cost_plan_version: costPlan.version }
          : {}),
      });
      const download = await getNativeBoqExportDownload(
        revision.revision_id,
        artifact.artifact_id,
      );
      window.location.assign(download.download_url);
    });
  };

  const selectedLineIds = new Set(selections.filter((row) => row.current).map((row) => row.offer_line_id));

  return (
    <section className="boq-vendor-panel">
      <button type="button" className="boq-vendor-panel-toggle" onClick={() => setOpen((current) => !current)} aria-expanded={open}>
        <span><Store size={18} /><b>Vendor cost & working plan</b><small>Offers stay internal and do not affect Funds until explicit publish.</small></span>
        {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>
      {open ? (
        <div className="boq-vendor-panel-body">
          <div className="boq-vendor-panel-heading">
            <div>
              <span className="boq-eyebrow">INTERNAL COST WORKSPACE</span>
              <h3>Compare on explicit quantity, unit, specification and tax basis</h3>
            </div>
            <div className="boq-vendor-panel-actions">
              <Link className="boq-button boq-button-secondary" to="/price-database">Price Database</Link>
              <button type="button" className="boq-button boq-button-secondary" onClick={load} disabled={busy || loading}><RefreshCw size={15} />Refresh</button>
            </div>
          </div>
          {error ? <div className="boq-notice boq-notice-danger" role="alert">{error}</div> : null}
          {dirty ? <div className="boq-notice boq-notice-warning"><AlertTriangle size={18} /><div><strong>Save the BOQ first</strong><p>Offer mapping always targets the acknowledged server component version.</p></div></div> : null}
          {!workspace.can_edit ? <div className="boq-notice"><div><strong>Read-only cost workspace</strong><p>Admins can compare offers and inspect provenance; Owner authorization is required to change or publish cost.</p></div></div> : null}

          <div className="boq-cost-plan-strip">
            <div><span>Plan</span><strong>{costPlan ? `v${costPlan.version} · ${costPlan.status}` : 'Not opened'}</strong></div>
            <div><span>Original estimate</span><strong>{money(costPlan?.original_estimated_cost)}</strong></div>
            <div><span>Agreed cost</span><strong>{money(costPlan?.agreed_cost)}</strong></div>
            <div><span>Candidate forecast</span><strong>{money(costPlan?.forecast_cost)}</strong><small>{costPlan?.completeness_state || 'UNKNOWN'}</small></div>
            {workspace.can_edit && workspace.active_baseline_id && (!costPlan || costPlan.source_baseline_id !== workspace.active_baseline_id) ? (
              <button type="button" className="boq-button boq-button-primary" onClick={openWorking} disabled={busy}>Open working plan</button>
            ) : null}
          </div>

          {workspace.can_edit ? (
            <div className="boq-vendor-entry-grid">
              <form onSubmit={addVendor}>
                <h4>Add commercial vendor</h4>
                <label>Vendor name<input required value={vendorName} onChange={(event) => setVendorName(event.target.value)} placeholder="Company or commercial reference" /></label>
                <button className="boq-button boq-button-secondary" disabled={busy}><Plus size={15} />Add vendor</button>
              </form>
              <form onSubmit={addOffer}>
                <h4>Record vendor offer</h4>
                <div className="boq-vendor-form-grid">
                  <label>Vendor<select required value={offer.vendor_id} onChange={(event) => setOffer({ ...offer, vendor_id: event.target.value })}><option value="">Select vendor</option>{vendors.filter((vendor) => vendor.status === 'ACTIVE').map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.display_name}</option>)}</select></label>
                  <label>Cost component<select required value={offer.component_id} onChange={(event) => setOffer({ ...offer, component_id: event.target.value })}><option value="">Select component</option>{components.map(({ node, component }) => <option key={component.id} value={component.id}>{componentLabel(node, component)}</option>)}</select></label>
                  <label>Quotation ref<input value={offer.quotation_reference} onChange={(event) => setOffer({ ...offer, quotation_reference: event.target.value })} /></label>
                  <label>Quotation date<input required type="date" value={offer.quotation_date} onChange={(event) => setOffer({ ...offer, quotation_date: event.target.value })} /></label>
                  <label>Valid until<input type="date" value={offer.valid_until} onChange={(event) => setOffer({ ...offer, valid_until: event.target.value })} /></label>
                  <label>Offered quantity<input required min="0.0001" step="0.0001" type="number" value={offer.offered_quantity} onChange={(event) => setOffer({ ...offer, offered_quantity: event.target.value })} /></label>
                  <label>Unit<input value={offer.unit} onChange={(event) => setOffer({ ...offer, unit: event.target.value })} /></label>
                  <label>Unit rate<input required min="0" step="0.0001" type="number" value={offer.unit_rate} onChange={(event) => setOffer({ ...offer, unit_rate: event.target.value })} /></label>
                  <label>Tax basis<select value={offer.tax_basis} onChange={(event) => setOffer({ ...offer, tax_basis: event.target.value })}><option>EXCLUSIVE_VAT</option><option>INCLUSIVE_VAT</option><option>NO_VAT</option><option>UNKNOWN</option></select></label>
                  <label>Tax rate<input disabled={!['EXCLUSIVE_VAT', 'INCLUSIVE_VAT'].includes(offer.tax_basis)} min="0" step="0.0001" type="number" value={offer.tax_rate} onChange={(event) => setOffer({ ...offer, tax_rate: event.target.value })} /></label>
                  <label className="wide">Specification<textarea rows="2" value={offer.specification} onChange={(event) => setOffer({ ...offer, specification: event.target.value })} /></label>
                  <label>Line discount<input min="0" step="0.01" type="number" value={offer.discount_amount} onChange={(event) => setOffer({ ...offer, discount_amount: event.target.value })} /></label>
                  <label>Included charges<input value={offer.included_charges} onChange={(event) => setOffer({ ...offer, included_charges: event.target.value })} /></label>
                </div>
                <button className="boq-button boq-button-primary" disabled={busy || dirty || !vendors.length}>Record offer</button>
              </form>
            </div>
          ) : null}

          {workspace.can_edit ? (
            <div className="boq-catalog-actions">
              <form onSubmit={promoteItem}>
                <h4>Save as standard item</h4>
                <label>Saved BOQ item<select required value={promotion.node_id} onChange={(event) => {
                  const node = itemNodes.find((item) => item.id === event.target.value);
                  setPromotion({ ...promotion, node_id: event.target.value, code: node?.item_code || '', name: node?.description || '', unit: node?.unit || '' });
                }}><option value="">Select item</option>{itemNodes.map((node) => <option key={node.id} value={node.id}>{node.item_code || node.description}</option>)}</select></label>
                <label>Catalog code<input required value={promotion.code} onChange={(event) => setPromotion({ ...promotion, code: event.target.value })} /></label>
                <label>Catalog name<input required value={promotion.name} onChange={(event) => setPromotion({ ...promotion, name: event.target.value })} /></label>
                <label>Unit<input required value={promotion.unit} onChange={(event) => setPromotion({ ...promotion, unit: event.target.value })} /></label>
                <label>Promotion reason<input required value={promotion.reason} onChange={(event) => setPromotion({ ...promotion, reason: event.target.value })} /></label>
                <button className="boq-button boq-button-secondary" disabled={busy || dirty}>Promote explicitly</button>
              </form>
              <form onSubmit={reuseItem}>
                <h4>Reuse from Price Database</h4>
                <label>Catalog item<select required value={reuse.item_id} onChange={(event) => setReuse({ ...reuse, item_id: event.target.value })}><option value="">Select standard item</option>{catalog.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label>
                <label>Parent section<select value={reuse.parent_logical_id} onChange={(event) => setReuse({ ...reuse, parent_logical_id: event.target.value })}><option value="">Root</option>{revision.nodes.filter((node) => node.node_kind !== 'ITEM').map((node) => <option key={node.logical_id} value={node.logical_id}>{node.display_path || node.description}</option>)}</select></label>
                <label>Quantity<input required min="0.0001" step="0.0001" type="number" value={reuse.quantity} onChange={(event) => setReuse({ ...reuse, quantity: event.target.value })} /></label>
                <p>Reference values are copied as a snapshot; later catalog updates do not cascade.</p>
                <button className="boq-button boq-button-secondary" disabled={busy || dirty || revision.status !== 'DRAFT'}>Reuse into draft</button>
              </form>
            </div>
          ) : null}

          <form className="boq-vendor-export" onSubmit={exportVendorScope}>
            <div>
              <h4>Vendor-safe export</h4>
              <p>RFQ leaves price cells blank. Selected-vendor files include only confirmed costs for that vendor.</p>
            </div>
            <label>Audience<select value={vendorExport.audience} onChange={(event) => setVendorExport({ ...vendorExport, audience: event.target.value })}><option value="RFQ">RFQ</option><option value="VENDOR">Selected vendor cost</option></select></label>
            <label>Vendor<select required value={vendorExport.vendor_id} onChange={(event) => setVendorExport({ ...vendorExport, vendor_id: event.target.value })}><option value="">Select vendor</option>{vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.display_name}</option>)}</select></label>
            <label>Component<select required={vendorExport.audience === 'RFQ'} value={vendorExport.component_id} onChange={(event) => setVendorExport({ ...vendorExport, component_id: event.target.value })}><option value="">{vendorExport.audience === 'RFQ' ? 'Select component' : 'All confirmed for vendor'}</option>{components.map(({ node, component }) => <option key={component.id} value={component.id}>{componentLabel(node, component)}</option>)}</select></label>
            <label>Format<select value={vendorExport.file_format} onChange={(event) => setVendorExport({ ...vendorExport, file_format: event.target.value })}><option value="XLSX">Excel</option><option value="PDF">PDF</option></select></label>
            <button className="boq-button boq-button-secondary" disabled={busy || !revision.issued_snapshot_id || !vendorExport.vendor_id || (vendorExport.audience === 'RFQ' && !vendorExport.component_id)}><Download size={15} />Export</button>
          </form>

          <div className="boq-offer-table-shell">
            <table className="boq-offer-table">
              <thead><tr><th>Vendor / reference</th><th>Component basis</th><th>Coverage</th><th>Tax / charges</th><th>Comparison</th><th>Selection</th></tr></thead>
              <tbody>
                {offers.flatMap((entry) => entry.lines.map((line) => {
                  const warnings = [
                    ...(entry.expired ? ['EXPIRED'] : []),
                    ...(line.comparison_state !== 'EQUIVALENT' ? [line.comparison_state] : []),
                    ...(entry.tax_basis === 'UNKNOWN' ? ['UNKNOWN_TAX'] : []),
                  ];
                  return (
                    <tr key={line.id}>
                      <td><strong>{entry.vendor.display_name}</strong><small>{entry.quotation_reference || 'No reference'} · {entry.quotation_date}{entry.valid_until ? ` → ${entry.valid_until}` : ''}</small></td>
                      <td><strong>{line.component_type}</strong><small>{line.required_quantity} {line.required_unit || '—'} required / {line.offered_quantity} {line.offered_unit || '—'} offered</small><small>{line.offered_specification || 'No specification'}</small></td>
                      <td><span className={`boq-offer-badge ${line.coverage_state.toLowerCase()}`}>{line.coverage_state}</span></td>
                      <td><strong>{entry.tax_basis}</strong><small>{entry.included_charges || 'No included-charge note'}</small></td>
                      <td><strong>{line.normalized_total_ex_vat ? money(line.normalized_total_ex_vat) : 'Not safely normalized'}</strong><small>{warnings.length ? warnings.join(' · ') : 'Equivalent basis'}</small></td>
                      <td>{selectedLineIds.has(line.id) ? <span className="boq-offer-selected"><CheckCircle2 size={15} />Selected</span> : workspace.can_edit ? <button type="button" className="boq-button boq-button-secondary" disabled={busy || !costPlan || line.coverage_state !== 'FULL'} onClick={() => selectLine(line, warnings)}>Select</button> : '—'}</td>
                    </tr>
                  );
                }))}
                {!offers.length ? <tr><td colSpan="6" className="boq-offer-empty">No vendor offers recorded for this revision.</td></tr> : null}
              </tbody>
            </table>
          </div>

          {workspace.can_edit && workspace.active_baseline_id && costPlan?.status === 'WORKING' && costPlan.source_baseline_id === workspace.active_baseline_id ? (
            <div className="boq-cost-publish">
              <div><strong>Publish operational cost plan</strong><p>This creates a new baseline/source version. Customer sell and actual-paid records remain unchanged.</p></div>
              <label>Required reason<textarea rows="2" value={publishReason} onChange={(event) => setPublishReason(event.target.value)} /></label>
              <button type="button" className="boq-button boq-button-primary" onClick={publish} disabled={busy || !publishReason.trim()}>Publish cost plan</button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
