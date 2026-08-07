import React, { useEffect, useState } from 'react';
import { CalendarDays, CheckCircle2, Info } from 'lucide-react';
import FundDialogShell from './FundDialogShell';
import { createIdempotencyKey, formatMoney, isPositiveMoney, normalizeMoney } from './fundMoney';

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function FundOpeningBalanceDialog({ open, onClose, projectName, onSubmit, onSuccess }) {
  const [amount, setAmount] = useState('');
  const [activationMonth, setActivationMonth] = useState(currentMonthValue);
  const [reason, setReason] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);

  useEffect(() => {
    if (!open) return;
    setAmount('');
    setActivationMonth(currentMonthValue());
    setReason('');
    setConfirmed(false);
    setError('');
    setResult(null);
    setIsSubmitting(false);
    setIdempotencyKey(createIdempotencyKey());
  }, [open]);

  const effectiveDate = activationMonth ? `${activationMonth}-01` : '';
  const amountIsValid = isPositiveMoney(amount) || normalizeMoney(amount, '') === '0.00';

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!amountIsValid) {
      setError('Enter a valid amount with no more than two decimal places. An explicit zero balance is allowed.');
      return;
    }
    if (!activationMonth) {
      setError('Select the activation month.');
      return;
    }
    if (!reason.trim()) {
      setError('Reason is required for the audit trail.');
      return;
    }
    if (!confirmed) {
      setError('Confirm that Accounting/Admin has prepared and verified this opening figure.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const summary = await onSubmit({
        amount: normalizeMoney(amount),
        activationMonth,
        reason: reason.trim(),
        idempotencyKey,
      });
      setResult(summary);
      onSuccess?.(summary);
    } catch (submitError) {
      setError(submitError.message || 'The opening balance could not be activated.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <FundDialogShell
      open={open}
      onClose={isSubmitting ? () => {} : onClose}
      title="Set opening balance"
      description={`Activate the initial fund balance for ${projectName || 'Company Operations'}.`}
    >
      {result ? (
        <div className="fund-success-state" role="status">
          <CheckCircle2 size={38} />
          <h3>Opening balance activated</h3>
          <p>{formatMoney(result.openingBalance || amount)} effective {result.balanceStartDate || effectiveDate}</p>
          <button type="button" className="fund-button primary" onClick={onClose}>Done</button>
        </div>
      ) : (
        <form className="fund-form" onSubmit={handleSubmit} noValidate>
          <div className="fund-notice neutral">
            <Info size={17} />
            <span>This is the system’s initial balance, not customer income. It is stored as an immutable ledger entry.</span>
          </div>

          <div className="fund-field">
            <label htmlFor="opening-balance-amount">Initial opening balance (THB)</label>
            <input
              id="opening-balance-amount"
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => {
                setAmount(event.target.value.replace(/[^0-9.]/g, ''));
                setError('');
              }}
              placeholder="0.00"
              required
            />
            <small>Enter 0.00 when Accounting confirms an explicit zero opening balance.</small>
          </div>

          <div className="fund-field">
            <label htmlFor="opening-balance-month">Activation month</label>
            <div className="fund-input-with-icon">
              <CalendarDays size={16} />
              <input
                id="opening-balance-month"
                type="month"
                value={activationMonth}
                onChange={(event) => {
                  setActivationMonth(event.target.value);
                  setError('');
                }}
                required
              />
            </div>
            <small>Effective date is automatically set to {effectiveDate || 'the first day of the selected month'}.</small>
          </div>

          <div className="fund-field">
            <label htmlFor="opening-balance-reason">Reason</label>
            <textarea
              id="opening-balance-reason"
              rows={3}
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                setError('');
              }}
              placeholder="Source and preparation basis for this figure"
              required
            />
          </div>

          <section className="fund-preview" aria-label="Opening balance preview">
            <div className="fund-section-label">Activation Preview</div>
            <div className="fund-preview-grid compact">
              <div><span>Opening balance</span><strong>{formatMoney(amount)}</strong></div>
              <div><span>Effective date</span><strong>{effectiveDate || '-'}</strong></div>
            </div>
          </section>

          <label className="fund-confirmation-check">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => {
                setConfirmed(event.target.checked);
                setError('');
              }}
            />
            <span>Accounting/Admin prepared and verified this figure, and I confirm it as the Owner.</span>
          </label>

          {error ? <div className="fund-form-error" role="alert">{error}</div> : null}

          <footer className="fund-dialog-actions">
            <button type="button" className="fund-button secondary" onClick={onClose} disabled={isSubmitting}>Cancel</button>
            <button type="submit" className="fund-button primary" disabled={isSubmitting || !amountIsValid || !reason.trim() || !confirmed}>
              {isSubmitting ? 'Activating…' : `Confirm opening balance ${formatMoney(amount)}`}
            </button>
          </footer>
        </form>
      )}
    </FundDialogShell>
  );
}

export default FundOpeningBalanceDialog;
