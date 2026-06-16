const SESSION_TOKEN_KEY = 'app_session_token';
const SESSION_USER_KEY = 'app_auth_user';
const PENDING_LINE_AUTH_KEY = 'app_pending_line_auth';
const AUTH_NOTICE_KEY = 'app_auth_notice';
const AUTH_EVENT_NAME = 'app-auth-changed';
const ADMIN_ROLES = new Set(['admin', 'owner', 'super_admin']);

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

export function updateStoredAuthUser(patch) {
  if (typeof window === 'undefined') return null;
  const current = getStoredAuthUser() || {};
  const nextUser = { ...current, ...(patch || {}) };
  window.localStorage.setItem(SESSION_USER_KEY, JSON.stringify(nextUser));
  emitAuthChanged();
  return nextUser;
}

export function getStoredPendingLineAuth() {
  if (typeof window === 'undefined') return null;
  return parseJson(window.localStorage.getItem(PENDING_LINE_AUTH_KEY), null);
}

export function saveAuthNotice(notice) {
  if (typeof window === 'undefined') return;
  const payload = {
    code: String(notice?.code || '').trim(),
    tone: String(notice?.tone || 'info').trim(),
    title: String(notice?.title || '').trim(),
    message: String(notice?.message || '').trim(),
  };
  if (!payload.title && !payload.message) {
    window.localStorage.removeItem(AUTH_NOTICE_KEY);
    return;
  }
  window.localStorage.setItem(AUTH_NOTICE_KEY, JSON.stringify(payload));
}

export function getStoredAuthNotice() {
  if (typeof window === 'undefined') return null;
  return parseJson(window.localStorage.getItem(AUTH_NOTICE_KEY), null);
}

export function clearAuthNotice() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(AUTH_NOTICE_KEY);
}

export function consumeAuthNotice() {
  if (typeof window === 'undefined') return null;
  const notice = getStoredAuthNotice();
  clearAuthNotice();
  return notice;
}

function emitAuthChanged() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(AUTH_EVENT_NAME));
}

export function saveAuthSession(payload) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SESSION_TOKEN_KEY, payload.session_token || '');
  window.localStorage.setItem(SESSION_USER_KEY, JSON.stringify(payload.user || null));
  window.localStorage.removeItem(AUTH_NOTICE_KEY);
  emitAuthChanged();
}

export function clearAuthSession({ preserveNotice = false } = {}) {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.localStorage.removeItem(SESSION_USER_KEY);
  if (!preserveNotice) {
    window.localStorage.removeItem(AUTH_NOTICE_KEY);
  }
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
    if (!event.key || [SESSION_TOKEN_KEY, SESSION_USER_KEY, PENDING_LINE_AUTH_KEY, AUTH_NOTICE_KEY].includes(event.key)) {
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
  if (isSubcontractorUser(user)) {
    return '/input';
  }
  if (isOwnerUser(user)) {
    return '/';
  }
  if (isAdminUser(user)) {
    return '/project';
  }
  return '/';
}

const normalizeRole = (user) => String(user?.role || '').trim().toLowerCase();
const normalizeAccessLevel = (user) => String(user?.access_level || user?.accessLevel || '').trim().toLowerCase();

export function isOwnerUser(user) {
  const role = normalizeRole(user);
  const accessLevel = normalizeAccessLevel(user);

  return (
    role === 'owner' ||
    role === 'super_admin' ||
    accessLevel === 'owner' ||
    user?.is_owner === true ||
    // Preserve the existing production contract until backend sends owner/admin separately.
    (role === 'admin' && user?.is_owner !== false && !accessLevel)
  );
}

export function isAdminUser(user) {
  return ADMIN_ROLES.has(normalizeRole(user));
}

export function isAdminPortalUser(user) {
  return isAdminUser(user) || isOwnerUser(user);
}

export function isSubcontractorUser(user) {
  return normalizeRole(user) === 'subcontractor';
}

export function canAccessOwnerArea(user) {
  return isOwnerUser(user);
}

export function canMutateAdminData(user) {
  return isOwnerUser(user);
}
