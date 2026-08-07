import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowLeftRight,
  BadgeDollarSign,
  CalendarRange,
  CircleDollarSign,
  Landmark,
  LockKeyhole,
  ShieldAlert,
  WalletCards,
} from 'lucide-react';
import {
  createFundAllocation,
  getFundAllocations,
  getFundBucketOptions,
  getProjectFundSummary,
  reverseFundAllocation,
  setFundOpeningBalance,
} from '../../api';
import AllocationLedger from './AllocationLedger';
import FundAllocationDialog from './FundAllocationDialog';
import FundOpeningBalanceDialog from './FundOpeningBalanceDialog';
import { formatMoney, isPositiveMoney } from './fundMoney';
import './funds.css';

function SummaryMetric({ icon: Icon, label, value, badge, description, tone = 'neutral', action }) {
  const iconElement = React.createElement(Icon, { size: 19 });
  return (
    <article className={`fund-summary-card ${tone}`}>
      <div className="fund-summary-card-top">
        <span className="fund-summary-icon">{iconElement}</span>
        {badge ? <span className="fund-badge">{badge}</span> : null}
      </div>
      <div>
        <span className="fund-summary-label">{label}</span>
        <strong className="fund-summary-value">{value}</strong>
      </div>
      <p>{description}</p>
      {action ? <div className="fund-summary-action">{action}</div> : null}
    </article>
  );
}

