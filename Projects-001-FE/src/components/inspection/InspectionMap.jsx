import { useState } from 'react';
import {
  AlertTriangle,
  ImagePlus,
  Layers3,
  Loader2,
  MapPin,
  Plus,
  UploadCloud,
} from 'lucide-react';
import {
  INSPECTION_PLAN_MAX_BYTES,
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_STATUS_LABELS,
  clampPlanCoordinate,
  formatInspectionDate,
  getSeverityTone,
  getStatusTone,
  validateInspectionImageFiles,
} from './inspectionUtils';
import useInspectionSignedUrl from './useInspectionSignedUrl';

const EMPTY_ZONE_DRAFT = {
  name: '',
  floor: '',
  room: '',
  sortOrder: '',
};

function zoneLabel(zone) {
  return [zone?.floor, zone?.room].filter(Boolean).join(' / ') || 'Zone';
}

function ZoneCreateForm({ onCreateZone, creating = false, onCancel }) {
  const [draft, setDraft] = useState(EMPTY_ZONE_DRAFT);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const name = draft.name.trim();
    if (!name || creating) return;
    await onCreateZone({
      name,
      floor: draft.floor.trim() || null,
      room: draft.room.trim() || null,
      sort_order: draft.sortOrder === '' ? 0 : Number(draft.sortOrder),
    });
    setDraft(EMPTY_ZONE_DRAFT);
    onCancel();
  };

  return (
    <form className="inspection-zone-create" onSubmit={handleSubmit}>
      <label>
        Zone name
        <input
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          placeholder="Level 4 - North Wing"
          required
        />
      </label>
      <div className="inspection-zone-create-grid">
        <label>
          Floor
          <input
            value={draft.floor}
            onChange={(event) => setDraft({ ...draft, floor: event.target.value })}
            placeholder="Level 4"
          />
        </label>
        <label>
          Room / area
          <input
            value={draft.room}
            onChange={(event) => setDraft({ ...draft, room: event.target.value })}
            placeholder="North Wing"
          />
        </label>
      </div>
      <label>
        Sort order
        <input
          type="number"
          value={draft.sortOrder}
          onChange={(event) => setDraft({ ...draft, sortOrder: event.target.value })}
          placeholder="10"
        />
      </label>
      <div className="inspection-zone-create-actions">
        <button type="button" className="inspection-button secondary" onClick={onCancel} disabled={creating}>
          Cancel
        </button>
        <button type="submit" className="inspection-button primary" disabled={creating || !draft.name.trim()}>
          <Plus size={15} />
          Create Zone
        </button>
      </div>
    </form>
  );
}

