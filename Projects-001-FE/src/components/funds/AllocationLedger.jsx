import React, { useEffect, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Eye, RotateCcw } from 'lucide-react';
import { getProjectFundSummary } from '../../api';
import FundDialogShell from './FundDialogShell';
import {
  addMoney,
  compareMoney,
  createIdempotencyKey,
  formatMoney,
  subtractMoney,
} from './fundMoney';

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed);
}

function AllocationLedger({
  projectId,
  items,
  loading,
  error,
  canReverse,
  onReverse,
  onLoadMore,
  hasMore,
}) {
  const [selected, setSelected] = useState(null);
  const [reversalReason, setReversalReason] = useState('');
  const [reversalError, setReversalError] = useState('');
  const [isReversing, setIsReversing] = useState(false);
  const [reverseSourceSummary, setReverseSourceSummary] = useState(null);
  const [reverseTargetSummary, setReverseTargetSummary] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (!selected) return undefined;
    let isActive = true;
    setReversalReason('');
    setReversalError('');
    setReverseSourceSummary(null);
    setReverseTargetSummary(null);

    if (!canReverse || selected.status !== 'POSTED' || selected.reversalOf) return undefined;
    if (!selected.target.projectId || !selected.source.projectId) return undefined;

    setPreviewLoading(true);
    Promise.all([
      getProjectFundSummary(selected.target.projectId),
      getProjectFundSummary(selected.source.projectId),
    ])
      .then(([sourceSummary, targetSummary]) => {
        if (!isActive) return;
        setReverseSourceSummary(sourceSummary);
        setReverseTargetSummary(targetSummary);
      })
      .catch((previewError) => {
        if (isActive) setReversalError(previewError.message || 'Unable to load the latest reversal preview.');
      })
      .finally(() => {
        if (isActive) setPreviewLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [canReverse, selected]);

  const reverseAvailable = reverseSourceSummary?.availableToAllocate || '0.00';
  const reverseTargetBefore = reverseTargetSummary?.availableToAllocate || '0.00';
  const reversalWouldOverdraw = selected ? compareMoney(selected.amount, reverseAvailable) === 1 : false;
  const canReverseSelected = Boolean(
    canReverse &&
    selected?.status === 'POSTED' &&
    !selected?.reversalOf &&
    !reversalWouldOverdraw &&
    reverseSourceSummary &&
    reverseTargetSummary
  );

  const submitReversal = async (event) => {
    event.preventDefault();
    if (!reversalReason.trim()) {
      setReversalError('Reversal reason is required.');
      return;
    }
    if (reversalWouldOverdraw) {
      setReversalError('Reverse is blocked because the returning bucket does not have enough Available balance.');
      return;
    }

    try {
      setIsReversing(true);
      setReversalError('');
      await onReverse(selected, {
        reason: reversalReason.trim(),
        expectedSourceBalanceVersion: reverseSourceSummary?.version || '',
        idempotencyKey: createIdempotencyKey(),
      });
      setSelected(null);
    } catch (reverseError) {
      const code = String(reverseError?.code || '').toUpperCase();
      if (code === 'REVERSAL_WOULD_OVERDRAW_TARGET') {
        setReversalError('Reverse is blocked because the returning bucket no longer has enough Available balance.');
      } else if (code === 'ALLOCATION_ALREADY_REVERSED') {
        setReversalError('This allocation has already been reversed.');
      } else {
        setReversalError(reverseError.message || 'The allocation could not be reversed.');
      }
    } finally {
      setIsReversing(false);
    }
  };

  return (
    <section className="fund-ledger-section">
      <div className="fund-section-heading">
        <div>
          <span className="fund-kicker">AUDITABLE HISTORY</span>
          <h2>Allocation Ledger</h2>
          <p>Posted movements remain immutable. Corrections create a linked reversal.</p>
        </div>
      </div>

      <div className="fund-ledger-card">
        {loading ? <div className="fund-empty-state">Loading allocation history…</div> : null}
        {!loading && error ? <div className="fund-inline-error" role="alert">{error}</div> : null}
        {!loading && !error && items.length === 0 ? (
          <div className="fund-empty-state">
            <strong>No fund allocations yet</strong>
            <span>Posted allocations and reversals will appear here.</span>
          </div>
        ) : null}

        {!loading && !error && items.length > 0 ? (
          <>
            <div className="fund-ledger-table-wrap">
              <table className="fund-ledger-table">
                <thead>
                  <tr>
                    <th>Direction</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Amount</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Created by</th>
                    <th>Created at</th>
                    <th><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((allocation) => {
                    const incoming = allocation.target.projectId === projectId;
                    const DirectionIcon = incoming ? ArrowDownLeft : ArrowUpRight;
                    return (
                      <tr key={allocation.id}>
                        <td><span className={`fund-direction ${incoming ? 'in' : 'out'}`}><DirectionIcon size={14} />{incoming ? 'Allocated In' : 'Allocated Out'}</span></td>
                        <td>{allocation.source.projectName}</td>
                        <td>{allocation.target.projectName}</td>
                        <td className="fund-money-cell">{incoming ? '+' : '−'}{formatMoney(allocation.amount)}</td>
                        <td className="fund-reason-cell">{allocation.reason || '-'}</td>
                        <td><span className={`fund-status ${allocation.status.toLowerCase()}`}>{allocation.status}</span></td>
                        <td>{allocation.createdBy}</td>
                        <td>{formatDateTime(allocation.createdAt)}</td>
                        <td>
                          <button type="button" className="fund-icon-button" onClick={() => setSelected(allocation)} aria-label={`View allocation ${allocation.referenceNo || allocation.id}`}>
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="fund-ledger-mobile">
              {items.map((allocation) => {
                const incoming = allocation.target.projectId === projectId;
                return (
                  <button key={allocation.id} type="button" className="fund-ledger-mobile-row" onClick={() => setSelected(allocation)}>
                    <span className={`fund-direction ${incoming ? 'in' : 'out'}`}>{incoming ? 'Allocated In' : 'Allocated Out'}</span>
                    <strong>{incoming ? '+' : '−'}{formatMoney(allocation.amount)}</strong>
                    <small>{allocation.source.projectName} → {allocation.target.projectName}</small>
                    <small>{formatDateTime(allocation.createdAt)} · {allocation.status}</small>
                  </button>
                );
              })}
            </div>
          </>
        ) : null}

        {hasMore ? (
          <div className="fund-load-more"><button type="button" className="fund-button secondary" onClick={onLoadMore}>Load more</button></div>
        ) : null}
      </div>

      <FundDialogShell
        open={Boolean(selected)}
        onClose={isReversing ? () => {} : () => setSelected(null)}
        title={`Allocation ${selected?.referenceNo || selected?.id || ''}`}
        description="Ledger detail and reversal relationship"
        size="wide"
      >
        {selected ? (
          <div className="fund-allocation-detail">
            <div className="fund-detail-grid">
              <div><span>From</span><strong>{selected.source.projectName}</strong></div>
              <div><span>To</span><strong>{selected.target.projectName}</strong></div>
              <div><span>Amount</span><strong>{formatMoney(selected.amount)}</strong></div>
              <div><span>Status</span><strong>{selected.status}</strong></div>
              <div><span>Created by</span><strong>{selected.createdBy}</strong></div>
              <div><span>Created at</span><strong>{formatDateTime(selected.createdAt)}</strong></div>
            </div>
            <div className="fund-detail-reason"><span>Reason</span><p>{selected.reason || '-'}</p></div>
            {selected.note ? <div className="fund-detail-reason"><span>Reference / note</span><p>{selected.note}</p></div> : null}
            {selected.reversalOf ? <div className="fund-notice neutral">Reversal of allocation {selected.reversalOf}</div> : null}

            {canReverse && selected.status === 'POSTED' && !selected.reversalOf ? (
              <form className="fund-reversal-panel" onSubmit={submitReversal}>
                <div className="fund-section-label"><RotateCcw size={15} /> Reverse allocation</div>
                <p>This creates the opposite immutable allocation. The original ledger entries are retained.</p>

                {previewLoading ? <div className="fund-empty-state small">Loading latest balances…</div> : null}
                {!previewLoading && reverseSourceSummary && reverseTargetSummary ? (
                  <div className="fund-preview-grid">
                    <div>
                      <span>{selected.target.projectName} returns</span>
                      <strong>{formatMoney(reverseAvailable)}</strong>
                      <small>After {formatMoney(subtractMoney(reverseAvailable, selected.amount))}</small>
                    </div>
                    <div>
                      <span>{selected.source.projectName} receives</span>
                      <strong>{formatMoney(reverseTargetBefore)}</strong>
                      <small>After {formatMoney(addMoney(reverseTargetBefore, selected.amount))}</small>
                    </div>
                  </div>
                ) : null}

                {reversalWouldOverdraw ? (
                  <div className="fund-form-error" role="alert">Reverse blocked: the returning bucket has only {formatMoney(reverseAvailable)} available.</div>
                ) : null}

                <div className="fund-field">
                  <label htmlFor="fund-reversal-reason">Reversal reason</label>
                  <textarea id="fund-reversal-reason" rows={3} value={reversalReason} onChange={(event) => setReversalReason(event.target.value)} required />
                </div>
                {reversalError ? <div className="fund-form-error" role="alert">{reversalError}</div> : null}
                <div className="fund-dialog-actions">
                  <button type="submit" className="fund-button danger" disabled={!canReverseSelected || !reversalReason.trim() || isReversing}>
                    {isReversing ? 'Posting reversal…' : `Reverse ${formatMoney(selected.amount)}`}
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        ) : null}
      </FundDialogShell>
    </section>
  );
}

export default AllocationLedger;
