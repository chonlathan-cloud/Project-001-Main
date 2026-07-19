export const statusTone = (status) => {
  const normalized = String(status || '').toUpperCase();
  if (['PUBLISHED', 'ACCEPTED', 'SENT'].includes(normalized)) return 'success';
  if (['CHANGES_REQUESTED', 'FAILED', 'OVERDUE'].includes(normalized)) return 'danger';
  if (['SUBMITTED', 'RESUBMITTED', 'PENDING_REVIEW', 'CORRECTION_DRAFT'].includes(normalized)) return 'warning';
  return 'neutral';
};

export const formatReportDate = (value, locale = 'en-GB') => {
  if (!value) return '—';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(locale, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }).format(date);
};

export const todayIso = () => {
  const date = new Date();
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60 * 1000).toISOString().slice(0, 10);
};
