import React from 'react';
import { ChevronDown } from 'lucide-react';

const buildInitials = (value) => {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return 'U';
  return words.slice(0, 2).map((word) => word.charAt(0).toUpperCase()).join('');
};

export function SettingsLocalNav({ items, activeTab, onTabChange }) {
  return (
    <nav className="settings-local-nav" aria-label="Settings sections" role="tablist">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.id === activeTab;

        return (
          <button
            key={item.id}
            type="button"
            className={isActive ? 'active' : ''}
            onClick={() => onTabChange(item.id)}
            role="tab"
            aria-selected={isActive}
          >
            <span className="settings-local-nav-icon">
              <Icon size={17} strokeWidth={2.2} />
            </span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export function SettingsPanel({ children, className = '' }) {
  return (
    <section className={`settings-panel${className ? ` ${className}` : ''}`}>
      {children}
    </section>
  );
}

export function SettingsPanelHeader({ kicker, title, description, action }) {
  return (
    <div className="settings-panel-header">
      <div>
        {kicker ? <span className="settings-kicker">{kicker}</span> : null}
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="settings-panel-action">{action}</div> : null}
    </div>
  );
}

export function SettingsAccordionItem({
  id,
  isOpen,
  onToggle,
  avatar,
  title,
  subtitle,
  meta,
  children,
}) {
  const triggerId = `${id}-trigger`;
  const panelId = `${id}-panel`;

  return (
    <article className={`settings-accordion-item${isOpen ? ' open' : ''}`}>
      <button
        id={triggerId}
        type="button"
        className="settings-accordion-trigger"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <span className="settings-accordion-main">
          {avatar}
          <span>
            <strong>{title}</strong>
            {subtitle ? <small>{subtitle}</small> : null}
          </span>
        </span>
        {meta ? <span className="settings-accordion-meta">{meta}</span> : null}
        <span className="settings-accordion-chevron" aria-hidden="true">
          <ChevronDown size={18} strokeWidth={2.3} />
        </span>
      </button>

      {isOpen ? (
        <div
          id={panelId}
          className="settings-accordion-panel"
          role="region"
          aria-labelledby={triggerId}
        >
          {children}
        </div>
      ) : null}
    </article>
  );
}

export function SettingsDetailGrid({ items }) {
  return (
    <div className="settings-detail-grid">
      {items.filter(Boolean).map((item) => (
        <div key={item.label} className={item.wide ? 'wide' : ''}>
          <span>{item.label}</span>
          <strong>{item.value || '-'}</strong>
        </div>
      ))}
    </div>
  );
}

export function SettingsNotice({ tone = 'info', children }) {
  return (
    <div className={`settings-notice ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      {children}
    </div>
  );
}

export function SettingsBadge({ tone = 'neutral', children }) {
  return <span className={`settings-badge ${tone}`}>{children}</span>;
}

export function SettingsAvatar({ name, imageUrl, size = 'md' }) {
  return (
    <span className={`settings-avatar ${size}`}>
      {imageUrl ? (
        <img src={imageUrl} alt={name || 'Avatar'} />
      ) : (
        <span>{buildInitials(name)}</span>
      )}
    </span>
  );
}

export function SettingsToggle({ checked, disabled = false, onChange, label, description }) {
  return (
    <button
      type="button"
      className={`settings-toggle-row${checked ? ' is-on' : ''}`}
      aria-pressed={checked}
      onClick={() => {
        if (!disabled) onChange(!checked);
      }}
      disabled={disabled}
    >
      <span>
        <strong>{label}</strong>
        {description ? <small>{description}</small> : null}
      </span>
      <span className="settings-toggle-track" aria-hidden="true">
        <span className="settings-toggle-thumb" />
      </span>
    </button>
  );
}

export function SettingsIntegrationCard({
  icon,
  name,
  description,
  status,
  tone = 'neutral',
  actionLabel,
  onAction,
}) {
  return (
    <article className="settings-integration-card">
      <div className="settings-integration-icon">
        {React.createElement(icon, { size: 19, strokeWidth: 2.2 })}
      </div>
      <div>
        <div className="settings-integration-head">
          <h3>{name}</h3>
          <SettingsBadge tone={tone}>{status}</SettingsBadge>
        </div>
        <p>{description}</p>
        {actionLabel ? <button type="button" onClick={onAction}>{actionLabel}</button> : null}
      </div>
    </article>
  );
}
