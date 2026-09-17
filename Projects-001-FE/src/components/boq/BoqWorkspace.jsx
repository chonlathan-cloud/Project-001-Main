import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  ChevronRight,
  Clipboard,
  Copy,
  FileClock,
  FolderPlus,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  WifiOff,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  copyNativeBoqRevision,
  createBoqIdempotencyKey,
  createNativeBoqDocument,
  getNativeBoqRevision,
  getNativeBoqWorkspace,
  saveNativeBoqDraft,
} from '../../api';
import { BOQ_V2_ENABLED } from '../../config/features';
import Loading from '../Loading';
import {
  addDraftNode,
  buildSavePayload,
  duplicateDraftItem,
  moveDraftNode,
  moveDraftNodeTo,
  normalizeSiblingPositions,
  parseRevisionDraft,
  removeDraftNode,
  updateDraftComponent,
  updateDraftNode,
} from './boqDraftState';
import './boqWorkspace.css';

const VIEW_MODES = [
  { value: 'consolidated', label: 'Consolidated' },
  { value: 'customer', label: 'Customer' },
  { value: 'cost', label: 'Cost' },
];

const NODE_LABELS = {
  SECTION: 'Section',
  CATEGORY: 'Category',
  SUBCATEGORY: 'Subcategory',
  ITEM: 'Item',
};

