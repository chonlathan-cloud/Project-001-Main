import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import AdminConfirmationDialog from './AdminConfirmationDialog';
import AdminToastRegion from './AdminToastRegion';
import { AdminFeedbackContext } from './adminFeedbackContext';
import './adminFeedback.css';

const MAX_VISIBLE_TOASTS = 3;
const DEFAULT_DURATION_BY_TONE = {
  success: 4500,
  error: 8000,
  warning: 7000,
  info: 5000,
};
const ALLOWED_TOAST_TONES = new Set(Object.keys(DEFAULT_DURATION_BY_TONE));
const ALLOWED_CONFIRMATION_TONES = new Set(['default', 'danger']);

export default function AdminFeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [pausedIds, setPausedIds] = useState(new Set());
  const [confirmation, setConfirmation] = useState(null);
  const [inputValue, setInputValue] = useState('');
  const nextToastIdRef = useRef(0);
  const timersRef = useRef(new Map());
  const confirmationResolverRef = useRef(null);
  const inputValueRef = useRef('');

  const dismissToast = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (timer?.timeoutId) window.clearTimeout(timer.timeoutId);
    timersRef.current.delete(id);
    setPausedIds((current) => {
      if (!current.has(id)) return current;
      const next = new Set(current);
      next.delete(id);
      return next;
    });
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const scheduleToast = useCallback((id, durationMs) => {
    if (durationMs <= 0) return;
    const startedAt = Date.now();
    const timeoutId = window.setTimeout(() => dismissToast(id), durationMs);
    timersRef.current.set(id, { timeoutId, remainingMs: durationMs, startedAt });
  }, [dismissToast]);

  const notify = useCallback((input) => {
    const tone = ALLOWED_TOAST_TONES.has(input?.tone) ? input.tone : 'info';
    const durationMs = Number.isFinite(input?.durationMs)
      ? Math.max(0, input.durationMs)
      : DEFAULT_DURATION_BY_TONE[tone];
    const toast = {
      id: ++nextToastIdRef.current,
      tone,
      title: String(input?.title || 'Notification'),
      message: input?.message ? String(input.message) : '',
      durationMs,
    };

    setToasts((current) => {
      const retained = [...current, toast].slice(-MAX_VISIBLE_TOASTS);
      const retainedIds = new Set(retained.map((item) => item.id));
      current.forEach((item) => {
        if (retainedIds.has(item.id)) return;
        const timer = timersRef.current.get(item.id);
        if (timer?.timeoutId) window.clearTimeout(timer.timeoutId);
        timersRef.current.delete(item.id);
      });
      return retained;
    });
    scheduleToast(toast.id, durationMs);
    return toast.id;
  }, [scheduleToast]);

  const pauseToast = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (!timer?.timeoutId) return;
    window.clearTimeout(timer.timeoutId);
    const elapsedMs = Date.now() - timer.startedAt;
    timersRef.current.set(id, {
      timeoutId: null,
      remainingMs: Math.max(0, timer.remainingMs - elapsedMs),
      startedAt: 0,
    });
    setPausedIds((current) => new Set(current).add(id));
  }, []);

  const resumeToast = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (!timer || timer.timeoutId) return;
    setPausedIds((current) => {
      if (!current.has(id)) return current;
      const next = new Set(current);
      next.delete(id);
      return next;
    });
    if (timer.remainingMs <= 0) dismissToast(id);
    else scheduleToast(id, timer.remainingMs);
  }, [dismissToast, scheduleToast]);

  const requestConfirmation = useCallback((options) => {
    confirmationResolverRef.current?.({ confirmed: false, inputValue: '' });
    const nextConfirmation = {
      title: String(options?.title || 'Confirm action'),
      message: String(options?.message || 'Continue with this action?'),
      confirmLabel: String(options?.confirmLabel || 'Confirm'),
      cancelLabel: String(options?.cancelLabel || 'Cancel'),
      tone: ALLOWED_CONFIRMATION_TONES.has(options?.tone) ? options.tone : 'default',
      input: options?.input || null,
    };
    inputValueRef.current = '';
    setInputValue('');
    setConfirmation(nextConfirmation);

    return new Promise((resolve) => {
      confirmationResolverRef.current = resolve;
    });
  }, []);

  const closeConfirmation = useCallback((confirmed) => {
    confirmationResolverRef.current?.({
      confirmed,
      inputValue: confirmed ? inputValueRef.current.trim() : '',
    });
    confirmationResolverRef.current = null;
    inputValueRef.current = '';
    setInputValue('');
    setConfirmation(null);
  }, []);

  const updateInputValue = useCallback((value) => {
    inputValueRef.current = value;
    setInputValue(value);
  }, []);

  const cancelConfirmation = useCallback(() => {
    closeConfirmation(false);
  }, [closeConfirmation]);

  const confirmAction = useCallback(() => {
    closeConfirmation(true);
  }, [closeConfirmation]);

  useEffect(() => () => {
    timersRef.current.forEach((timer) => {
      if (timer.timeoutId) window.clearTimeout(timer.timeoutId);
    });
    timersRef.current.clear();
    confirmationResolverRef.current?.({ confirmed: false, inputValue: '' });
    confirmationResolverRef.current = null;
  }, []);

  const contextValue = useMemo(
    () => ({ notify, requestConfirmation }),
    [notify, requestConfirmation],
  );

  return (
    <AdminFeedbackContext.Provider value={contextValue}>
      {children}
      <AdminToastRegion
        toasts={toasts}
        pausedIds={pausedIds}
        onDismiss={dismissToast}
        onPause={pauseToast}
        onResume={resumeToast}
      />
      <AdminConfirmationDialog
        confirmation={confirmation}
        inputValue={inputValue}
        onInputChange={updateInputValue}
        onCancel={cancelConfirmation}
        onConfirm={confirmAction}
      />
    </AdminFeedbackContext.Provider>
  );
}
