import { useState } from 'react';
import { Camera, CheckCircle2, Clock3, MessageSquare, RotateCcw, UploadCloud } from 'lucide-react';
import {
  INSPECTION_EVENT_LABELS,
  INSPECTION_PHOTO_MAX_BYTES,
  INSPECTION_STATUS_LABELS,
  formatInspectionDateTime,
  validateInspectionImageFiles,
} from './inspectionUtils';

function getWorkflowActions(defect, roleContext) {
  const status = String(defect?.status || 'OPEN').toUpperCase();
  const canStaff = Boolean(roleContext?.canStaff);
  const isSubcontractor = Boolean(roleContext?.isSubcontractor && !canStaff);

  if (canStaff) {
    if (status === 'OPEN') {
      return [
        { status: 'IN_PROGRESS', label: 'Start Work', icon: Clock3 },
        { status: 'READY_FOR_REVIEW', label: 'Ready for Review', icon: CheckCircle2 },
      ];
    }
    if (status === 'IN_PROGRESS') {
      return [{ status: 'READY_FOR_REVIEW', label: 'Ready for Review', icon: CheckCircle2 }];
    }
    if (status === 'READY_FOR_REVIEW') {
      return [
        { status: 'RESOLVED', label: 'Resolve', icon: CheckCircle2 },
        { status: 'IN_PROGRESS', label: 'Reject Fix', icon: RotateCcw, requiresComment: true, danger: true },
      ];
    }
    return [];
  }

  if (isSubcontractor && ['OPEN', 'IN_PROGRESS'].includes(status)) {
    return [{ status: 'READY_FOR_REVIEW', label: 'Mark Ready', icon: CheckCircle2 }];
  }

  return [];
}

function TimelineEvent({ event }) {
  const label = INSPECTION_EVENT_LABELS[event.event_type] || event.event_type || 'Event';
  const fromStatus = event.from_status ? INSPECTION_STATUS_LABELS[event.from_status] || event.from_status : '';
  const toStatus = event.to_status ? INSPECTION_STATUS_LABELS[event.to_status] || event.to_status : '';
  const transition = fromStatus || toStatus ? `${fromStatus || '-'} -> ${toStatus || '-'}` : '';
  const metadata = event.metadata || {};

  return (
    <article className="inspection-timeline-event">
      <span />
      <div>
        <div className="inspection-timeline-event-head">
          <strong>{label}</strong>
          <small>{formatInspectionDateTime(event.created_at)}</small>
        </div>
        {transition ? <p>{transition}</p> : null}
        {event.comment ? <p>{event.comment}</p> : null}
        {metadata.kind ? <p>{metadata.kind.replace(/_/g, ' ')}</p> : null}
        <small>{event.actor_id || 'System'}{event.actor_role ? ` / ${event.actor_role}` : ''}</small>
      </div>
    </article>
  );
}

export default function InspectionWorkflowPanel({
  defect,
  roleContext,
  events = [],
  loadingEvents = false,
  workflowBusy = false,
  workflowError = '',
  onStatusChange,
  onAddComment,
  onUploadAfterPhotos,
}) {
  const [workflowNote, setWorkflowNote] = useState('');
  const [commentDraft, setCommentDraft] = useState('');
  const [afterFiles, setAfterFiles] = useState([]);
  const [localError, setLocalError] = useState('');
  const actions = getWorkflowActions(defect, roleContext);
  const canUploadAfter = Boolean(defect && (roleContext?.canStaff || roleContext?.isSubcontractor));
  const canComment = Boolean(defect && (roleContext?.canStaff || roleContext?.isSubcontractor));

  const handleAfterFiles = (event) => {
    const files = Array.from(event.target.files || []);
    const validation = validateInspectionImageFiles(files, {
      maxBytes: INSPECTION_PHOTO_MAX_BYTES,
      label: 'photo',
    });
    if (validation.error) {
      setLocalError(validation.error);
      event.target.value = '';
      return;
    }
    setLocalError('');
    setAfterFiles(validation.files);
  };

  const runStatusAction = async (action) => {
    if (workflowBusy) return;
    const comment = workflowNote.trim();
    if (action.requiresComment && !comment) {
      setLocalError('A rejection comment is required.');
      return;
    }
    setLocalError('');
    await onStatusChange(defect, action.status, comment || null);
    setWorkflowNote('');
  };

  const uploadEvidence = async () => {
    if (!afterFiles.length || workflowBusy) return;
    setLocalError('');
    await onUploadAfterPhotos(defect, afterFiles);
    setAfterFiles([]);
  };

  const addComment = async () => {
    const comment = commentDraft.trim();
    if (!comment || workflowBusy) return;
    setLocalError('');
    await onAddComment(defect, comment);
    setCommentDraft('');
  };

  return (
    <section className="inspection-workflow-panel">
      {(workflowError || localError) ? (
        <div className="inspection-alert danger" role="alert">{workflowError || localError}</div>
      ) : null}

      {actions.length ? (
        <div className="inspection-workflow-card">
          <h4>Status workflow</h4>
          <textarea
            value={workflowNote}
            onChange={(event) => setWorkflowNote(event.target.value)}
            placeholder="Optional status note. Required when rejecting a fix."
            rows={3}
          />
          <div className="inspection-workflow-actions">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={`${action.status}-${action.label}`}
                  type="button"
                  className={`inspection-button ${action.danger ? 'danger' : 'primary'}`}
                  onClick={() => runStatusAction(action)}
                  disabled={workflowBusy}
                >
                  <Icon size={16} />
                  {action.label}
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="inspection-soft-empty">No status action is available for this defect.</div>
      )}

      {canUploadAfter ? (
        <div className="inspection-workflow-card">
          <h4>Fix evidence</h4>
          <label className="inspection-photo-input">
            <input type="file" accept="image/*" multiple onChange={handleAfterFiles} disabled={workflowBusy} />
            <span>
              <Camera size={16} />
              {afterFiles.length ? `${afterFiles.length} after photos selected` : 'Select after photos'}
            </span>
          </label>
          <button
            type="button"
            className="inspection-button secondary"
            onClick={uploadEvidence}
            disabled={workflowBusy || !afterFiles.length}
          >
            <UploadCloud size={16} />
            Upload Evidence
          </button>
        </div>
      ) : null}

      {canComment ? (
        <div className="inspection-workflow-card">
          <h4>Comment</h4>
          <textarea
            value={commentDraft}
            onChange={(event) => setCommentDraft(event.target.value)}
            placeholder="Add a note to the inspection timeline"
            rows={3}
          />
          <button
            type="button"
            className="inspection-button secondary"
            onClick={addComment}
            disabled={workflowBusy || !commentDraft.trim()}
          >
            <MessageSquare size={16} />
            Add Comment
          </button>
        </div>
      ) : null}

      <div className="inspection-workflow-card">
        <div className="inspection-detail-card-head">
          <h4>Timeline</h4>
          {loadingEvents ? <Clock3 size={16} /> : <MessageSquare size={16} />}
        </div>
        {loadingEvents ? (
          <div className="inspection-soft-empty">Loading timeline</div>
        ) : events.length ? (
          <div className="inspection-timeline">
            {events.map((event) => (
              <TimelineEvent key={event.id} event={event} />
            ))}
          </div>
        ) : (
          <div className="inspection-soft-empty">No timeline events</div>
        )}
      </div>
    </section>
  );
}
