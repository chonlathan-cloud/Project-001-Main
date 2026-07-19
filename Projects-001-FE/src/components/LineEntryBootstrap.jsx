import React, { useEffect, useMemo, useState } from 'react';

import {
  initializeLineClient,
  isLiffPrimaryRedirect,
  resolveLineEntryPortal,
  resolveLineEntryTarget,
} from '../liffClient';
import { getStoredSessionToken } from '../auth';
import Loading from './Loading';

export default function LineEntryBootstrap({ children }) {
  const portal = useMemo(() => resolveLineEntryPortal(), []);
  const entryTarget = useMemo(() => resolveLineEntryTarget(), []);
  const primaryRedirect = useMemo(() => isLiffPrimaryRedirect(), []);
  const [ready, setReady] = useState(() => !portal);

  useEffect(() => {
    if (!portal) return undefined;

    let active = true;
    const restoreEntryTarget = () => {
      if (entryTarget && window.location.pathname !== entryTarget) {
        window.history.replaceState(window.history.state, '', entryTarget);
      }
    };

    const redirectToLineLogin = () => {
      const params = new URLSearchParams({
        portal,
        autoLine: '1',
      });
      if (entryTarget && entryTarget !== '/login') {
        params.set('returnTo', entryTarget);
      }
      const loginPath = `/login?${params.toString()}`;
      if (window.location.pathname !== '/login' || window.location.search !== `?${params.toString()}`) {
        window.history.replaceState(window.history.state, '', loginPath);
      }
    };

    initializeLineClient(portal)
      .then(() => {
        if (!active || primaryRedirect) return;
        if (!getStoredSessionToken()) {
          redirectToLineLogin();
        } else {
          restoreEntryTarget();
        }
        setReady(true);
      })
      .catch(() => {
        if (active) {
          if (!getStoredSessionToken()) {
            redirectToLineLogin();
          } else {
            restoreEntryTarget();
          }
          setReady(true);
        }
      });

    return () => {
      active = false;
    };
  }, [entryTarget, portal, primaryRedirect]);

  return ready ? children : <Loading />;
}
