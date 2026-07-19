import React from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';

export default function SidebarToggleButton({
  collapsed,
  onToggle,
  language = 'en',
}) {
  const label = language === 'th'
    ? (collapsed ? 'ขยายแถบเมนู' : 'ย่อแถบเมนู')
    : (collapsed ? 'Expand sidebar' : 'Collapse sidebar');
  const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <button
      type="button"
      className="sidebar-toggle-button"
      onClick={onToggle}
      aria-controls="primary-sidebar"
      aria-expanded={!collapsed}
      aria-label={label}
      title={label}
    >
      <ToggleIcon size={17} strokeWidth={2.2} aria-hidden="true" />
    </button>
  );
}
