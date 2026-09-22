import React from 'react';
import {
  CheckCircle2,
  Download,
  Eye,
  FilePlus2,
  GitBranch,
  MinusCircle,
  PlusCircle,
  Send,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { Link } from 'react-router-dom';

function updateSchedule(schedule, index, updates) {
  return schedule.map((item, itemIndex) => (
    itemIndex === index ? { ...item, ...updates } : item
  ));
}

export default function QuotationLifecyclePanel({
  revision,
  quotation,
  disabled,
  canEdit,
  busy,
  hasActiveBaseline,
  onChange,
  onPreview,
  onIssue,
  onAccept,
  onRevise,
  onAlternative,
  onTransition,
  onChangeOrder,
  onExport,
}) {
  const mutable = revision.status === 'DRAFT' && canEdit && !disabled;
  const issued = revision.status === 'ISSUED';
  const immutable = revision.status !== 'DRAFT';
  const schedule = quotation.payment_schedule || [];

  return (
    <section className="quotation-lifecycle" aria-labelledby="quotation-lifecycle-title">
      <div className="quotation-lifecycle-heading">
        <div>
          <span className="boq-eyebrow">QUOTATION</span>
          <h2 id="quotation-lifecycle-title">
            {revision.document_number} <small>R{revision.revision_number}</small>
          </h2>
        </div>
        <span className={`quotation-status quotation-status-${revision.status.toLowerCase()}`}>
          {revision.status}
        </span>
      </div>

      {immutable ? (
        <div className="quotation-lock-note" role="status">
          <ShieldCheck size={18} aria-hidden="true" />
          <div>
            <strong>Immutable customer document</strong>
            <p>This revision is frozen. Create a new revision to change scope, pricing, or terms.</p>
          </div>
        </div>
      ) : null}

      <div className="quotation-fields">
        <label className="quotation-field-wide">
          <span>Document title</span>
          <input
            value={quotation.title || ''}
            onChange={(event) => onChange({ title: event.target.value })}
            disabled={!mutable}
            placeholder="ใบเสนอราคา / Quotation"
          />
        </label>
        <label>
          <span>Customer name</span>
          <input
            value={quotation.customer_name || ''}
            onChange={(event) => onChange({ customer_name: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>Tax ID</span>
          <input
            value={quotation.customer_tax_id || ''}
            onChange={(event) => onChange({ customer_tax_id: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label className="quotation-field-wide">
          <span>Customer address</span>
          <textarea
            rows="2"
            value={quotation.customer_address || ''}
            onChange={(event) => onChange({ customer_address: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>Contact</span>
          <input
            value={quotation.customer_contact || ''}
            onChange={(event) => onChange({ customer_contact: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>Quotation date</span>
          <input
            type="date"
            value={quotation.quotation_date || ''}
            onChange={(event) => onChange({ quotation_date: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>Valid until</span>
          <input
            type="date"
            value={quotation.valid_until || ''}
            onChange={(event) => onChange({ valid_until: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>VAT rate (%)</span>
          <input
            type="number"
            min="0"
            max="100"
            step="0.0001"
            value={quotation.vat_rate ?? '7.0000'}
            onChange={(event) => onChange({ vat_rate: event.target.value })}
            disabled={!mutable}
          />
        </label>
        <label>
          <span>Discount</span>
          <div className="quotation-split-field">
            <select
              value={quotation.discount_type || 'NONE'}
              onChange={(event) => onChange({
                discount_type: event.target.value,
                discount_value: event.target.value === 'NONE' ? '0.0000' : quotation.discount_value,
              })}
              disabled={!mutable}
            >
              <option value="NONE">None</option>
              <option value="PERCENT">Percent</option>
              <option value="FIXED">Fixed THB</option>
            </select>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={quotation.discount_value ?? '0.0000'}
              onChange={(event) => onChange({ discount_value: event.target.value })}
              disabled={!mutable || quotation.discount_type === 'NONE'}
              aria-label="Discount value"
            />
          </div>
        </label>
      </div>

      <div className="quotation-terms-grid">
        <fieldset disabled={!mutable}>
          <legend>Payment schedule</legend>
          {schedule.map((item, index) => (
            <div className="quotation-payment-row" key={`${item.label}-${index}`}>
              <input
                value={item.label || ''}
                onChange={(event) => onChange({
                  payment_schedule: updateSchedule(schedule, index, { label: event.target.value }),
                })}
                aria-label={`Payment ${index + 1} label`}
                placeholder="Milestone"
              />
              <input
                type="number"
                min="0"
                max="100"
                step="0.0001"
                value={item.percentage ?? ''}
                onChange={(event) => onChange({
                  payment_schedule: updateSchedule(schedule, index, {
                    percentage: event.target.value,
                    fixed_amount: null,
                  }),
                })}
                aria-label={`Payment ${index + 1} percent`}
                placeholder="%"
              />
              <button
                type="button"
                className="boq-icon-button"
                onClick={() => onChange({ payment_schedule: schedule.filter((_, itemIndex) => itemIndex !== index) })}
                aria-label={`Remove payment ${index + 1}`}
              >
                <XCircle size={16} />
              </button>
            </div>
          ))}
          {mutable ? (
            <button
              type="button"
              className="quotation-text-action"
              onClick={() => onChange({
                payment_schedule: [...schedule, { label: '', percentage: '', fixed_amount: null }],
              })}
            >
              <PlusCircle size={15} /> Add milestone
            </button>
          ) : null}
        </fieldset>
        <label>
          <span>Commercial terms</span>
          <textarea
            rows="5"
            value={(quotation.commercial_terms || []).join('\n')}
            onChange={(event) => onChange({
              commercial_terms: event.target.value.split('\n').filter((line) => line.trim()),
            })}
            disabled={!mutable}
            placeholder="One term per line"
          />
        </label>
      </div>

      <div className="quotation-totals" aria-label="Quotation totals">
        <div><span>Subtotal</span><strong>{quotation.subtotal || '0.00'} THB</strong></div>
        <div><span>Discount</span><strong>{quotation.discount_amount || '0.00'} THB</strong></div>
        <div><span>Net ex VAT</span><strong>{quotation.net_sell_ex_vat || '0.00'} THB</strong></div>
        <div><span>VAT</span><strong>{quotation.vat_amount || '0.00'} THB</strong></div>
        <div className="quotation-grand-total"><span>Grand total</span><strong>{quotation.grand_total || '0.00'} THB</strong></div>
      </div>

      <div className="quotation-actions" aria-label="Quotation lifecycle actions">
        <Link className="boq-button boq-button-secondary" to={`/quotations/${revision.document_id}?revision_id=${revision.revision_id}`}>
          <FilePlus2 size={16} /> Document composer
        </Link>
        <button type="button" className="boq-button boq-button-secondary" onClick={onPreview} disabled={busy}>
          <Eye size={16} /> {immutable ? 'ตัวอย่างฉบับตรึง / Exact snapshot' : 'ดูตัวอย่างเอกสาร / Preview quotation'}
        </button>
        {mutable ? (
          <button type="button" className="boq-button boq-button-primary" onClick={onIssue} disabled={busy}>
            <Send size={16} /> Issue revision
          </button>
        ) : null}
        {issued && canEdit ? (
          <>
            <button type="button" className="boq-button boq-button-primary" onClick={onAccept} disabled={busy}>
              <CheckCircle2 size={16} /> Record acceptance
            </button>
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onTransition('reject')} disabled={busy}>
              Reject
            </button>
          </>
        ) : null}
        {['ISSUED', 'ACCEPTED', 'REJECTED', 'WITHDRAWN', 'SUPERSEDED'].includes(revision.status) && canEdit ? (
          <button type="button" className="boq-button boq-button-secondary" onClick={onRevise} disabled={busy}>
            <GitBranch size={16} /> New revision
          </button>
        ) : null}
        {canEdit && ['DRAFT', 'ISSUED', 'ACCEPTED'].includes(revision.status) ? (
          <button type="button" className="boq-button boq-button-secondary" onClick={onAlternative} disabled={busy}>
            <FilePlus2 size={16} /> Alternative
          </button>
        ) : null}
        {revision.status === 'DRAFT' && canEdit ? (
          <button type="button" className="boq-button boq-button-quiet" onClick={() => onTransition('withdraw')} disabled={busy}>
            Withdraw
          </button>
        ) : null}
        {hasActiveBaseline && canEdit ? (
          <>
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onChangeOrder('ADD')} disabled={busy}>
              <PlusCircle size={16} /> ADD change order
            </button>
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onChangeOrder('DEDUCT')} disabled={busy}>
              <MinusCircle size={16} /> DEDUCT change order
            </button>
          </>
        ) : null}
        {revision.issued_snapshot_id ? (
          <div className="quotation-export-actions">
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onExport('CUSTOMER', 'PDF')} disabled={busy}>
              <Download size={16} /> PDF
            </button>
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onExport('CUSTOMER', 'XLSX')} disabled={busy}>
              Customer XLSX
            </button>
            <button type="button" className="boq-button boq-button-secondary" onClick={() => onExport('INTERNAL', 'XLSX')} disabled={busy}>
              Internal XLSX
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
