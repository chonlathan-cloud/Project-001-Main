import { AlertTriangle, Info } from 'lucide-react';

export default function AuthNotice({ notice }) {
  if (!notice?.title && !notice?.message) return null;

  const tone = notice.tone === 'error' ? 'error' : 'warning';
  const Icon = tone === 'error' ? AlertTriangle : Info;

  return (
    <div className={`auth-notice ${tone}`} role="status" aria-live="polite">
      <span className="auth-notice-icon">
        <Icon size={17} />
      </span>
      <span>
        {notice.title ? <strong>{notice.title}</strong> : null}
        {notice.message ? <small>{notice.message}</small> : null}
      </span>
    </div>
  );
}
