import liff from '@line/liff';

const defaultLiffId = import.meta.env.VITE_LINE_LIFF_ID;
const subcontractorLiffId = import.meta.env.VITE_LINE_SUBCONTRACTOR_LIFF_ID || defaultLiffId;
const customerLiffId = import.meta.env.VITE_LINE_CUSTOMER_LIFF_ID;

let initPromise = null;
let initializedPortal = '';

function normalizePath(value = '') {
  const rawValue = String(value || '').trim();
  if (!rawValue) return '';

  let decodedValue = rawValue;
  try {
    decodedValue = decodeURIComponent(rawValue);
  } catch {
    // URLSearchParams normally decodes this value. Keep the original if it is malformed.
  }

  const path = decodedValue.split(/[?#]/, 1)[0];
  if (!path) return '';
  return path.startsWith('/') ? path : `/${path}`;
}

function resolveLiffId(portal = 'subcontractor') {
  return portal === 'customer' ? customerLiffId : subcontractorLiffId;
}

function resolvePortalFromClientId(clientId = '') {
  const normalizedClientId = String(clientId || '').trim();
  if (!normalizedClientId) return '';

  if (
    subcontractorLiffId === normalizedClientId
    || subcontractorLiffId?.startsWith(`${normalizedClientId}-`)
  ) {
    return 'subcontractor';
  }
  if (
    customerLiffId === normalizedClientId
    || customerLiffId?.startsWith(`${normalizedClientId}-`)
  ) {
    return 'customer';
  }
  return '';
}

async function ensureLiff(portal = 'subcontractor') {
  const liffId = resolveLiffId(portal);
  if (!liffId) {
    throw new Error(
      portal === 'customer'
        ? 'Missing VITE_LINE_CUSTOMER_LIFF_ID.'
        : 'Missing VITE_LINE_SUBCONTRACTOR_LIFF_ID.',
    );
  }

  if (initializedPortal && initializedPortal !== portal) {
    window.location.reload();
    return null;
  }
  if (!initPromise) {
    initializedPortal = portal;
    initPromise = liff
      .init({
        liffId,
        withLoginOnExternalBrowser: true,
      })
      .catch((error) => {
        initPromise = null;
        initializedPortal = '';
        throw error;
      });
  }

  await initPromise;
  return liff;
}

export function resolveLineEntryPortal(currentLocation = window.location) {
  const searchParams = new URLSearchParams(currentLocation.search);
  const currentPath = normalizePath(currentLocation.pathname);
  const liffStatePath = normalizePath(searchParams.get('liff.state'));
  const candidatePath = liffStatePath || currentPath;
  const hasLiffState = searchParams.has('liff.state');

  if (candidatePath.startsWith('/project-reports')) {
    return 'customer';
  }
  if (candidatePath.startsWith('/daily-reports/me')) {
    return 'subcontractor';
  }
  if (candidatePath.startsWith('/payment-confirmation')) {
    return 'subcontractor';
  }
  if (
    hasLiffState &&
    (candidatePath === '/input' ||
      candidatePath.startsWith('/inspection/tasks') ||
      candidatePath.startsWith('/profile/me') ||
      candidatePath === '/login')
  ) {
    return 'subcontractor';
  }
  const callbackPortal = resolvePortalFromClientId(searchParams.get('liffClientId'));
  if (callbackPortal) {
    return callbackPortal;
  }
  if (
    currentPath === '/auth/line/callback'
    || (currentPath === '/login' && searchParams.get('autoLine') === '1')
  ) {
    return searchParams.get('portal') === 'customer' ? 'customer' : 'subcontractor';
  }
  return '';
}

export function resolveLineEntryTarget(currentLocation = window.location) {
  const searchParams = new URLSearchParams(currentLocation.search);
  const currentPath = normalizePath(currentLocation.pathname);
  const liffStatePath = normalizePath(searchParams.get('liff.state'));
  const candidatePath = liffStatePath || currentPath;

  if (candidatePath.startsWith('/project-reports')) {
    return '/project-reports';
  }
  if (candidatePath.startsWith('/daily-reports/me')) {
    return '/daily-reports/me';
  }
  if (candidatePath.startsWith('/payment-confirmation')) {
    return '/payment-confirmation';
  }
  if (candidatePath === '/input') {
    return '/input';
  }
  if (candidatePath.startsWith('/inspection/tasks')) {
    return '/inspection/tasks';
  }
  if (candidatePath.startsWith('/profile/me')) {
    return '/profile/me';
  }
  if (candidatePath === '/login') {
    return '/login';
  }

  const callbackPortal = resolvePortalFromClientId(searchParams.get('liffClientId'));
  if (callbackPortal === 'customer') {
    return '/project-reports';
  }
  if (callbackPortal === 'subcontractor') {
    return '/daily-reports/me';
  }
  return '';
}

export function isLiffPrimaryRedirect(currentLocation = window.location) {
  return new URLSearchParams(currentLocation.search).has('liff.state');
}

export async function initializeLineClient(portal = 'subcontractor') {
  return ensureLiff(portal);
}

export async function beginLineLogin(portal = 'subcontractor', returnTo = '') {
  const liffClient = await ensureLiff(portal);
  if (!liffClient) return null;
  if (!liffClient.isLoggedIn()) {
    const query = new URLSearchParams({ portal });
    if (returnTo) query.set('returnTo', returnTo);
    liffClient.login({
      redirectUri: `${window.location.origin}/auth/line/callback?${query.toString()}`,
    });
    return null;
  }
  return liffClient;
}

export async function getActiveLineAccessToken(portal = 'subcontractor') {
  const liffClient = await ensureLiff(portal);
  if (!liffClient) return null;
  if (!liffClient.isLoggedIn()) {
    return null;
  }
  return liffClient.getAccessToken();
}

export async function getActiveLineProfile(portal = 'subcontractor') {
  const liffClient = await ensureLiff(portal);
  if (!liffClient) return null;
  if (!liffClient.isLoggedIn()) {
    return null;
  }

  return liffClient.getProfile();
}

export async function logoutLineClient() {
  const liffClient = await ensureLiff(initializedPortal || 'subcontractor');
  if (!liffClient) return;
  if (liffClient.isLoggedIn()) {
    liffClient.logout();
  }
}
