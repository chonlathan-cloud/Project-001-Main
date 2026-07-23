import React, { useState } from 'react';
import { Check, Copy, ExternalLink, Smartphone } from 'lucide-react';
import { getEmbeddedBrowserInfo } from './embeddedBrowserUtils';

function buildExternalBrowserUrl(currentUrl, isAndroid) {
  if (!currentUrl || !isAndroid) return currentUrl;

  try {
    const parsedUrl = new URL(currentUrl);
    const scheme = parsedUrl.protocol.replace(':', '') || 'https';
    return `intent://${parsedUrl.host}${parsedUrl.pathname}${parsedUrl.search}#Intent;scheme=${scheme};package=com.android.chrome;S.browser_fallback_url=${encodeURIComponent(currentUrl)};end`;
  } catch {
    return currentUrl;
  }
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textArea = document.createElement('textarea');
  textArea.value = value;
  textArea.setAttribute('readonly', '');
  textArea.style.position = 'fixed';
  textArea.style.opacity = '0';
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand('copy');
  document.body.removeChild(textArea);
}

export default function ExternalBrowserLoginNotice({
  browserInfo = getEmbeddedBrowserInfo(),
  lineAlternative = '',
}) {
  const [copyState, setCopyState] = useState('idle');
  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
  const externalBrowserUrl = buildExternalBrowserUrl(currentUrl, browserInfo.isAndroid);
  const browserName = browserInfo.isLine ? 'LINE' : 'แอปอื่น';

  const handleCopy = async () => {
    try {
      await copyText(currentUrl);
      setCopyState('copied');
    } catch {
      setCopyState('error');
    }
  };

  return (
    <aside className="external-browser-login-notice" role="alert" aria-live="polite">
      <div className="external-browser-login-heading">
        <span className="external-browser-login-icon" aria-hidden="true">
          <Smartphone size={19} />
        </span>
        <div>
          <strong>กรุณาเปิดหน้านี้ด้วย Chrome</strong>
          <p>
            ขณะนี้คุณเปิด RAYADEE ผ่าน {browserName} ซึ่งไม่รองรับการเข้าสู่ระบบด้วย Google
          </p>
        </div>
      </div>

      <div className="external-browser-login-actions">
        <a
          className="external-browser-login-primary"
          href={externalBrowserUrl}
          target={browserInfo.isAndroid ? undefined : '_blank'}
          rel={browserInfo.isAndroid ? undefined : 'noreferrer'}
        >
          <ExternalLink size={17} aria-hidden="true" />
          เปิดด้วย Chrome
        </a>
        <button type="button" onClick={handleCopy}>
          {copyState === 'copied' ? <Check size={17} aria-hidden="true" /> : <Copy size={17} aria-hidden="true" />}
          {copyState === 'copied'
            ? 'คัดลอกแล้ว'
            : copyState === 'error'
              ? 'คัดลอกไม่สำเร็จ'
              : 'คัดลอกลิงก์'}
        </button>
      </div>

      <small>
        หรือกดเมนู ⋮ ด้านบน แล้วเลือก “เปิดในเบราว์เซอร์”
        {lineAlternative ? ` ${lineAlternative}` : ''}
      </small>
    </aside>
  );
}
