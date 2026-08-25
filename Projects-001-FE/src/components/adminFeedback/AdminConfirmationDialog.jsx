import { useEffect, useId, useRef } from 'react';
import { AlertTriangle, CircleHelp, X } from 'lucide-react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

export default function AdminConfirmationDialog({
  confirmation,
  inputValue,
  onInputChange,
  onCancel,
  onConfirm,
}) {
  const dialogRef = useRef(null);
  const cancelButtonRef = useRef(null);
  const inputRef = useRef(null);
  const previousFocusRef = useRef(null);
  const titleId = useId();
  const descriptionId = useId();
  const inputId = useId();

  useEffect(() => {
    if (!confirmation) return undefined;

    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    window.requestAnimationFrame(() => {
      if (confirmation.input) inputRef.current?.focus();
      else cancelButtonRef.current?.focus();
    });

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusable = Array.from(dialogRef.current.querySelectorAll(FOCUSABLE_SELECTOR));
      if (focusable.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocusRef.current?.focus?.();
    };
  }, [confirmation, onCancel]);

  if (!confirmation) return null;

  const isDanger = confirmation.tone === 'danger';
  const SymbolIcon = isDanger ? AlertTriangle : CircleHelp;
  const inputRequired = Boolean(confirmation.input?.required);
  const confirmDisabled = inputRequired && !inputValue.trim();

  const submit = (event) => {
    event.preventDefault();
    if (!confirmDisabled) onConfirm();
  };

  return (
    <div
      className="admin-confirmation-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        className={`admin-confirmation-dialog tone-${confirmation.tone}`}
        role={isDanger ? 'alertdialog' : 'dialog'}
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
      >
        <form onSubmit={submit}>
          <header className="admin-confirmation-header">
            <span className="admin-confirmation-symbol" aria-hidden="true">
              <SymbolIcon size={21} strokeWidth={2.2} />
            </span>
            <button
              type="button"
              className="admin-confirmation-close"
              onClick={onCancel}
              aria-label="Close confirmation dialog"
            >
              <X size={18} />
            </button>
          </header>

          <div className="admin-confirmation-copy">
            <h2 id={titleId}>{confirmation.title}</h2>
            <p id={descriptionId}>{confirmation.message}</p>
          </div>

          {confirmation.input ? (
            <label className="admin-confirmation-input" htmlFor={inputId}>
              <span>{confirmation.input.label}</span>
              <textarea
                ref={inputRef}
                id={inputId}
                value={inputValue}
                onChange={(event) => onInputChange(event.target.value)}
                placeholder={confirmation.input.placeholder}
                required={inputRequired}
                maxLength={confirmation.input.maxLength || 300}
              />
            </label>
          ) : null}

          <footer className="admin-confirmation-actions">
            <button ref={cancelButtonRef} type="button" onClick={onCancel}>
              {confirmation.cancelLabel}
            </button>
            <button
              type="submit"
              className={isDanger ? 'danger' : 'primary'}
              disabled={confirmDisabled}
            >
              {confirmation.confirmLabel}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
