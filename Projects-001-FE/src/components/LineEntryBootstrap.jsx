import React, { useEffect, useMemo, useState } from 'react';

import {
  initializeLineClient,
  isLiffPrimaryRedirect,
  resolveLineEntryPortal,
  resolveLineEntryTarget,
} from '../liffClient';
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

    initializeLineClient(portal)
      .then(() => {
        if (!active || primaryRedirect) return;
        restoreEntryTarget();
        setReady(true);
      })
      .catch(() => {
        if (active) {
          restoreEntryTarget();
          setReady(true);
        }
      });

    return () => {
      active = false;
    };
  }, [entryTarget, portal, primaryRedirect]);

  return ready ? children : <Loading />;
}
