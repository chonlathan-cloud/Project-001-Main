import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowUpFromLine,
  BadgeDollarSign,
  CalendarRange,
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

const summaryTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatSummaryTime(value) {
  if (!value) return '';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : summaryTimeFormatter.format(parsed);
}

function toDisplayNumber(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

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

function ProjectFundsWorkspace({ project, canMutate = false, initialAction = '' }) {
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
  const featureDisabled = summary?.mutationsEnabled === false;
  const mutationsAllowed = canMutate && !featureDisabled;

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
          ? 'Forecast Margin Allocation is not configured for this environment yet.'
          : summaryResult.reason?.message || 'Unable to load the forecast margin summary.'
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
          ? 'Margin Allocation history will be available after the service is enabled.'
          : ledgerResult.reason?.message || 'Unable to load Margin Allocation history.'
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
    else if (initialAction === 'opening' && isOperations && summary?.openingForecastBalanceSet === false) setOpeningDialogOpen(true);
    else if (
      initialAction === 'allocate' &&
      (!isOperations || summary?.openingForecastBalanceSet !== false) &&
      isPositiveMoney(summary?.availableMarginToAllocate)
    ) setDialogDirection('outgoing');
  }, [initialAction, isOperations, mutationsAllowed, summary, summaryLoading]);

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

  const available = summary?.availableMarginToAllocate || '0.00';
  const forecastDeficit = summary?.forecastDeficit || '0.00';
  const openingForecastRequired = isOperations && summary && summary.openingForecastBalanceSet === false;
  const canAllocate = mutationsAllowed && !openingForecastRequired && isPositiveMoney(available);
  const forecastBase = isOperations ? summary?.openingForecastBalance : summary?.projectedBoqMargin;
  const forecastCapacity = Math.max(
    0,
    toDisplayNumber(forecastBase) +
      toDisplayNumber(summary?.forecastAllocatedIn) -
      toDisplayNumber(summary?.forecastReserve)
  );
  const allocatedPercent = forecastCapacity > 0
    ? Math.max(0, (toDisplayNumber(summary?.forecastAllocatedOut) / forecastCapacity) * 100)
    : 0;
  const remainingPercent = forecastCapacity > 0
    ? Math.max(0, (toDisplayNumber(available) / forecastCapacity) * 100)
    : 0;
  const progressPercent = Math.min(100, allocatedPercent);

  const allocateButton = (
    <button
      type="button"
      className="fund-button primary"
      onClick={() => setDialogDirection('outgoing')}
      disabled={!canAllocate}
    >
      <ArrowLeftRight size={16} /> Allocate Margin
    </button>
  );

  return (
    <section className="project-funds-workspace" aria-labelledby="project-funds-title">
      <div className="fund-section-heading">
        <div>
          <span className="fund-kicker">FORECAST MARGIN BUCKET</span>
          <h2 id="project-funds-title">{isOperations ? 'Company Operations' : 'Forecast Margin'}</h2>
          <p>{isOperations
            ? 'Company-wide operating expenses and forecast margin allocation history.'
            : 'Forecast margin from BOQ; this is not actual cash.'}</p>
        </div>
        <div className="fund-heading-meta">
          {summary?.calculatedAt ? <span className="fund-calculated-at">Updated {formatSummaryTime(summary.calculatedAt)}</span> : null}
          {!canMutate ? <span className="fund-read-only"><LockKeyhole size={14} /> Read only — Owner permission is required</span> : null}
          {canMutate && featureDisabled ? <span className="fund-read-only"><LockKeyhole size={14} /> Forecast Margin Allocation is temporarily disabled</span> : null}
        </div>
      </div>

      {summaryLoading ? (
        <div className="fund-summary-grid">
          {[0, 1, 2].map((item) => <div key={item} className="fund-summary-skeleton" />)}
        </div>
      ) : null}

      {!summaryLoading && summaryError ? (
        <div className="fund-configuration-state" role="status">
          <ShieldAlert size={21} />
          <div><strong>Forecast margin data is unavailable</strong><span>{summaryError}</span></div>
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
                value={formatMoney(summary.projectedBoqMargin)}
                badge="Estimate"
                description="Forecast margin from BOQ; this is not actual cash."
              />
            ) : null}

            <SummaryMetric
              icon={WalletCards}
              label="Available Margin to Allocate"
              value={formatMoney(available)}
              badge="Available Margin"
              tone={isPositiveMoney(forecastDeficit) ? 'danger' : 'positive'}
              description={isPositiveMoney(available)
                ? 'Forecast base plus Allocated In, less Allocated Out and Forecast Reserve.'
                : 'No forecast margin is currently available to allocate.'}
              action={mutationsAllowed ? allocateButton : null}
            />

            {isOperations ? (
              <>
                <SummaryMetric
                  icon={ArrowDownToLine}
                  label="Forecast Allocated In"
                  value={formatMoney(summary.forecastAllocatedIn)}
                  badge="Forecast"
                  description="Margin received from other Project Buckets."
                />
                <SummaryMetric
                  icon={ArrowUpFromLine}
                  label="Forecast Allocated Out"
                  value={formatMoney(summary.forecastAllocatedOut)}
                  badge="Forecast"
                  description="Margin allocated to other Project Buckets."
                />
              </>
            ) : null}
          </div>

          {isPositiveMoney(forecastDeficit) ? (
            <div className="fund-deficit-alert" role="alert">
              <ShieldAlert size={19} />
              <div><strong>Forecast Deficit {formatMoney(forecastDeficit)}</strong><span>Forecast margin is below the amount already allocated. Further outgoing allocation is disabled.</span></div>
            </div>
          ) : null}

          <div className="fund-formula-strip" aria-label="Available Margin equals forecast base plus allocated in, less allocated out and forecast reserve">
            <div><span>{isOperations ? 'Opening Forecast Balance' : 'Projected BOQ Margin'}</span><strong>{formatMoney(forecastBase)}</strong></div>
            <div><span>+ Forecast Allocated In</span><strong>{formatMoney(summary.forecastAllocatedIn)}</strong></div>
            <div><span>− Forecast Allocated Out</span><strong>{formatMoney(summary.forecastAllocatedOut)}</strong></div>
            <div><span>− Forecast Reserve</span><strong>{formatMoney(summary.forecastReserve)}</strong></div>
            <div className="fund-formula-result"><span>= Available Margin</span><strong>{formatMoney(available)}</strong></div>
          </div>

          {forecastCapacity > 0 ? (
            <div className="fund-allocation-progress">
              <div className="fund-allocation-progress-heading">
                <div>
                  <strong>Forecast allocation progress</strong>
                  <span>Actual cashflow is excluded from this calculation.</span>
                </div>
                <strong>{allocatedPercent.toFixed(1)}% allocated · {remainingPercent.toFixed(1)}% remaining</strong>
              </div>
              <div
                className="fund-allocation-progress-track"
                role="progressbar"
                aria-label="Forecast margin allocated"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow={Math.round(progressPercent)}
              >
                <span style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
          ) : null}

          {openingForecastRequired ? (
            <div className="fund-first-use-state">
              <div className="fund-first-use-icon"><Landmark size={24} /></div>
              <div>
                <strong>No forecast margin is available in Company Operations yet.</strong>
                <span>The Owner can confirm the one-time Opening Forecast Balance or receive Margin from an active Project.</span>
              </div>
              {mutationsAllowed ? (
                <div className="fund-first-use-actions">
                  <button type="button" className="fund-button primary" onClick={() => setOpeningDialogOpen(true)}>Set Opening Forecast Balance</button>
                  <button type="button" className="fund-button secondary" onClick={() => setDialogDirection('incoming')}><ArrowDownToLine size={16} /> Receive Margin from Project</button>
                </div>
              ) : null}
            </div>
          ) : null}

          {isOperations && summary.openingForecastBalanceSet === true ? (
            <div className="fund-monthly-rollforward">
              <div><CalendarRange size={18} /><span>Forecast start</span><strong>{summary.balanceStartDate || '-'}</strong></div>
              <div><span>Monthly Forecast Opening</span><strong>{summary.monthlyForecastOpening ? formatMoney(summary.monthlyForecastOpening) : '—'}</strong></div>
              <div><span>Current Forecast Closing</span><strong>{summary.monthlyForecastClosing ? formatMoney(summary.monthlyForecastClosing) : '—'}</strong></div>
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
