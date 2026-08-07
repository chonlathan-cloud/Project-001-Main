import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Info, RefreshCw, Search } from 'lucide-react';
import { getProjectFundSummary } from '../../api';
import FundDialogShell from './FundDialogShell';
import {
  addMoney,
  compareMoney,
  createIdempotencyKey,
  formatMoney,
  isPositiveMoney,
  normalizeMoney,
  subtractMoney,
} from './fundMoney';

const ERROR_MESSAGES = {
  INSUFFICIENT_AVAILABLE_FUNDS: 'The amount is above the latest Available to Allocate balance.',
  STALE_FUND_BALANCE: 'The balance changed while this dialog was open. The latest balance is shown below.',
  INVALID_SOURCE_TARGET: 'Choose two different active fund buckets.',
  TARGET_BUCKET_INACTIVE: 'The destination bucket is no longer active.',
  OPERATIONS_BUCKET_MISSING: 'Company Operations is not configured. Contact the system administrator.',
  FORBIDDEN: 'Owner permission is required to allocate funds.',
};

function optionSort(left, right) {
  if (left.isOperations !== right.isOperations) return left.isOperations ? -1 : 1;
  return left.projectName.localeCompare(right.projectName);
}

function FundAllocationDialog({
  open,
  onClose,
  currentProject,
  currentSummary,
  options,
  direction = 'outgoing',
  onSubmit,
  onSuccess,
}) {
  const currentProjectId = currentProject?.projectId || currentProject?.id || '';
  const [sourceProjectId, setSourceProjectId] = useState('');
  const [targetProjectId, setTargetProjectId] = useState('');
  const [sourceSummary, setSourceSummary] = useState(currentSummary);
  const [searchValue, setSearchValue] = useState('');
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');
  const [formError, setFormError] = useState('');
  const [isLoadingSource, setIsLoadingSource] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);

  const activeOptions = useMemo(
    () => (Array.isArray(options) ? options : []).filter((option) => option.isActive).sort(optionSort),
    [options]
  );

  useEffect(() => {
    if (!open) return;
    const firstOther = activeOptions.find((option) => option.projectId !== currentProjectId);

    setSourceProjectId(direction === 'incoming' ? firstOther?.projectId || '' : currentProjectId);
    setTargetProjectId(direction === 'incoming' ? currentProjectId : firstOther?.projectId || '');
    setSourceSummary(direction === 'incoming' ? null : currentSummary);
    setSearchValue('');
    setAmount('');
    setReason('');
    setNote('');
    setFormError('');
    setResult(null);
    setIsSubmitting(false);
    setIdempotencyKey(createIdempotencyKey());
  }, [activeOptions, currentProjectId, currentSummary, direction, open]);

  useEffect(() => {
    if (!open || direction !== 'incoming' || !sourceProjectId) return undefined;
    let isActive = true;

    setIsLoadingSource(true);
    setFormError('');
    getProjectFundSummary(sourceProjectId)
      .then((summary) => {
        if (isActive) setSourceSummary(summary);
      })
      .catch((error) => {
        if (isActive) setFormError(error.message || 'Unable to load the source balance.');
      })
      .finally(() => {
        if (isActive) setIsLoadingSource(false);
      });

    return () => {
      isActive = false;
    };
  }, [direction, open, sourceProjectId]);

  const sourceOption = activeOptions.find((option) => option.projectId === sourceProjectId);
  const targetOption = activeOptions.find((option) => option.projectId === targetProjectId);
  const sourceName = sourceProjectId === currentProjectId ? currentProject?.name : sourceOption?.projectName;
  const targetName = targetProjectId === currentProjectId ? currentProject?.name : targetOption?.projectName;
  const available = sourceSummary?.availableToAllocate || sourceOption?.availableToAllocate || '0.00';
  const targetBefore = targetProjectId === currentProjectId
    ? currentSummary?.availableToAllocate || '0.00'
    : targetOption?.availableToAllocate || '0.00';
  const validAmount = isPositiveMoney(amount) && compareMoney(amount, available) !== 1;
  const sourceAfter = validAmount ? subtractMoney(available, amount) : available;
  const targetAfter = validAmount ? addMoney(targetBefore, amount) : targetBefore;

  const selectableOptions = activeOptions.filter((option) => {
    const lockedProjectId = direction === 'incoming' ? targetProjectId : sourceProjectId;
    const matchesSearch = option.projectName.toLowerCase().includes(searchValue.trim().toLowerCase());
    return option.projectId !== lockedProjectId && matchesSearch;
  });

  const validate = () => {
    if (!sourceProjectId || !targetProjectId || sourceProjectId === targetProjectId) {
      return 'Choose two different fund buckets.';
    }
    if (!isPositiveMoney(amount)) return 'Enter an amount greater than THB 0.00 with no more than two decimal places.';
    if (compareMoney(amount, available) === 1) return `The maximum available amount is ${formatMoney(available)}.`;
    if (!reason.trim()) return 'Reason is required for the audit trail.';
    return '';
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const validationMessage = validate();
    if (validationMessage) {
      setFormError(validationMessage);
      return;
    }

    try {
      setIsSubmitting(true);
      setFormError('');
      const allocation = await onSubmit({
        sourceProjectId,
        targetProjectId,
        amount: normalizeMoney(amount),
        currency: sourceSummary?.currency || 'THB',
        reason: reason.trim(),
        note: note.trim(),
        expectedSourceBalanceVersion: sourceSummary?.version || sourceOption?.balanceVersion || '',
        idempotencyKey,
      });
      setResult(allocation);
      onSuccess?.(allocation);
    } catch (error) {
      const code = String(error?.code || '').toUpperCase();
      if (code === 'STALE_FUND_BALANCE') {
        try {
          const refreshed = await getProjectFundSummary(sourceProjectId);
          setSourceSummary(refreshed);
        } catch {
          // Preserve the user's input and surface the original conflict.
        }
      }
      setFormError(ERROR_MESSAGES[code] || error.message || 'Allocation could not be posted.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <FundDialogShell
      open={open}
      onClose={isSubmitting ? () => {} : onClose}
      title={direction === 'incoming' ? 'Receive funds from a Project' : 'Allocate funds'}
      description="Review both balances before posting this immutable ledger movement."
      size="wide"
    >
      {result ? (
        <div className="fund-success-state" role="status">
          <CheckCircle2 size={38} />
          <h3>Allocation posted</h3>
          <p>Reference {result.referenceNo || result.id}</p>
          <div className="fund-preview-grid compact">
            <div><span>{sourceName} after</span><strong>{formatMoney(result.sourceBalanceAfter || sourceAfter)}</strong></div>
            <div><span>{targetName} after</span><strong>{formatMoney(result.targetBalanceAfter || targetAfter)}</strong></div>
          </div>
          <button type="button" className="fund-button primary" onClick={onClose}>Done</button>
        </div>
      ) : (
        <form className="fund-form" onSubmit={handleSubmit} noValidate>
          <div className="fund-transfer-route" aria-label="Allocation route">
            <div><span>From</span><strong>{sourceName || 'Select a Project'}</strong></div>
            <ArrowRight size={18} aria-hidden="true" />
            <div><span>To</span><strong>{targetName || 'Select a destination'}</strong></div>
          </div>

          <div className="fund-balance-callout">
            <span>Available from source</span>
            <strong>{isLoadingSource ? 'Refreshing…' : formatMoney(available)}</strong>
            {sourceSummary?.calculatedAt ? <small>Server-calculated {new Date(sourceSummary.calculatedAt).toLocaleString()}</small> : null}
          </div>

          <div className="fund-field">
            <label htmlFor="fund-project-search">
              {direction === 'incoming' ? 'Search source Project' : 'Search destination'}
            </label>
            <div className="fund-input-with-icon">
              <Search size={16} />
              <input
                id="fund-project-search"
                type="search"
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
                placeholder="Search active fund buckets"
              />
            </div>
          </div>

          <div className="fund-field">
            <label htmlFor="fund-project-select">
              {direction === 'incoming' ? 'From' : 'To'}
            </label>
            <select
              id="fund-project-select"
              value={direction === 'incoming' ? sourceProjectId : targetProjectId}
              onChange={(event) => {
                if (direction === 'incoming') {
                  setSourceSummary(null);
                  setSourceProjectId(event.target.value);
                } else {
                  setTargetProjectId(event.target.value);
                }
                setFormError('');
              }}
              required
            >
              <option value="">Select a Project</option>
              {selectableOptions.map((option) => (
                <option key={option.projectId} value={option.projectId}>
                  {option.projectName}{option.isOperations ? ' — Company Operations' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="fund-field">
            <div className="fund-label-row">
              <label htmlFor="fund-amount">Amount (THB)</label>
              <button
                type="button"
                className="fund-text-button"
                onClick={() => {
                  setAmount(normalizeMoney(available));
                  setFormError('');
                }}
                disabled={!isPositiveMoney(available)}
              >
                Use maximum
              </button>
            </div>
            <input
              id="fund-amount"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={amount}
              onChange={(event) => {
                setAmount(event.target.value.replace(/[^0-9.]/g, ''));
                setFormError('');
              }}
              placeholder="0.00"
              aria-describedby="fund-amount-help"
              required
            />
            <small id="fund-amount-help">Maximum {formatMoney(available)}. Two decimal places are supported.</small>
          </div>

          <div className="fund-field">
            <label htmlFor="fund-reason">Reason</label>
            <textarea
              id="fund-reason"
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                setFormError('');
              }}
              rows={3}
              placeholder="Why is this allocation needed?"
              required
            />
          </div>

          <div className="fund-field">
            <label htmlFor="fund-note">Reference / note <span>Optional</span></label>
            <input id="fund-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Working paper or internal reference" />
          </div>

          <section className="fund-preview" aria-label="Before and after preview">
            <div className="fund-section-label">Before / After Preview</div>
            <div className="fund-preview-grid">
              <div>
                <span>{sourceName || 'Source'}</span>
                <strong>{formatMoney(available)}</strong>
                <small>After {formatMoney(sourceAfter)}</small>
              </div>
              <div>
                <span>{targetName || 'Target'}</span>
                <strong>{formatMoney(targetBefore)}</strong>
                <small>After {formatMoney(targetAfter)}</small>
              </div>
            </div>
          </section>

          <div className="fund-notice"><Info size={17} /><span>This is an internal fund allocation. It does not initiate a bank transfer.</span></div>
          {formError ? <div className="fund-form-error" role="alert"><RefreshCw size={16} />{formError}</div> : null}

          <footer className="fund-dialog-actions">
            <button type="button" className="fund-button secondary" onClick={onClose} disabled={isSubmitting}>Cancel</button>
            <button type="submit" className="fund-button primary" disabled={isSubmitting || isLoadingSource || !validAmount || !reason.trim()}>
              {isSubmitting ? 'Posting allocation…' : `Confirm allocation ${formatMoney(amount)}`}
            </button>
          </footer>
        </form>
      )}
    </FundDialogShell>
  );
}

export default FundAllocationDialog;
