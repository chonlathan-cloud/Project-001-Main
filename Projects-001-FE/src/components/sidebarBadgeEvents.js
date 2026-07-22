export const SIDEBAR_BADGES_REFRESH_EVENT = 'app-sidebar-badges-refresh';

export function requestSidebarBadgeRefresh() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(SIDEBAR_BADGES_REFRESH_EVENT));
}
