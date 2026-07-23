export function getEmbeddedBrowserInfo(userAgent = '') {
  const resolvedUserAgent = userAgent || (
    typeof window !== 'undefined' ? window.navigator.userAgent : ''
  );
  const isLine = /Line\/[\d.]+(?:\/IAB)?/i.test(resolvedUserAgent);
  const isAndroidWebView = /\bwv\b/i.test(resolvedUserAgent);

  return {
    isEmbedded: isLine || isAndroidWebView,
    isLine,
    isAndroid: /Android/i.test(resolvedUserAgent),
  };
}
