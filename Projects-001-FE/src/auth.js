const SESSION_TOKEN_KEY = 'app_session_token';
const SESSION_USER_KEY = 'app_auth_user';
const PENDING_LINE_AUTH_KEY = 'app_pending_line_auth';
const AUTH_EVENT_NAME = 'app-auth-changed';

function parseJson(value, fallback = null) {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

export function getStoredSessionToken() {
  if (typeof window === 'undefined') return '';
  return String(window.localStorage.getItem(SESSION_TOKEN_KEY) || '').trim();
}

export function getStoredAuthUser() {
  if (typeof window === 'undefined') return null;
  return parseJson(window.localStorage.getItem(SESSION_USER_KEY), null);
}

export function getStoredPendingLineAuth() {
  if (typeof window === 'undefined') return null;
  return parseJson(window.localStorage.getItem(PENDING_LINE_AUTH_KEY), null);
}

function emitAuthChanged() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(AUTH_EVENT_NAME));
}

export function saveAuthSession(payload) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SESSION_TOKEN_KEY, payload.session_token || '');
  window.localStorage.setItem(SESSION_USER_KEY, JSON.stringify(payload.user || null));
  emitAuthChanged();
}

export function clearAuthSession() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.localStorage.removeItem(SESSION_USER_KEY);
  emitAuthChanged();
}

export function savePendingLineAuth(payload) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(PENDING_LINE_AUTH_KEY, JSON.stringify(payload));
}

export function clearPendingLineAuth() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(PENDING_LINE_AUTH_KEY);
}

export function subscribeToAuthChanges(listener) {
  if (typeof window === 'undefined') return () => {};

  const handleStorage = (event) => {
    if (!event.key || [SESSION_TOKEN_KEY, SESSION_USER_KEY, PENDING_LINE_AUTH_KEY].includes(event.key)) {
      listener();
    }
  };
  const handleCustom = () => listener();

  window.addEventListener('storage', handleStorage);
  window.addEventListener(AUTH_EVENT_NAME, handleCustom);

  return () => {
    window.removeEventListener('storage', handleStorage);
    window.removeEventListener(AUTH_EVENT_NAME, handleCustom);
  };
}

export function resolvePostLoginPath(user) {
  if (user?.role === 'subcontractor') {
    return '/input';
  }
  return '/';
}

export function isAdminUser(user) {
  return user?.role === 'admin';
}

export function isSubcontractorUser(user) {
  return user?.role === 'subcontractor';
}