const currency = new Intl.NumberFormat('th-TH', {
  style: 'currency',
  currency: 'THB',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value) {
  if (value == null || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? currency.format(number) : '—';
}

function formatTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('th-TH', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function domainCode(error) {
  return error?.payload?.detail?.code || error?.code || 'BOQ_REQUEST_FAILED';
}

function domainMessage(error) {
  return error?.payload?.detail?.message || error?.detail || error?.message || 'BOQ request failed.';
}

function backupKey(revisionId) {
  return `projects001_boq_v2_draft_${revisionId}`;
}

function readBackup(revisionId) {
  if (!revisionId) return null;
  try {
    const stored = JSON.parse(window.localStorage.getItem(backupKey(revisionId)) || 'null');
    return Array.isArray(stored?.nodes) ? stored : null;
  } catch {
    return null;
  }
}

function clearBackup(revisionId) {
  try {
    window.localStorage.removeItem(backupKey(revisionId));
  } catch {
    // Saving still works when browser storage is unavailable.
  }
}

function childKinds(nodeKind) {
  if (nodeKind === 'SECTION') return ['CATEGORY'];
  if (nodeKind === 'CATEGORY') return ['SUBCATEGORY', 'ITEM'];
  if (nodeKind === 'SUBCATEGORY') return ['ITEM'];
  return [];
}

function RecoveryPanel({ recovery, onRestore, onDiscard }) {
  if (!recovery) return null;
  return (
    <section className="boq-notice boq-notice-warning" role="status">
      <FileClock size={18} aria-hidden="true" />
      <div>
        <strong>Unsaved browser recovery found</strong>
        <p>
          Saved locally {formatTimestamp(recovery.saved_at)} from server version {recovery.base_version}.
        </p>
      </div>
      <div className="boq-notice-actions">
        <button type="button" className="boq-button boq-button-secondary" onClick={onDiscard}>Discard</button>
        <button type="button" className="boq-button boq-button-primary" onClick={onRestore}>Restore draft</button>
      </div>
    </section>
  );
}

function ComponentEditor({ component, componentType, disabled, onChange }) {
  const current = component || {
    component_type: componentType,
    quantity_basis: 'INHERITED',
    quantity: null,
    unit: null,
    specification: null,
    cost_state: 'UNKNOWN',
    unit_rate: null,
    explicit_zero_reason: null,
  };
  const isOverride = current.quantity_basis === 'OVERRIDDEN';
  const isPriced = current.cost_state === 'PRICED';
  const isExplicitZero = isPriced && Number(current.unit_rate) === 0 && String(current.unit_rate ?? '').trim() !== '';

  return (
    <fieldset className="boq-component-editor" disabled={disabled}>
      <legend>{componentType === 'MATERIAL' ? 'Material' : 'Labor'}</legend>
      <div className="boq-inline-fields">
        <label>
          <span>Quantity basis</span>
          <select
            value={current.quantity_basis}
            onChange={(event) => onChange({
              quantity_basis: event.target.value,
              quantity: event.target.value === 'INHERITED' ? null : (current.quantity || ''),
            })}
          >
            <option value="INHERITED">Inherited</option>
            <option value="OVERRIDDEN">Override</option>
          </select>
        </label>
        {isOverride ? (
          <label>
            <span>Cost quantity</span>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={current.quantity ?? ''}
              onChange={(event) => onChange({ quantity: event.target.value })}
              required
            />
          </label>
        ) : null}
      </div>
      {isOverride ? (
        <div className="boq-inline-fields">
          <label>
            <span>Unit</span>
            <input value={current.unit || ''} onChange={(event) => onChange({ unit: event.target.value })} />
          </label>
          <label>
            <span>Specification</span>
            <input
              value={current.specification || ''}
              onChange={(event) => onChange({ specification: event.target.value })}
            />
          </label>
        </div>
      ) : null}
      <div className="boq-inline-fields">
        <label>
          <span>Cost state</span>
          <select
            value={current.cost_state}
            onChange={(event) => onChange({
              cost_state: event.target.value,
              unit_rate: event.target.value === 'PRICED' ? (current.unit_rate ?? '') : null,
              explicit_zero_reason: event.target.value === 'PRICED' ? current.explicit_zero_reason : null,
            })}
          >
            <option value="UNKNOWN">Unknown</option>
            <option value="PRICED">Priced</option>
            <option value="NOT_APPLICABLE">Not applicable</option>
          </select>
        </label>
        {isPriced ? (
          <label>
            <span>Unit cost</span>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={current.unit_rate ?? ''}
              onChange={(event) => onChange({ unit_rate: event.target.value })}
              required
            />
          </label>
        ) : (
          <div className={`boq-cost-state boq-cost-state-${current.cost_state.toLowerCase()}`}>
            {current.cost_state === 'UNKNOWN' ? 'Pending price' : 'Excluded from costing'}
          </div>
        )}
      </div>
      {isExplicitZero ? (
        <label>
          <span>Reason for explicit zero</span>
          <input
            value={current.explicit_zero_reason || ''}
            onChange={(event) => onChange({ explicit_zero_reason: event.target.value })}
            placeholder="e.g. Included at no additional cost"
            required
          />
        </label>
      ) : null}
      <small>Server total: {formatMoney(current.total)}</small>
    </fieldset>
  );
}

function ScopeRow({ node, nodes, viewMode, disabled, onNodesChange }) {
  const structural = node.node_kind !== 'ITEM';
  const candidateParents = nodes.filter((candidate) => (
    candidate.logical_id !== node.logical_id && candidate.node_kind !== 'ITEM'
  ));

  const update = (updates) => onNodesChange(updateDraftNode(nodes, node.logical_id, updates));
  const updateComponent = (type, updates) => (
    onNodesChange(updateDraftComponent(nodes, node.logical_id, type, updates))
  );
  const remove = () => {
    const descendantCount = nodes.filter((candidate) => candidate.parent_logical_id === node.logical_id).length;
    if (descendantCount > 0 && !window.confirm('Delete this group and all nested rows?')) return;
    onNodesChange(removeDraftNode(nodes, node.logical_id));
  };

  return (
    <tr className={`boq-scope-row boq-scope-${node.node_kind.toLowerCase()}`}>
      <td className="boq-scope-cell" data-label="Scope">
        <div className="boq-scope-indent" style={{ '--boq-depth': node.depth || 0 }}>
          <span className="boq-node-kind">{NODE_LABELS[node.node_kind]}</span>
          <div className="boq-scope-primary">
            {node.node_kind === 'ITEM' ? (
              <input
                className="boq-code-input"
                aria-label="Item code"
                value={node.item_code || ''}
                onChange={(event) => update({ item_code: event.target.value })}
                placeholder="Code"
                disabled={disabled}
              />
            ) : null}
            <input
              className="boq-description-input"
              aria-label={`${NODE_LABELS[node.node_kind]} description`}
              value={node.description || ''}
              onChange={(event) => update({ description: event.target.value })}
              placeholder={`${NODE_LABELS[node.node_kind]} description`}
              disabled={disabled}
            />
          </div>
          {node.node_kind === 'ITEM' ? (
            <>
              <input
                aria-label="Item specification"
                value={node.specification || ''}
                onChange={(event) => update({ specification: event.target.value })}
                placeholder="Specification"
                disabled={disabled}
              />
              <div className="boq-inline-fields boq-item-basics">
                <label>
                  <span>Quantity</span>
                  <input
                    type="number"
                    min="0"
                    step="0.0001"
                    value={node.quantity ?? ''}
                    onChange={(event) => update({ quantity: event.target.value })}
                    disabled={disabled}
                  />
                </label>
                <label>
                  <span>Unit</span>
                  <input value={node.unit || ''} onChange={(event) => update({ unit: event.target.value })} disabled={disabled} />
                </label>
              </div>
            </>
          ) : null}
          <label className="boq-inclusion-field">
            <span>Inclusion</span>
            <select value={node.inclusion_state} onChange={(event) => update({ inclusion_state: event.target.value })} disabled={disabled}>
              <option value="REQUIRED">Required</option>
              <option value="OPTIONAL">Optional</option>
              <option value="EXCLUDED">Excluded</option>
            </select>
          </label>
        </div>
      </td>
      {viewMode !== 'cost' ? (
        <td className="boq-customer-cell" data-label="Customer price">
          {structural ? <span className="boq-rollup-label">Server roll-up</span> : (
            <div className="boq-price-grid">
              <label>
                <span>Material / unit</span>
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={node.sell_material_unit_rate ?? ''}
                  onChange={(event) => update({ sell_material_unit_rate: event.target.value })}
                  disabled={disabled}
                />
              </label>
              <label>
                <span>Labor / unit</span>
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={node.sell_labor_unit_rate ?? ''}
                  onChange={(event) => update({ sell_labor_unit_rate: event.target.value })}
                  disabled={disabled}
                />
              </label>
            </div>
          )}
        </td>
      ) : null}
      {viewMode !== 'customer' ? (
        <td className="boq-cost-cell" data-label="Estimated cost">
          {structural ? <span className="boq-rollup-label">Server roll-up</span> : (
            <div className="boq-component-stack">
              {['MATERIAL', 'LABOR'].map((type) => (
                <ComponentEditor
                  key={type}
                  component={node.components?.find((component) => component.component_type === type)}
                  componentType={type}
                  disabled={disabled}
                  onChange={(updates) => updateComponent(type, updates)}
                />
              ))}
            </div>
          )}
        </td>
      ) : null}
      <td className="boq-total-cell" data-label="Server total">
        <strong>{formatMoney(node.sell_total)}</strong>
        <span>Customer total</span>
      </td>
      <td className="boq-row-actions" data-label="Actions">
        {!disabled ? (
          <>
            <div className="boq-icon-actions">
              <button type="button" onClick={() => onNodesChange(moveDraftNode(nodes, node.logical_id, 'up'))} aria-label="Move row up"><ArrowUp size={15} /></button>
              <button type="button" onClick={() => onNodesChange(moveDraftNode(nodes, node.logical_id, 'down'))} aria-label="Move row down"><ArrowDown size={15} /></button>
              {node.node_kind === 'ITEM' ? (
                <button type="button" onClick={() => onNodesChange(duplicateDraftItem(nodes, node.logical_id))} aria-label="Duplicate item"><Copy size={15} /></button>
              ) : null}
              <button type="button" className="danger" onClick={remove} aria-label="Delete row"><Trash2 size={15} /></button>
            </div>
            <label>
              <span>Move to</span>
              <select
                value={node.parent_logical_id || ''}
                onChange={(event) => onNodesChange(moveDraftNodeTo(nodes, node.logical_id, event.target.value || null))}
              >
                <option value="">Top level</option>
                {candidateParents.map((candidate) => (
                  <option key={candidate.logical_id} value={candidate.logical_id}>
                    {candidate.display_path || candidate.description || NODE_LABELS[candidate.node_kind]}
                  </option>
                ))}
              </select>
            </label>
            {structural ? (
              <div className="boq-child-actions">
                {childKinds(node.node_kind).map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => onNodesChange(addDraftNode(nodes, kind, node.logical_id))}
                  >
                    <Plus size={13} /> {NODE_LABELS[kind]}
                  </button>
                ))}
              </div>
            ) : null}
          </>
        ) : <span className="boq-readonly-label">Read only</span>}
      </td>
    </tr>
  );
}

