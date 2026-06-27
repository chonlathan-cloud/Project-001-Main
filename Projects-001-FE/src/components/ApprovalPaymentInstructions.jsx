import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Check,
  Copy,
  Landmark,
  Phone,
  ReceiptText,
  UserRound,
  WalletCards,
} from 'lucide-react';

const formatAmount = (value) =>
  `${Number(value || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} THB`;

const buildCopyText = ({ bankName, accountNo, accountName, amount, requesterName, vendorName, phone }) =>
  [
    'Payment Instructions',
    `Bank: ${bankName || '-'}`,
    `Account No: ${accountNo || '-'}`,
    `Account Name: ${accountName || '-'}`,
    `Amount: ${formatAmount(amount)}`,
    `Requester: ${requesterName || '-'}`,
    `Vendor: ${vendorName || '-'}`,
    `Phone: ${phone || '-'}`,
  ].join('\n');

function DetailLine({ icon, label, value, copyValue, onCopy, copied }) {
  const IconComponent = icon;

  return (
    <div className="approval-payment-line">
      <span className="approval-payment-line-icon">
        <IconComponent size={16} />
      </span>
      <div>
        <span>{label}</span>
        <strong>{value || '-'}</strong>
      </div>
      {copyValue ? (
        <button type="button" onClick={() => onCopy(copyValue)} title={`Copy ${label}`}>
          {copied ? <Check size={15} /> : <Copy size={15} />}
        </button>
      ) : null}
    </div>
  );
}

export default function ApprovalPaymentInstructions({
  request,
  editor,
  onFieldChange,
  canEdit,
}) {
  const [copiedValue, setCopiedValue] = useState('');
  const approvedAmount = request?.approved_amount ?? request?.amount ?? editor.amount;
  const bankName = editor.bank_name || request?.bank_name || request?.bank_account?.bank_name || '';
  const accountNo = editor.account_no || request?.account_no || request?.bank_account?.account_no || '';
  const accountName = editor.account_name || request?.account_name || request?.bank_account?.account_name || '';
  const requesterName = editor.requester_name || request?.requester_name || '';
  const vendorName = editor.vendor_name || request?.vendor_name || '';
  const phone = editor.phone || request?.phone || '';
  const missingFields = [
    !bankName ? 'bank name' : '',
    !accountNo ? 'account number' : '',
    !accountName ? 'account name' : '',
  ].filter(Boolean);
  const hasMissingBankInfo = missingFields.length > 0;

  const fullCopyText = useMemo(
    () =>
      buildCopyText({
        bankName,
        accountNo,
        accountName,
        amount: approvedAmount,
        requesterName,
        vendorName,
        phone,
      }),
    [accountName, accountNo, approvedAmount, bankName, phone, requesterName, vendorName]
  );

  const copyToClipboard = async (value) => {
    if (!value) return;

    try {
      await navigator.clipboard.writeText(value);
      setCopiedValue(value);
      window.setTimeout(() => {
        setCopiedValue((current) => (current === value ? '' : current));
      }, 1600);
    } catch {
      setCopiedValue('');
    }
  };

  return (
    <section className={hasMissingBankInfo ? 'approval-payment-card missing' : 'approval-payment-card'}>
      <div className="approval-payment-head">
        <div>
          <div className="approval-payment-kicker">
            <WalletCards size={15} />
            Payment Instructions
          </div>
          <h3>Bank transfer details</h3>
        </div>

        <button
          type="button"
          className="approval-copy-all-button"
          onClick={() => copyToClipboard(fullCopyText)}
        >
          {copiedValue === fullCopyText ? <Check size={16} /> : <Copy size={16} />}
          Copy transfer note
        </button>
      </div>

      {hasMissingBankInfo ? (
        <div className="approval-payment-warning">
          <AlertTriangle size={18} />
          <div>
            <strong>Bank information is incomplete.</strong>
            <span>
              Missing {missingFields.join(', ')}. Confirm recipient details before transferring or marking this request as paid.
            </span>
          </div>
        </div>
      ) : null}

      <div className="approval-payment-summary">
        <DetailLine
          icon={Landmark}
          label="Bank Name"
          value={bankName}
          copyValue={bankName}
          copied={copiedValue === bankName}
          onCopy={copyToClipboard}
        />
        <DetailLine
          icon={ReceiptText}
          label="Account Number"
          value={accountNo}
          copyValue={accountNo}
          copied={copiedValue === accountNo}
          onCopy={copyToClipboard}
        />
        <DetailLine
          icon={UserRound}
          label="Account Name"
          value={accountName}
          copyValue={accountName}
          copied={copiedValue === accountName}
          onCopy={copyToClipboard}
        />
        <DetailLine
          icon={WalletCards}
          label="Transfer Amount"
          value={formatAmount(approvedAmount)}
          copyValue={formatAmount(approvedAmount)}
          copied={copiedValue === formatAmount(approvedAmount)}
          onCopy={copyToClipboard}
        />
        <DetailLine
          icon={UserRound}
          label="Requester / Vendor"
          value={[requesterName, vendorName].filter(Boolean).join(' / ')}
        />
        <DetailLine
          icon={Phone}
          label="Phone"
          value={phone}
          copyValue={phone}
          copied={copiedValue === phone}
          onCopy={copyToClipboard}
        />
      </div>

      <div className="approval-bank-edit-grid">
        <label>
          <span>Bank Name</span>
          <input value={editor.bank_name} onChange={onFieldChange('bank_name')} disabled={!canEdit} />
        </label>
        <label>
          <span>Account Number</span>
          <input value={editor.account_no} onChange={onFieldChange('account_no')} disabled={!canEdit} />
        </label>
        <label>
          <span>Account Name</span>
          <input value={editor.account_name} onChange={onFieldChange('account_name')} disabled={!canEdit} />
        </label>
      </div>
    </section>
  );
}
