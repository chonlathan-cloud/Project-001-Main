import liff from '@line/liff';

const liffId = import.meta.env.VITE_LINE_LIFF_ID;

let initPromise = null;

async function ensureLiff() {
  if (!liffId) {
    throw new Error('Missing VITE_LINE_LIFF_ID.');
  }

  if (!initPromise) {
    initPromise = liff.init({
      liffId,
      withLoginOnExternalBrowser: true,
    });
  }

  await initPromise;
  return liff;
}

export async function beginLineLogin() {
  const liffClient = await ensureLiff();
  if (!liffClient.isLoggedIn()) {
    liffClient.login({ redirectUri: `${window.location.origin}/auth/line/callback` });
    return null;
  }
  return liffClient;
}

export async function getActiveLineAccessToken() {
  const liffClient = await ensureLiff();
  if (!liffClient.isLoggedIn()) {
    return null;
  }
  return liffClient.getAccessToken();
}

export async function getActiveLineProfile() {
  const liffClient = await ensureLiff();
  if (!liffClient.isLoggedIn()) {
    return null;
  }

  return liffClient.getProfile();
}

export async function logoutLineClient() {
  const liffClient = await ensureLiff();
  if (liffClient.isLoggedIn()) {
    liffClient.logout();
  }
}
