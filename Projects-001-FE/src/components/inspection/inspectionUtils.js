export const INSPECTION_STATUS_LABELS = {
  OPEN: 'Open',
  IN_PROGRESS: 'In Progress',
  READY_FOR_REVIEW: 'Ready for Review',
  RESOLVED: 'Resolved',
};

export const INSPECTION_SEVERITY_LABELS = {
  CRITICAL: 'Critical',
  MAJOR: 'Major',
  MINOR: 'Minor',
  COSMETIC: 'Cosmetic',
};

export const INSPECTION_SEVERITY_OPTIONS = Object.entries(INSPECTION_SEVERITY_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const INSPECTION_STATUS_OPTIONS = Object.entries(INSPECTION_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const INSPECTION_EVENT_LABELS = {
  DEFECT_CREATED: 'Defect created',
  STATUS_CHANGED: 'Status changed',
  ASSIGNED: 'Assigned',
  COMMENT_ADDED: 'Comment added',
  FILE_UPLOADED: 'File uploaded',
  READY_FOR_REVIEW: 'Ready for review',
  REVIEW_REJECTED: 'Review rejected',
  RESOLVED: 'Resolved',
  REPORT_PRINTED: 'Report printed',
};

export const INSPECTION_PHOTO_MAX_BYTES = 10 * 1024 * 1024;
export const INSPECTION_PLAN_MAX_BYTES = 25 * 1024 * 1024;

export function formatFileSize(bytes) {
  const size = Number(bytes || 0);
  if (!Number.isFinite(size) || size <= 0) return '0MB';
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(size % (1024 * 1024) === 0 ? 0 : 1)}MB`;
  return `${Math.ceil(size / 1024)}KB`;
}

export function validateInspectionImageFiles(files, { maxBytes, label = 'photo' } = {}) {
  const items = Array.from(files || []);
  const limit = Number(maxBytes || INSPECTION_PHOTO_MAX_BYTES);

  for (const file of items) {
    const type = String(file.type || '').toLowerCase();
    if (type && !type.startsWith('image/')) {
      return {
        files: [],
        error: `${file.name} is not a supported image file.`,
      };
    }
    if (file.size > limit) {
      return {
        files: [],
        error: `${file.name} exceeds the ${formatFileSize(limit)} ${label} limit.`,
      };
    }
  }

  return { files: items, error: '' };
}

export function formatInspectionDate(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(parsed);
}

export function formatInspectionDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

export function formatReadinessScore(value) {
  const number = Number(value || 0);
  return `${number.toFixed(number % 1 === 0 ? 0 : 1)}%`;
}

export function getRoundStatusLabel(status) {
  const normalized = String(status || '').toUpperCase();
  if (normalized === 'CLOSED') return 'Closed';
  if (normalized === 'ARCHIVED') return 'Archived';
  return 'Active';
}

export function getStatusTone(status) {
  switch (String(status || '').toUpperCase()) {
    case 'RESOLVED':
      return 'positive';
    case 'READY_FOR_REVIEW':
      return 'warning';
    case 'IN_PROGRESS':
      return 'neutral';
    case 'OPEN':
    default:
      return 'danger';
  }
}

export function getSeverityTone(severity) {
  switch (String(severity || '').toUpperCase()) {
    case 'CRITICAL':
      return 'danger';
    case 'MAJOR':
      return 'warning';
    case 'MINOR':
      return 'neutral';
    case 'COSMETIC':
    default:
      return 'muted';
  }
}

export function countFromMap(map, key) {
  if (!map || typeof map !== 'object') return 0;
  return Number(map[key] || 0);
}

export function clampPlanCoordinate(value, fallback = 50) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(100, Math.max(0, number));
}

export function formatPlanCoordinate(planX, planY) {
  if (planX == null || planY == null) return 'No plan pin';
  return `${clampPlanCoordinate(planX).toFixed(1)}%, ${clampPlanCoordinate(planY).toFixed(1)}%`;
}

export function isInspectionDefectOverdue(defect) {
  if (!defect?.due_date || String(defect.status || '').toUpperCase() === 'RESOLVED') {
    return false;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(defect.due_date);
  due.setHours(0, 0, 0, 0);
  return Number.isFinite(due.getTime()) && due < today;
}