function ProjectFundsWorkspace({ project, projectedMargin = '0.00', canMutate = false, initialAction = '' }) {
  const projectId = project?.projectId || project?.id || '';
  const isOperations = Boolean(project?.isSystemOperations || project?.systemKey === 'OPERATIONS');
  const [summary, setSummary] = useState(null);
  const [options, setOptions] = useState([]);
  const [allocations, setAllocations] = useState([]);
  const [nextCursor, setNextCursor] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [ledgerLoading, setLedgerLoading] = useState(true);
  const [summaryError, setSummaryError] = useState('');
  const [ledgerError, setLedgerError] = useState('');
  const [dialogDirection, setDialogDirection] = useState('');
  const [openingDialogOpen, setOpeningDialogOpen] = useState(false);
  const initialActionHandled = useRef(false);
  const mutationsAllowed = canMutate && summary?.mutationsEnabled !== false;

  const loadFunds = useCallback(async () => {
    if (!projectId) return;
    setSummaryLoading(true);
    setLedgerLoading(true);
    setSummaryError('');
    setLedgerError('');

    const [summaryResult, optionsResult, ledgerResult] = await Promise.allSettled([
      getProjectFundSummary(projectId),
      getFundBucketOptions(),
      getFundAllocations({ projectId }),
    ]);

    if (summaryResult.status === 'fulfilled') {
      setSummary(summaryResult.value);
    } else {
      setSummary(null);
      setSummaryError(
        summaryResult.reason?.code === 'NOT_FOUND'
          ? 'Fund allocation is not configured for this environment yet.'
          : summaryResult.reason?.message || 'Unable to load the fund summary.'
      );
    }

    if (optionsResult.status === 'fulfilled') setOptions(optionsResult.value);
    else setOptions([]);

    if (ledgerResult.status === 'fulfilled') {
      setAllocations(ledgerResult.value.items);
      setNextCursor(ledgerResult.value.nextCursor);
      setHasMore(ledgerResult.value.hasMore);
    } else {
      setAllocations([]);
      setLedgerError(
        ledgerResult.reason?.code === 'NOT_FOUND'
          ? 'Allocation history will be available after the fund service is enabled.'
          : ledgerResult.reason?.message || 'Unable to load allocation history.'
      );
    }

    setSummaryLoading(false);
    setLedgerLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadFunds();
  }, [loadFunds]);

  useEffect(() => {
    if (initialActionHandled.current || summaryLoading || !initialAction || !mutationsAllowed) return;
    initialActionHandled.current = true;
    if (initialAction === 'receive') setDialogDirection('incoming');
    else if (initialAction === 'opening') setOpeningDialogOpen(true);
    else if (initialAction === 'allocate') setDialogDirection('outgoing');
  }, [initialAction, mutationsAllowed, summaryLoading]);

  const loadMore = async () => {
    if (!nextCursor || ledgerLoading) return;
    try {
      setLedgerLoading(true);
      const response = await getFundAllocations({ projectId, cursor: nextCursor });
      setAllocations((current) => [...current, ...response.items]);
      setNextCursor(response.nextCursor);
      setHasMore(response.hasMore);
    } catch (loadError) {
      setLedgerError(loadError.message || 'Unable to load more allocation history.');
    } finally {
      setLedgerLoading(false);
    }
  };

  const available = summary?.availableToAllocate || '0.00';
  const fundingDeficit = summary?.fundingDeficit || '0.00';
  const openingBalanceRequired = isOperations && summary && summary.openingBalanceSet === false;
  const canAllocate = mutationsAllowed && isPositiveMoney(available);

  const allocateButton = (
    <button
      type="button"
      className="fund-button primary"
      onClick={() => setDialogDirection('outgoing')}
      disabled={!canAllocate}
    >
      <ArrowLeftRight size={16} /> Allocate funds
    </button>
  );

  return (
    <section className="project-funds-workspace" aria-labelledby="project-funds-title">
      <div className="fund-section-heading">
        <div>
          <span className="fund-kicker">VIRTUAL FUND BUCKET</span>
          <h2 id="project-funds-title">{isOperations ? 'Company Funds' : 'Project Funds'}</h2>
          <p>{isOperations
            ? 'Company-wide operating funds, commitments, and immutable allocation history.'
            : 'Projected BOQ margin is kept separate from cash that can actually be allocated.'}</p>
        </div>
        {!mutationsAllowed ? <span className="fund-read-only"><LockKeyhole size={14} /> Read only — Owner permission or feature activation is required</span> : null}
      </div>

      {summaryLoading ? (
        <div className="fund-summary-grid">
          {[0, 1, 2].map((item) => <div key={item} className="fund-summary-skeleton" />)}
        </div>
      ) : null}

      {!summaryLoading && summaryError ? (
        <div className="fund-configuration-state" role="status">
          <ShieldAlert size={21} />
          <div><strong>Project fund data is unavailable</strong><span>{summaryError}</span></div>
          <button type="button" className="fund-button secondary" onClick={loadFunds}>Try again</button>
        </div>
      ) : null}

      {!summaryLoading && summary ? (
        <>
          <div className={`fund-summary-grid ${isOperations ? 'operations' : ''}`}>
            {!isOperations ? (
              <SummaryMetric
                icon={BadgeDollarSign}
                label="Projected BOQ Margin"
                value={formatMoney(summary.projectedBoqMargin || projectedMargin)}
                badge="Estimate"
                description="For planning purposes; this is not cash available to allocate."
              />
            ) : null}

            <SummaryMetric
              icon={WalletCards}
              label="Available to Allocate"
              value={formatMoney(available)}
              badge="Available"
              tone={isPositiveMoney(fundingDeficit) ? 'danger' : 'positive'}
              description={isPositiveMoney(available)
                ? 'Calculated from paid cash, commitments, reserves, and posted allocations.'
                : 'No funds are currently available to allocate.'}
              action={mutationsAllowed ? allocateButton : null}
            />

            {isOperations ? (
              <>
                <SummaryMetric
                  icon={Landmark}
                  label="Approved — Awaiting payment"
                  value={formatMoney(summary.approvedExpenseCommitment)}
                  badge="Committed"
                  description="Approved operating expenses that have not been paid."
                  tone="warning"
                />
                <SummaryMetric
                  icon={CircleDollarSign}
                  label="Paid This Month"
                  value={summary.paidExpenseThisMonth ? formatMoney(summary.paidExpenseThisMonth) : 'Not available'}
                  badge={summary.paidExpenseThisMonthCount == null ? 'Monthly' : `${summary.paidExpenseThisMonthCount} items`}
                  description="Paid Company Operations expenses in the current month."
                />
              </>
            ) : null}
          </div>

          {isPositiveMoney(fundingDeficit) ? (
            <div className="fund-deficit-alert" role="alert">
              <ShieldAlert size={19} />
              <div><strong>Funding Deficit {formatMoney(fundingDeficit)}</strong><span>Amount required to cover current commitments. Allocation is disabled.</span></div>
            </div>
          ) : null}

          <div className="fund-formula-strip" aria-label="Fund balance calculation">
            <div><span>Paid income</span><strong>{formatMoney(summary.paidIncome)}</strong></div>
            <div><span>Allocated in</span><strong>{formatMoney(summary.allocatedIn)}</strong></div>
            <div><span>Paid expense</span><strong>{formatMoney(summary.paidExpense)}</strong></div>
            <div><span>Approved commitments</span><strong>{formatMoney(summary.approvedExpenseCommitment)}</strong></div>
            <div><span>Allocated out</span><strong>{formatMoney(summary.allocatedOut)}</strong></div>
            <div><span>Protected reserve</span><strong>{formatMoney(summary.protectedReserve)}</strong></div>
          </div>

          {openingBalanceRequired ? (
            <div className="fund-first-use-state">
              <div className="fund-first-use-icon"><Landmark size={24} /></div>
              <div>
                <strong>No funds are available in Company Operations yet.</strong>
                <span>The Owner can activate the one-time opening balance or receive funds from an active Project.</span>
              </div>
              {mutationsAllowed ? (
                <div className="fund-first-use-actions">
                  <button type="button" className="fund-button primary" onClick={() => setOpeningDialogOpen(true)}>Set opening balance</button>
                  <button type="button" className="fund-button secondary" onClick={() => setDialogDirection('incoming')}><ArrowDownToLine size={16} /> Receive from Project</button>
                </div>
              ) : null}
            </div>
          ) : null}

          {isOperations && summary.openingBalanceSet === true ? (
            <div className="fund-monthly-rollforward">
              <div><CalendarRange size={18} /><span>Balance start</span><strong>{summary.balanceStartDate || '-'}</strong></div>
              <div><span>Monthly opening</span><strong>{summary.monthlyOpening ? formatMoney(summary.monthlyOpening) : '—'}</strong></div>
              <div><span>Current closing</span><strong>{summary.monthlyClosing ? formatMoney(summary.monthlyClosing) : '—'}</strong></div>
            </div>
          ) : null}
        </>
      ) : null}

      <AllocationLedger
        projectId={projectId}
        items={allocations}
        loading={ledgerLoading}
        error={ledgerError}
        canReverse={mutationsAllowed}
        onReverse={async (allocation, payload) => {
          const result = await reverseFundAllocation(allocation.id, payload);
          await loadFunds();
          return result;
        }}
        onLoadMore={loadMore}
        hasMore={hasMore}
      />

      <FundAllocationDialog
        open={Boolean(dialogDirection)}
        onClose={() => {
          setDialogDirection('');
          loadFunds();
        }}
        currentProject={project}
        currentSummary={summary}
        options={options}
        direction={dialogDirection || 'outgoing'}
        onSubmit={createFundAllocation}
      />

      <FundOpeningBalanceDialog
        open={openingDialogOpen}
        onClose={() => setOpeningDialogOpen(false)}
        projectName={project?.name}
        onSubmit={(payload) => setFundOpeningBalance(projectId, payload)}
        onSuccess={loadFunds}
      />
    </section>
  );
}

export default ProjectFundsWorkspace;
