import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { createEmptyLineItem, sumLineItems } from './inputLineItemsUtils';

const toNumber = (value, fallback = 0) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};

const moneyInputStyle = {
  fontVariantNumeric: 'tabular-nums',
  textAlign: 'right',
};

function InputLineItemsEditor({
  value = [],
  onChange,
  disabled = false,
  entryType = 'EXPENSE',
  workTypeOptions = [],
  requestTypeOptions = [],
  fallbackWorkType = '',
  fallbackRequestType = '',
  title = 'รายการค่าใช้จ่าย',
  subtitle = '',
}) {
  const isIncome = entryType === 'INCOME';
  const lineItems = value.length ? value : [];
  const totalAmount = sumLineItems(lineItems);

  const emitChange = (nextItems) => {
    onChange(nextItems.map((item, index) => ({
      ...item,
      line_no: index + 1,
    })));
  };

  const handleAdd = () => {
    emitChange([
      ...lineItems,
      createEmptyLineItem({
        work_type: isIncome ? '' : fallbackWorkType,
        request_type: isIncome ? '' : fallbackRequestType,
      }),
    ]);
  };

  const handleRemove = (indexToRemove) => {
    emitChange(lineItems.filter((_, index) => index !== indexToRemove));
  };

  const handleChange = (indexToUpdate, field, rawValue) => {
    const nextItems = lineItems.map((item, index) => {
      if (index !== indexToUpdate) return item;

      const nextItem = { ...item, [field]: rawValue };
      if (field === 'qty' || field === 'unit_price') {
        const qty = toNumber(field === 'qty' ? rawValue : nextItem.qty);
        const unitPrice = toNumber(field === 'unit_price' ? rawValue : nextItem.unit_price);
        nextItem.amount = Number((qty * unitPrice).toFixed(2));
      }
      if (field === 'amount') {
        nextItem.amount = rawValue;
      }
      return nextItem;
    });
    emitChange(nextItems);
  };

  return (
    <section className="input-line-items-editor">
      <div className="input-line-items-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <div className="input-line-items-total" aria-label="ยอดรวมรายการ">
          <span>รวม</span>
          <strong>{totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>
      </div>

      <div className="input-line-items-table" role="table" aria-label={title}>
        <div className={`input-line-items-row input-line-items-row-head${isIncome ? ' is-income' : ''}`} role="row">
          <div role="columnheader">รายการ</div>
          <div role="columnheader">จำนวน</div>
          <div role="columnheader">ราคา/หน่วย</div>
          <div role="columnheader">ยอดรวม</div>
          {!isIncome ? <div role="columnheader">ประเภท</div> : null}
          <div role="columnheader" aria-label="actions" />
        </div>

        {lineItems.map((item, index) => (
          <div className={`input-line-items-row${isIncome ? ' is-income' : ''}`} role="row" key={item.id || `${item.description}-${index}`}>
            <div role="cell">
              <input
                type="text"
                value={item.description || ''}
                onChange={(event) => handleChange(index, 'description', event.target.value)}
                placeholder="ชื่อรายการ"
                disabled={disabled}
              />
            </div>
            <div role="cell">
              <input
                type="number"
                inputMode="decimal"
                value={item.qty ?? ''}
                onChange={(event) => handleChange(index, 'qty', event.target.value)}
                disabled={disabled}
                style={moneyInputStyle}
              />
            </div>
            <div role="cell">
              <input
                type="number"
                inputMode="decimal"
                value={item.unit_price ?? ''}
                onChange={(event) => handleChange(index, 'unit_price', event.target.value)}
                disabled={disabled}
                style={moneyInputStyle}
              />
            </div>
            <div role="cell">
              <input
                type="number"
                inputMode="decimal"
                value={item.amount ?? ''}
                onChange={(event) => handleChange(index, 'amount', event.target.value)}
                disabled={disabled}
                style={moneyInputStyle}
              />
            </div>
            {!isIncome ? (
              <div role="cell" className="input-line-items-category-cell">
                <select
                  value={item.work_type || ''}
                  onChange={(event) => handleChange(index, 'work_type', event.target.value)}
                  disabled={disabled}
                  aria-label="ประเภทงาน"
                >
                  <option value="">ประเภทงาน</option>
                  {workTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <select
                  value={item.request_type || ''}
                  onChange={(event) => handleChange(index, 'request_type', event.target.value)}
                  disabled={disabled}
                  aria-label="ประเภทการเบิก"
                >
                  <option value="">ประเภทการเบิก</option>
                  {requestTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            <div role="cell" className="input-line-items-actions">
              <button
                type="button"
                onClick={() => handleRemove(index)}
                disabled={disabled || lineItems.length <= 1}
                aria-label="ลบรายการ"
                title="ลบรายการ"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="input-line-items-add"
        onClick={handleAdd}
        disabled={disabled}
      >
        <Plus size={16} />
        <span>เพิ่มรายการ</span>
      </button>
    </section>
  );
}

export default InputLineItemsEditor;
