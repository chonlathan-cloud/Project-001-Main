import React, { useEffect, useState } from 'react';
import { ArrowRight, Building2, LockKeyhole, ShieldAlert, WalletCards } from 'lucide-react';
import { getProjectFundSummary } from '../../api';
import { formatMoney, isPositiveMoney } from './fundMoney';
import './funds.css';

function CompanyFundsCard({ project, canMutate, onOpen, onAllocate, onSetOpening }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(Boolean(project?.id));
  const [error, setError] = useState('');

  useEffect(() => {
    if (!project?.id) return undefined;
    let isActive = true;
    getProjectFundSummary(project.id)
      .then((value) => {
        if (isActive) setSummary(value);
      })
      .catch((loadError) => {
        if (isActive) setError(loadError.message || 'Company Operations fund data is unavailable.');
      })
      .finally(() => {
        if (isActive) setLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [project?.id]);

  if (!project) {
    return (
      <section className="company-funds-section">
        <div className="fund-section-heading"><div><span className="fund-kicker">COMPANY FUNDS</span><h2>Company Funds</h2></div></div>
        <div className="fund-configuration-state"><ShieldAlert size={21} /><div><strong>Company Operations is missing</strong><span>Use the auditable bootstrap/recovery process. The UI will not create a duplicate Operations project.</span></div></div>
      </section>
    );
  }

  const available = summary?.availableToAllocate || '0.00';
  const deficit = summary?.fundingDeficit || '0.00';
  const mutationsAllowed = canMutate && summary?.mutationsEnabled !== false;

  return (
    <section className="company-funds-section" aria-labelledby="company-funds-title">
      <div className="fund-section-heading">
        <div><span className="fund-kicker">COMPANY FUNDS</span><h2 id="company-funds-title">Company Funds</h2><p>Central funds for company-wide operating expenses.</p></div>
      </div>
      <article className="company-funds-card">
        <div className="company-funds-card-header">
          <span className="company-funds-card-icon"><Building2 size={22} /></span>
          <div><h3>{project.name || 'Company Operations'}</h3><p>Company-wide operating expenses</p></div>
          <span className="fund-system-badge">System Bucket</span>
          {!mutationsAllowed ? <span className="fund-read-only"><LockKeyhole size={13} /> Read only</span> : null}
        </div>

        {loading ? <div className="company-funds-loading">Loading fund balance…</div> : null}
        {!loading && error ? <div className="fund-inline-error">{error}</div> : null}
        {!loading && summary ? (
          <>
            <div className="company-funds-metrics">
              <div className={isPositiveMoney(deficit) ? 'danger' : ''}>
                <span>{isPositiveMoney(deficit) ? 'Funding Deficit' : 'Available to Allocate'}</span>
                <strong>{formatMoney(isPositiveMoney(deficit) ? deficit : available)}</strong>
              </div>
              <div><span>Awaiting payment</span><strong>{formatMoney(summary.approvedExpenseCommitment)}</strong></div>
              <div><span>Paid this month</span><strong>{summary.paidExpenseThisMonth ? formatMoney(summary.paidExpenseThisMonth) : 'Not available'}</strong></div>
            </div>
            <div className="company-funds-actions">
              <button type="button" className="fund-button secondary" onClick={onOpen}>Open <ArrowRight size={15} /></button>
              {mutationsAllowed && summary.openingBalanceSet === false ? <button type="button" className="fund-button secondary" onClick={onSetOpening}>Set opening balance</button> : null}
              {mutationsAllowed ? <button type="button" className="fund-button primary" onClick={onAllocate} disabled={!isPositiveMoney(available)}><WalletCards size={16} /> Allocate funds</button> : null}
            </div>
          </>
        ) : null}
      </article>
    </section>
  );
}

export default CompanyFundsCard;