function EmptyWorkspace({ workspace, busy, copySource, onCopySource, onCreate, onCopy }) {
  return (
    <section className="boq-empty-state">
      <FolderPlus size={34} aria-hidden="true" />
      <div>
        <h2>Start the native BOQ</h2>
        <p>Create a blank MAIN draft or reuse an existing project revision. Drafts do not affect the operational budget.</p>
      </div>
      {workspace.can_edit ? (
        <div className="boq-empty-actions">
          <button type="button" className="boq-button boq-button-primary" onClick={onCreate} disabled={busy}>
            <Plus size={16} /> Create blank draft
          </button>
          {workspace.reuse_sources.length ? (
            <div className="boq-copy-control">
              <select value={copySource} onChange={(event) => onCopySource(event.target.value)} aria-label="BOQ revision to copy">
                {workspace.reuse_sources.map((source) => (
                  <option key={source.revision_id} value={source.revision_id}>
                    {source.project_name} · R{source.revision_number} · {formatMoney(source.net_sell_ex_vat)}
                  </option>
                ))}
              </select>
              <button type="button" className="boq-button boq-button-secondary" onClick={onCopy} disabled={busy || !copySource}>
                <Copy size={16} /> Reuse revision
              </button>
            </div>
          ) : null}
        </div>
      ) : <p className="boq-readonly-copy">Only an Owner can create or copy a BOQ draft.</p>}
    </section>
  );
}

