import { useEffect, useRef } from 'react';
import {
  CalendarDays,
  Camera,
  ClipboardList,
  MapPin,
  Tag,
  UserRound,
  X,
} from 'lucide-react';
import InspectionDefectForm from './InspectionDefectForm';
import InspectionFilePreview from './InspectionFilePreview';
import InspectionWorkflowPanel from './InspectionWorkflowPanel';
import {
  INSPECTION_SEVERITY_LABELS,
  INSPECTION_STATUS_LABELS,
  formatInspectionDate,
  formatPlanCoordinate,
  getSeverityTone,
  getStatusTone,
} from './inspectionUtils';

function DetailRow({ icon, label, value }) {
  const IconComponent = icon;
  return (
    <div className="inspection-detail-row">
      <IconComponent size={15} />
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}

export default function InspectionDefectDrawer({
  mode = '',
  defect = null,
  zones = [],
  categories = [],
  subcontractors = [],
  coordinate = null,
  defaultZoneId = '',
  roleContext = {},
  events = [],
  loadingEvents = false,
  workflowBusy = false,
  workflowError = '',
  onClose,
  onCreateDefect,
  onStatusChange,
  onAddComment,
  onUploadAfterPhotos,
  saving = false,
}) {
  const drawerRef = useRef(null);

  useEffect(() => {
    if (mode) {
      drawerRef.current?.focus();
    }
  }, [mode]);

  if (!mode) return null;

  const zone = zones.find((item) => item.id === defect?.zone_id || item.id === coordinate?.zoneId) || null;
  const beforeFileIds = Array.isArray(defect?.before_file_ids) ? defect.before_file_ids : [];
  const afterFileIds = Array.isArray(defect?.after_file_ids) ? defect.after_file_ids : [];
  const isCreate = mode === 'create';
  const status = String(defect?.status || 'OPEN').toUpperCase();
  const severity = String(defect?.severity || 'MINOR').toUpperCase();
  const dialogLabel = isCreate ? 'Capture inspection defect' : `Inspection defect ${defect?.display_no || ''}`.trim();

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="inspection-drawer-scrim" onMouseDown={onClose}>
      <aside
        ref={drawerRef}
        className="inspection-defect-drawer"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-modal="true"
        aria-label={dialogLabel}
        tabIndex={-1}
      >
        <header className="inspection-drawer-header">
          <div>
            <span className="inspection-drawer-kicker">
              <ClipboardList size={15} />
              {isCreate ? 'Capture Defect' : 'Defect Detail'}
            </span>
            <h3>{isCreate ? 'Add defect' : `${defect?.display_no || 'Defect'} ${defect?.title || ''}`}</h3>
          </div>
          <button type="button" className="inspection-icon-button" onClick={onClose} aria-label="Close defect drawer">
            <X size={18} />
          </button>
        </header>

        {isCreate ? (
          <InspectionDefectForm
            zones={zones}
            categories={categories}
            subcontractors={subcontractors}
            coordinate={coordinate}
            defaultZoneId={defaultZoneId}
            onSubmit={onCreateDefect}
            onCancel={onClose}
            saving={saving}
          />
        ) : (
          <div className="inspection-drawer-detail">
            <div className="inspection-badge-row">
              <span className={`inspection-badge tone-${getStatusTone(status)}`}>
                {INSPECTION_STATUS_LABELS[status] || status}
              </span>
              <span className={`inspection-badge tone-${getSeverityTone(severity)}`}>
                {INSPECTION_SEVERITY_LABELS[severity] || severity}
              </span>
            </div>

            <section className="inspection-detail-card">
              <h4>Location</h4>
              <DetailRow icon={MapPin} label="Zone" value={zone?.name || defect?.zone_id} />
              <DetailRow icon={Tag} label="Category" value={defect?.category} />
              <DetailRow icon={CalendarDays} label="Due" value={formatInspectionDate(defect?.due_date)} />
              <DetailRow icon={MapPin} label="Plan pin" value={formatPlanCoordinate(defect?.plan_x, defect?.plan_y)} />
            </section>

            <section className="inspection-detail-card">
              <h4>Responsibility</h4>
              <DetailRow icon={UserRound} label="Contractor" value={defect?.assigned_subcontractor_name || 'Unassigned'} />
              <DetailRow icon={CalendarDays} label="Updated" value={formatInspectionDate(defect?.updated_at)} />
            </section>

            {defect?.description ? (
              <section className="inspection-detail-card">
                <h4>Notes</h4>
                <p>{defect.description}</p>
              </section>
            ) : null}

            <section className="inspection-detail-card">
              <div className="inspection-detail-card-head">
                <h4>Before photos</h4>
                <Camera size={16} />
              </div>
              {beforeFileIds.length ? (
                <div className="inspection-photo-grid">
                  {beforeFileIds.map((fileId) => (
                    <InspectionFilePreview key={fileId} fileId={fileId} label="Before photo" compact />
                  ))}
                </div>
              ) : (
                <div className="inspection-soft-empty">No before photos</div>
              )}
            </section>

            <section className="inspection-detail-card">
              <div className="inspection-detail-card-head">
                <h4>After photos</h4>
                <Camera size={16} />
              </div>
              {afterFileIds.length ? (
                <div className="inspection-photo-grid">
                  {afterFileIds.map((fileId) => (
                    <InspectionFilePreview key={fileId} fileId={fileId} label="After photo" compact />
                  ))}
                </div>
              ) : (
                <div className="inspection-soft-empty">No after photos</div>
              )}
            </section>

            <InspectionWorkflowPanel
              defect={defect}
              roleContext={roleContext}
              events={events}
              loadingEvents={loadingEvents}
              workflowBusy={workflowBusy}
              workflowError={workflowError}
              onStatusChange={onStatusChange}
              onAddComment={onAddComment}
              onUploadAfterPhotos={onUploadAfterPhotos}
            />
          </div>
        )}
      </aside>
    </div>
  );
}
