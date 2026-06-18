import { useMemo, useState } from 'react';
import { Camera, Check, MapPin, Plus } from 'lucide-react';
import {
  INSPECTION_PHOTO_MAX_BYTES,
  INSPECTION_SEVERITY_OPTIONS,
  formatPlanCoordinate,
  validateInspectionImageFiles,
} from './inspectionUtils';

const PRESETS = [
  { title: 'Paint touch-up', category: 'Finishes', severity: 'COSMETIC' },
  { title: 'Tile/grout incomplete', category: 'Finishes', severity: 'MINOR' },
  { title: 'Door/window alignment', category: 'Architectural', severity: 'MINOR' },
  { title: 'Electrical point issue', category: 'Electrical', severity: 'MAJOR' },
  { title: 'Plumbing leak', category: 'Plumbing', severity: 'CRITICAL' },
];

function normalizeSubcontractor(item) {
  const id = String(item?.subcontractor_id || item?.id || item?.uid || '').trim();
  const name = String(item?.name || item?.company_name || item?.contact_name || id || '').trim();
  return id ? { id, name } : null;
}

function createInitialDraft({ coordinate, defaultZoneId, categories }) {
  return {
    zoneId: coordinate?.zoneId || defaultZoneId || '',
    title: '',
    description: '',
    category: categories[0] || 'Other',
    severity: 'MINOR',
    assignedSubcontractorId: '',
    assignedSubcontractorName: '',
    dueDate: '',
    photoFiles: [],
  };
}

export default function InspectionDefectForm({
  zones = [],
  categories = [],
  subcontractors = [],
  coordinate = null,
  defaultZoneId = '',
  onSubmit,
  onCancel,
  saving = false,
}) {
  const [draft, setDraft] = useState(() => createInitialDraft({ coordinate, defaultZoneId, categories }));
  const [fileError, setFileError] = useState('');

  const normalizedSubcontractors = useMemo(
    () => subcontractors.map(normalizeSubcontractor).filter(Boolean),
    [subcontractors]
  );
  const selectedZoneValue = draft.zoneId || coordinate?.zoneId || defaultZoneId || '';
  const selectedCategory = categories.includes(draft.category) ? draft.category : categories[0] || 'Other';

  const updateDraft = (updates) => {
    setDraft((current) => ({ ...current, ...updates }));
  };

  const handlePreset = (preset) => {
    updateDraft({
      title: preset.title,
      category: categories.includes(preset.category) ? preset.category : selectedCategory,
      severity: preset.severity,
    });
  };

  const handleSubcontractorChange = (value) => {
    const selected = normalizedSubcontractors.find((item) => item.id === value);
    updateDraft({
      assignedSubcontractorId: value,
      assignedSubcontractorName: selected?.name || '',
    });
  };

  const handleFilesChange = (event) => {
    const files = Array.from(event.target.files || []);
    const validation = validateInspectionImageFiles(files, {
      maxBytes: INSPECTION_PHOTO_MAX_BYTES,
      label: 'photo',
    });
    if (validation.error) {
      setFileError(validation.error);
      event.target.value = '';
      return;
    }

    setFileError('');
    updateDraft({ photoFiles: validation.files });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (saving) return;

    const title = draft.title.trim();
    const zoneId = selectedZoneValue;
    if (!title || !zoneId) return;

    onSubmit(
      {
        zone_id: zoneId,
        title,
        description: draft.description.trim() || null,
        category: selectedCategory,
        severity: draft.severity,
        status: 'OPEN',
        assigned_subcontractor_id: draft.assignedSubcontractorId || null,
        assigned_subcontractor_name: draft.assignedSubcontractorName || null,
        due_date: draft.dueDate || null,
        plan_x: coordinate?.planX ?? null,
        plan_y: coordinate?.planY ?? null,
      },
      draft.photoFiles
    );
  };

  return (
    <form className="inspection-defect-form" onSubmit={handleSubmit}>
      <div className="inspection-form-coordinate">
        <MapPin size={16} />
        <span>{formatPlanCoordinate(coordinate?.planX, coordinate?.planY)}</span>
      </div>

      <div className="inspection-preset-row">
        {PRESETS.map((preset) => (
          <button key={preset.title} type="button" onClick={() => handlePreset(preset)}>
            <Plus size={13} />
            {preset.title}
          </button>
        ))}
      </div>

      <label className="inspection-field">
        Zone
        <select
          value={selectedZoneValue}
          onChange={(event) => updateDraft({ zoneId: event.target.value })}
          required
        >
          <option value="">Select zone</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
      </label>

      <label className="inspection-field">
        Description
        <input
          value={draft.title}
          onChange={(event) => updateDraft({ title: event.target.value })}
          placeholder="Water stain above ceiling"
          required
        />
      </label>

      <label className="inspection-field">
        Notes
        <textarea
          value={draft.description}
          onChange={(event) => updateDraft({ description: event.target.value })}
          placeholder="Observed condition, affected area, or repair notes"
          rows={4}
        />
      </label>

      <div className="inspection-form-grid">
        <label className="inspection-field">
          Category
          <select value={selectedCategory} onChange={(event) => updateDraft({ category: event.target.value })}>
            {(categories.length ? categories : ['Other']).map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>

        <label className="inspection-field">
          Severity
          <select value={draft.severity} onChange={(event) => updateDraft({ severity: event.target.value })}>
            {INSPECTION_SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="inspection-form-grid">
        <label className="inspection-field">
          Responsible party
          <select
            value={draft.assignedSubcontractorId}
            onChange={(event) => handleSubcontractorChange(event.target.value)}
          >
            <option value="">Unassigned</option>
            {normalizedSubcontractors.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="inspection-field">
          Due date
          <input
            type="date"
            value={draft.dueDate}
            onChange={(event) => updateDraft({ dueDate: event.target.value })}
          />
        </label>
      </div>

      <label className="inspection-photo-input">
        <input type="file" accept="image/*" multiple onChange={handleFilesChange} />
        <span>
          <Camera size={16} />
          {draft.photoFiles.length ? `${draft.photoFiles.length} before photos selected` : 'Add before photos'}
        </span>
      </label>
      {fileError ? <div className="inspection-alert danger" role="alert">{fileError}</div> : null}

      <div className="inspection-drawer-actions">
        <button type="button" className="inspection-button secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="inspection-button primary" disabled={saving || !selectedZoneValue || !draft.title.trim()}>
          <Check size={16} />
          Save Defect
        </button>
      </div>
    </form>
  );
}