export default function BoqWorkspace() {
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const query = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const requestedRevisionId = query.get('revision') || '';
  const [workspace, setWorkspace] = useState(null);
  const [revision, setRevision] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [viewMode, setViewMode] = useState('consolidated');
  const [copySource, setCopySource] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [recovery, setRecovery] = useState(null);
  const [online, setOnline] = useState(() => navigator.onLine);
  const pendingSaveRef = useRef(null);

  const selectRevision = useCallback((nextRevision) => {
    setRevision(nextRevision);
    setNodes(parseRevisionDraft(nextRevision));
    setDirty(false);
    setSaveError(null);
    pendingSaveRef.current = null;
    const stored = readBackup(nextRevision.revision_id);
    setRecovery(stored);
  }, []);

  const loadWorkspace = useCallback(async ({ preferredRevisionId = '' } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const nextWorkspace = await getNativeBoqWorkspace(projectId);
      setWorkspace(nextWorkspace);
      const selectedId = preferredRevisionId
        || requestedRevisionId
        || nextWorkspace.revisions[0]?.revision_id
        || '';
      setCopySource(nextWorkspace.reuse_sources[0]?.revision_id || '');
      if (!selectedId) {
        setRevision(null);
        setNodes([]);
        return;
      }
      const nextRevision = await getNativeBoqRevision(selectedId);
      selectRevision(nextRevision);
      if (requestedRevisionId !== selectedId) {
        navigate(`/project/detail/${projectId}/boq?revision=${selectedId}`, { replace: true });
      }
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [navigate, projectId, requestedRevisionId, selectRevision]);

  useEffect(() => {
    if (!BOQ_V2_ENABLED) {
      setLoading(false);
      return;
    }
    loadWorkspace();
  }, [loadWorkspace]);

  useEffect(() => {
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  useEffect(() => {
    if (!dirty || !revision) return;
    try {
      window.localStorage.setItem(backupKey(revision.revision_id), JSON.stringify({
        base_version: revision.version,
        saved_at: new Date().toISOString(),
        nodes,
      }));
    } catch {
      // Server save remains available when browser storage is full or disabled.
    }
  }, [dirty, nodes, revision]);

  useEffect(() => {
    const beforeUnload = (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [dirty]);

  const mutateNodes = (nextNodes) => {
    setNodes(normalizeSiblingPositions(nextNodes));
    setDirty(true);
    setSaveError(null);
    pendingSaveRef.current = null;
  };

  const openRevision = async (revisionId) => {
    if (!revisionId || revisionId === revision?.revision_id) return;
    if (dirty && !window.confirm('Discard the current unsaved edits and open another revision?')) return;
    navigate(`/project/detail/${projectId}/boq?revision=${revisionId}`);
  };

  const createDraft = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await createNativeBoqDocument(projectId);
      await loadWorkspace({ preferredRevisionId: created.revision_id });
    } catch (createError) {
      setError(createError);
    } finally {
      setBusy(false);
    }
  };

  const copyDraft = async () => {
    if (!copySource) return;
    setBusy(true);
    setError(null);
    try {
      const copied = await copyNativeBoqRevision(projectId, copySource);
      await loadWorkspace({ preferredRevisionId: copied.revision_id });
    } catch (copyError) {
      setError(copyError);
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = useCallback(async () => {
    if (!revision || !workspace?.can_edit || busy || !dirty || !online) return;
    const payload = buildSavePayload(revision.version, nodes);
    const fingerprint = JSON.stringify(payload);
    if (pendingSaveRef.current?.fingerprint !== fingerprint) {
      pendingSaveRef.current = {
        fingerprint,
        idempotencyKey: createBoqIdempotencyKey('boq-save'),
      };
    }
    setBusy(true);
    setSaveError(null);
    try {
      const saved = await saveNativeBoqDraft(revision.revision_id, payload, {
        idempotencyKey: pendingSaveRef.current.idempotencyKey,
      });
      clearBackup(revision.revision_id);
      setRecovery(null);
      selectRevision(saved);
      const nextWorkspace = await getNativeBoqWorkspace(projectId);
      setWorkspace(nextWorkspace);
    } catch (requestError) {
      setSaveError(requestError);
    } finally {
      setBusy(false);
    }
  }, [busy, dirty, nodes, online, projectId, revision, selectRevision, workspace?.can_edit]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveDraft();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [saveDraft]);

  const copyRecovery = async () => {
    const payload = JSON.stringify(buildSavePayload(revision.version, nodes), null, 2);
    try {
      await navigator.clipboard.writeText(payload);
    } catch {
      const blob = new Blob([payload], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `boq-recovery-${revision.revision_id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    }
  };

  if (!BOQ_V2_ENABLED) {
    return (
      <section className="boq-empty-state">
        <AlertTriangle size={30} />
        <h2>Native BOQ is not enabled</h2>
        <p>Return to Project Detail to use the retained legacy BOQ workflow.</p>
        <Link className="boq-button boq-button-secondary" to={`/project/detail/${projectId}`}>Open legacy BOQ</Link>
      </section>
    );
  }

  if (loading) return <Loading />;

  if (error || !workspace) {
    return (
      <section className="boq-empty-state boq-error-state" role="alert">
        <AlertTriangle size={30} />
        <h2>Could not load the BOQ workspace</h2>
        <p>{domainMessage(error)}</p>
        <button type="button" className="boq-button boq-button-primary" onClick={() => loadWorkspace()}>
          <RefreshCw size={16} /> Retry
        </button>
      </section>
    );
  }

  const projectName = workspace.project_name || location.state?.projectName || 'Project';
  const isConflict = saveError && ['STALE_BOQ_VERSION', 'BOQ_WRITE_CONFLICT'].includes(domainCode(saveError));
  const totalsStale = dirty;

  return (
    <div className="boq-workspace">
      <header className="boq-workspace-header">
        <div>
          <nav className="boq-breadcrumb" aria-label="Breadcrumb">
            <Link to="/project">Projects</Link>
            <ChevronRight size={13} />
            <Link to={`/project/detail/${projectId}`}>{projectName}</Link>
            <ChevronRight size={13} />
            <span aria-current="page">Native BOQ</span>
          </nav>
          <div className="boq-title-line">
            <Link className="boq-back-link" to={`/project/detail/${projectId}`} aria-label="Back to project detail">
              <ArrowLeft size={19} />
            </Link>
            <div>
              <h1>{projectName} · BOQ</h1>
              <p>Single scope structure with customer price and estimated cost views.</p>
            </div>
          </div>
        </div>
        <div className="boq-header-actions">
          <Link className="boq-button boq-button-secondary" to={`/project/detail/${projectId}`}>
            Legacy view{workspace.legacy_available ? ` · ${workspace.legacy_row_count} rows` : ''}
          </Link>
          {revision && workspace.can_edit ? (
            <button
              type="button"
              className="boq-button boq-button-primary"
              onClick={saveDraft}
              disabled={!dirty || busy || !online}
            >
              <Save size={16} /> {busy ? 'Saving…' : 'Save draft'}
            </button>
          ) : null}
        </div>
      </header>

      {!online ? (
        <section className="boq-notice boq-notice-danger" role="alert">
          <WifiOff size={18} />
          <div><strong>You are offline</strong><p>Edits are kept locally. Reconnect before saving.</p></div>
        </section>
      ) : null}

      {!workspace.can_edit ? (
        <section className="boq-notice" role="status">
          <Clipboard size={18} />
          <div><strong>Read-only workspace</strong><p>Admins can review native BOQ drafts; only Owners can change them.</p></div>
        </section>
      ) : null}

      <RecoveryPanel
        recovery={recovery}
        onRestore={() => {
          setNodes(normalizeSiblingPositions(recovery.nodes));
          setDirty(true);
          setRecovery(null);
        }}
        onDiscard={() => {
          clearBackup(revision?.revision_id);
          setRecovery(null);
        }}
      />

      {saveError ? (
        <section className={`boq-notice ${isConflict ? 'boq-notice-danger' : 'boq-notice-warning'}`} role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>{isConflict ? 'This draft changed on the server' : 'Draft was not saved'}</strong>
            <p>{domainMessage(saveError)} Your unsaved rows remain in this browser.</p>
          </div>
          <div className="boq-notice-actions">
            <button type="button" className="boq-button boq-button-secondary" onClick={copyRecovery}>Copy recovery JSON</button>
            {isConflict ? (
              <button type="button" className="boq-button boq-button-secondary" onClick={() => loadWorkspace({ preferredRevisionId: revision.revision_id })}>
                Reload server version
              </button>
            ) : (
              <button type="button" className="boq-button boq-button-primary" onClick={saveDraft}>Retry save</button>
            )}
          </div>
        </section>
      ) : null}

      {!revision ? (
        <EmptyWorkspace
          workspace={workspace}
          busy={busy}
          copySource={copySource}
          onCopySource={setCopySource}
          onCreate={createDraft}
          onCopy={copyDraft}
        />
      ) : (
        <div className="boq-workspace-grid">
          <aside className="boq-revision-panel" aria-label="BOQ revisions">
            <div>
              <span className="boq-eyebrow">DRAFT HISTORY</span>
              <h2>Revisions</h2>
            </div>
            <div className="boq-revision-list">
              {workspace.revisions.map((item) => (
                <button
                  key={item.revision_id}
                  type="button"
                  className={item.revision_id === revision.revision_id ? 'active' : ''}
                  onClick={() => openRevision(item.revision_id)}
                >
                  <span>R{item.revision_number} · {item.status}</span>
                  <strong>{formatMoney(item.net_sell_ex_vat)}</strong>
                  <small>v{item.version} · {item.completeness_state}</small>
                </button>
              ))}
            </div>
            <div className="boq-source-status">
              <span>Operational budget source</span>
              <strong>{workspace.active_source_kind}</strong>
              <small>This DRAFT is not an operational baseline.</small>
            </div>
          </aside>

          <main className="boq-editor-panel">
            <section className="boq-summary-strip" aria-label="Server-calculated BOQ summary">
              <div><span>Customer price ex VAT</span><strong>{formatMoney(revision.net_sell_ex_vat)}</strong></div>
              <div><span>Known estimated cost</span><strong>{formatMoney(revision.known_estimated_cost)}</strong></div>
              <div><span>Forecast margin</span><strong>{formatMoney(revision.forecast_margin)}</strong></div>
              <div>
                <span>Cost completeness</span>
                <strong>{revision.completeness.state}</strong>
                <small>{revision.completeness.priced_count}/{revision.completeness.required_count} required components priced</small>
              </div>
              {totalsStale ? <p className="boq-stale-totals">Totals are from the last server save. Save to recalculate.</p> : null}
            </section>

            <div className="boq-editor-toolbar">
              <div className="boq-view-switcher" role="group" aria-label="BOQ view">
                {VIEW_MODES.map((mode) => (
                  <button
                    key={mode.value}
                    type="button"
                    className={viewMode === mode.value ? 'active' : ''}
                    onClick={() => setViewMode(mode.value)}
                    aria-pressed={viewMode === mode.value}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
              <div className="boq-toolbar-actions">
                {dirty ? <span className="boq-unsaved-mark">Unsaved changes</span> : <span className="boq-saved-mark"><Check size={14} /> Saved</span>}
                {workspace.can_edit ? (
                  <button type="button" className="boq-button boq-button-secondary" onClick={() => mutateNodes(addDraftNode(nodes, 'SECTION'))}>
                    <Plus size={15} /> Add section
                  </button>
                ) : null}
              </div>
            </div>

            {nodes.length === 0 ? (
              <div className="boq-inline-empty">
                <p>This draft has no scope rows.</p>
                {workspace.can_edit ? (
                  <button type="button" className="boq-button boq-button-primary" onClick={() => mutateNodes(addDraftNode(nodes, 'SECTION'))}>
                    <Plus size={16} /> Add first section
                  </button>
                ) : null}
              </div>
            ) : (
              <div className="boq-table-shell" data-view={viewMode}>
                <table className="boq-editor-table">
                  <thead>
                    <tr>
                      <th>Scope</th>
                      {viewMode !== 'cost' ? <th>Customer price</th> : null}
                      {viewMode !== 'customer' ? <th>Estimated cost</th> : null}
                      <th>Server total</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nodes.map((node) => (
                      <ScopeRow
                        key={node.logical_id}
                        node={node}
                        nodes={nodes}
                        viewMode={viewMode}
                        disabled={!workspace.can_edit || busy}
                        onNodesChange={mutateNodes}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <footer className="boq-editor-footer">
              <span>Revision {revision.revision_number} · version {revision.version} · calculation {revision.calculation_version}</span>
              <span>Last server update {formatTimestamp(revision.updated_at)}</span>
              <span>Keyboard: Ctrl/Cmd + S</span>
            </footer>
          </main>
        </div>
      )}
    </div>
  );
}