export default function InspectionMap({
  zones = [],
  defects = [],
  selectedZoneId = '',
  selectedDefectId = '',
  draftCoordinate = null,
  loading = false,
  creatingZone = false,
  uploadingPlan = false,
  roleContext = {},
  onSelectZone,
  onSelectDefect,
  onCreateZone,
  onUploadPlan,
  onStartDefect,
}) {
  const [createZoneOpen, setCreateZoneOpen] = useState(false);
  const [planUploadError, setPlanUploadError] = useState('');
  const selectedZone = zones.find((zone) => zone.id === selectedZoneId) || zones[0] || null;
  const selectedDefect = defects.find((defect) => defect.id === selectedDefectId) || null;
  const zoneDefects = defects.filter((defect) => defect.zone_id === selectedZone?.id);
  const pinnedDefects = zoneDefects.filter((defect) => defect.plan_x != null && defect.plan_y != null);
  const { signedUrl: planUrl, loading: loadingPlan, error: planError } = useInspectionSignedUrl(selectedZone?.plan_file_id);
  const canManageMap = Boolean(roleContext?.canStaff);

  const zoneCounts = new Map();
  defects.forEach((defect) => {
    zoneCounts.set(defect.zone_id, Number(zoneCounts.get(defect.zone_id) || 0) + 1);
  });

  const handlePlanClick = (event) => {
    if (!canManageMap || !selectedZone || !planUrl) return;
    const rect = event.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    onStartDefect({
      zoneId: selectedZone.id,
      planX: clampPlanCoordinate(((event.clientX - rect.left) / rect.width) * 100, 0),
      planY: clampPlanCoordinate(((event.clientY - rect.top) / rect.height) * 100, 0),
    });
  };

  const handlePlanKeyDown = (event) => {
    if (!canManageMap || !selectedZone || !planUrl) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    onStartDefect({ zoneId: selectedZone.id, planX: 50, planY: 50 });
  };

  const handlePlanUpload = (event) => {
    const file = event.target.files?.[0];
    if (file && selectedZone && canManageMap) {
      const validation = validateInspectionImageFiles([file], {
        maxBytes: INSPECTION_PLAN_MAX_BYTES,
        label: 'plan image',
      });
      if (validation.error) {
        setPlanUploadError(validation.error);
      } else {
        setPlanUploadError('');
        onUploadPlan(validation.files[0], selectedZone.id);
      }
    }
    event.target.value = '';
  };

  return (
    <section className="inspection-map-shell">
      <aside className="inspection-zone-panel">
        <div className="inspection-panel-head">
          <div>
            <span>Zones</span>
            <h3>{zones.length} areas</h3>
          </div>
          {canManageMap ? (
            <button
              type="button"
              className="inspection-icon-button"
              onClick={() => setCreateZoneOpen(true)}
              aria-label="Create inspection zone"
            >
              <Plus size={17} />
            </button>
          ) : null}
        </div>

        {createZoneOpen && canManageMap ? (
          <ZoneCreateForm
            onCreateZone={onCreateZone}
            creating={creatingZone}
            onCancel={() => setCreateZoneOpen(false)}
          />
        ) : null}

        {zones.length ? (
          <div className="inspection-zone-list">
            {zones.map((zone) => {
              const isActive = zone.id === selectedZone?.id;
              return (
                <button
                  key={zone.id}
                  type="button"
                  className={isActive ? 'active' : ''}
                  onClick={() => onSelectZone(zone.id)}
                >
                  <span>
                    <strong>{zone.name}</strong>
                    <small>{zoneLabel(zone)}</small>
                  </span>
                  <em>{zoneCounts.get(zone.id) || 0}</em>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="inspection-soft-empty">No zones in this round</div>
        )}
      </aside>

      <main className="inspection-map-canvas">
        <div className="inspection-map-toolbar">
          <div>
            <span>Floor plan</span>
            <h3>{selectedZone?.name || 'No zone selected'}</h3>
          </div>
          {canManageMap ? (
            <div className="inspection-map-actions">
              <label className={`inspection-button secondary${!selectedZone ? ' disabled' : ''}`}>
                <UploadCloud size={16} />
                {uploadingPlan ? 'Uploading' : 'Upload Plan'}
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePlanUpload}
                  disabled={!selectedZone || uploadingPlan}
                />
              </label>
              <button
                type="button"
                className="inspection-button primary"
                onClick={() => selectedZone && onStartDefect({ zoneId: selectedZone.id, planX: null, planY: null })}
                disabled={!selectedZone}
              >
                <MapPin size={16} />
                Add Defect
              </button>
            </div>
          ) : null}
        </div>
        {planUploadError ? <div className="inspection-inline-alert danger" role="alert">{planUploadError}</div> : null}

        {loading ? (
          <div className="inspection-plan-empty" role="status" aria-live="polite">
            <Loader2 size={22} className="inspection-spin" />
            <strong>Loading inspection map</strong>
          </div>
        ) : !selectedZone ? (
          <div className="inspection-plan-empty">
            <Layers3 size={26} />
            <strong>{canManageMap ? 'Create a zone to start inspection capture' : 'No zone selected'}</strong>
          </div>
        ) : loadingPlan ? (
          <div className="inspection-plan-empty" role="status" aria-live="polite">
            <Loader2 size={22} className="inspection-spin" />
            <strong>Loading plan</strong>
          </div>
        ) : planUrl ? (
          <div className="inspection-plan-scroll">
            <div className={`inspection-plan-stage${canManageMap ? '' : ' read-only'}`}>
              <img src={planUrl} alt={`${selectedZone.name} plan`} draggable={false} />
              {canManageMap ? (
                <button
                  type="button"
                  className="inspection-plan-hotspot"
                  onClick={handlePlanClick}
                  onKeyDown={handlePlanKeyDown}
                  aria-label={`Add defect pin to ${selectedZone.name}`}
                />
              ) : null}
              {pinnedDefects.map((defect) => {
                const isSelected = defect.id === selectedDefectId;
                return (
                  <button
                    key={defect.id}
                    type="button"
                    className={`inspection-map-pin tone-${getSeverityTone(defect.severity)}${isSelected ? ' active' : ''}`}
                    style={{
                      left: `${clampPlanCoordinate(defect.plan_x)}%`,
                      top: `${clampPlanCoordinate(defect.plan_y)}%`,
                    }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectDefect(defect.id);
                    }}
                    aria-label={`Open ${defect.display_no || 'defect'}`}
                  >
                    <MapPin size={16} />
                  </button>
                );
              })}
              {draftCoordinate?.zoneId === selectedZone.id && draftCoordinate.planX != null && draftCoordinate.planY != null ? (
                <span
                  className="inspection-map-pin draft"
                  style={{
                    left: `${clampPlanCoordinate(draftCoordinate.planX)}%`,
                    top: `${clampPlanCoordinate(draftCoordinate.planY)}%`,
                  }}
                >
                  <Plus size={15} />
                </span>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="inspection-plan-empty">
            <ImagePlus size={28} />
            <strong>{planError || 'No plan image uploaded'}</strong>
            {canManageMap ? (
              <label className="inspection-button primary">
                <UploadCloud size={16} />
                Upload Plan
                <input type="file" accept="image/*" onChange={handlePlanUpload} disabled={uploadingPlan} />
              </label>
            ) : null}
          </div>
        )}
      </main>

      <aside className="inspection-map-side">
        <section className="inspection-side-card">
          <div className="inspection-panel-head compact">
            <div>
              <span>Current zone</span>
              <h3>{selectedZone?.name || '-'}</h3>
            </div>
            <Layers3 size={18} />
          </div>
          <div className="inspection-side-stats">
            <div>
              <strong>{zoneDefects.length}</strong>
              <span>Defects</span>
            </div>
            <div>
              <strong>{pinnedDefects.length}</strong>
              <span>Pins</span>
            </div>
          </div>
        </section>

        {selectedDefect ? (
          <section className="inspection-side-card">
            <div className="inspection-panel-head compact">
              <div>
                <span>Selected pin</span>
                <h3>{selectedDefect.display_no}</h3>
              </div>
              <AlertTriangle size={18} />
            </div>
            <p>{selectedDefect.title}</p>
            <div className="inspection-badge-row">
              <span className={`inspection-badge tone-${getStatusTone(selectedDefect.status)}`}>
                {INSPECTION_STATUS_LABELS[selectedDefect.status] || selectedDefect.status}
              </span>
              <span className={`inspection-badge tone-${getSeverityTone(selectedDefect.severity)}`}>
                {INSPECTION_SEVERITY_LABELS[selectedDefect.severity] || selectedDefect.severity}
              </span>
            </div>
          </section>
        ) : null}

        <section className="inspection-side-card">
          <div className="inspection-panel-head compact">
            <div>
              <span>Recent defects</span>
              <h3>{zoneDefects.length ? `${zoneDefects.length} items` : 'Empty'}</h3>
            </div>
          </div>
          {zoneDefects.length ? (
            <div className="inspection-mini-defect-list">
              {zoneDefects.slice(0, 6).map((defect) => (
                <button key={defect.id} type="button" onClick={() => onSelectDefect(defect.id)}>
                  <span>{defect.display_no}</span>
                  <strong>{defect.title}</strong>
                  <small>{formatInspectionDate(defect.updated_at)}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="inspection-soft-empty">No captured defects</div>
          )}
        </section>
      </aside>
    </section>
  );
}
