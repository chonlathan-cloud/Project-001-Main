import {
  AlertTriangle,
  CheckCircle2,
  Info,
  TriangleAlert,
  X,
} from 'lucide-react';

const toneMeta = {
  success: { Icon: CheckCircle2, label: 'Success' },
  error: { Icon: AlertTriangle, label: 'Error' },
  warning: { Icon: TriangleAlert, label: 'Warning' },
  info: { Icon: Info, label: 'Information' },
};

export default function AdminToastRegion({
  toasts,
  pausedIds,
  onDismiss,
  onPause,
  onResume,
}) {
  return (
    <div className="admin-toast-region" aria-live="polite" aria-relevant="additions">
      {toasts.map((toast) => {
        const meta = toneMeta[toast.tone] || toneMeta.info;
        const { Icon } = meta;
        const isPaused = pausedIds.has(toast.id);

        return (
          <article
            key={toast.id}
            className={`admin-feedback-toast tone-${toast.tone}${isPaused ? ' is-paused' : ''}`}
            role={toast.tone === 'error' ? 'alert' : 'status'}
            aria-atomic="true"
            onMouseEnter={() => onPause(toast.id)}
            onMouseLeave={(event) => {
              if (!event.currentTarget.contains(document.activeElement)) onResume(toast.id);
            }}
            onFocus={() => onPause(toast.id)}
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) onResume(toast.id);
            }}
          >
            <span className="admin-feedback-toast-icon" aria-hidden="true">
              <Icon size={18} strokeWidth={2.2} />
            </span>
            <div className="admin-feedback-toast-copy">
              <span className="admin-feedback-toast-tone">{meta.label}</span>
              <strong>{toast.title}</strong>
              {toast.message ? <p>{toast.message}</p> : null}
            </div>
            <button
              type="button"
              className="admin-feedback-toast-dismiss"
              aria-label={`Dismiss ${meta.label.toLowerCase()} notification`}
              onClick={() => onDismiss(toast.id)}
            >
              <X size={17} />
            </button>
            {toast.durationMs > 0 ? (
              <span
                className="admin-feedback-toast-progress"
                aria-hidden="true"
                style={{ animationDuration: `${toast.durationMs}ms` }}
              />
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
