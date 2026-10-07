import { useEffect, useRef, useState } from 'react';
import { Camera, Upload, LoaderCircle } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import InputLineItemsEditor from './InputLineItemsEditor';
import InputRequestHistory from './InputRequestHistory';
import ReceiptOcrInspector from './ReceiptOcrInspector';
import { inputDate, inputMoney } from './inputWorkflowUtils';

function WorkflowField({ name, Control: controlComponent, form, requirements, onChange, ...props }) {
  const Control = controlComponent;
  return <div data-input-field={name}><Control value={form[name]} onChange={onChange(name)} {...requirements} {...props} hint="" /></div>;
}

export default function SubcontractorInputWorkflow({
  form, fields, requirements, projectOptions, workTypeOptions, requestTypeOptions, vatOptions,
  otherWorkType, lineItems, lineTotal, onChange, onLineItemsChange,
  tagProps, selectedFile, fileInputRef, cameraInputRef, onFileChange, onPickFile, onPickCamera,
  extractData, localPreviewUrl, ocrWarning, formatEntryTypeLabel,
  step, onStepChange, onNext, onSubmit, onClear, busy, extracting, error, errorField,
  outcomeUnknown, reviewWarnings,
}) {
  const [search, setSearch] = useSearchParams();
  const history = search.get('view') === 'history';
  const [profileOpen, setProfileOpen] = useState(false);
  const [bankOpen, setBankOpen] = useState(false);
  const [extrasOpen, setExtrasOpen] = useState(false);
  const [taxOpen, setTaxOpen] = useState(false);
  const headingRef = useRef(null);
  const rootRef = useRef(null);
  const { InputField, SelectField, TextAreaField, TagInput } = fields;
  const needsTax = ['vat_inclusive', 'vat_exclusive'].includes(form.accountingVatMode) || form.requestType === 'ค่าแรง';
  const profileFields = ['requesterName', 'phone', 'requestDate'];
  const taxFields = ['vendorTaxId', 'vendorBranch', 'vendorAddress'];
  const profileIncomplete = !form.requesterName || !form.requestDate;
  const field = (name, label, props = {}, Control = InputField) => <WorkflowField name={name} Control={Control} form={form} requirements={requirements[name === 'projectId' ? 'project' : name === 'accountingVatMode' ? 'vatMode' : name]} onChange={onChange} label={label} {...props} />;
  const payable = Number(form.amount) > 0 ? Number(form.amount) : lineTotal;
  useEffect(() => {
    if (history) return;
    const frame = window.requestAnimationFrame(() => {
      const wrapper = errorField && rootRef.current?.querySelector(`[data-input-field="${errorField}"]`);
      const target = wrapper?.querySelector('input:not([type=file]), select, textarea, button');
      (target || headingRef.current)?.focus();
      if (target) wrapper.scrollIntoView({ block: 'center', behavior: 'auto' });
      else headingRef.current?.scrollIntoView({ block: 'start', behavior: 'auto' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [step, errorField, error, history]);

  return (
    <div className="subcontractor-input-page input-mobile-workflow" ref={rootRef}>
      <nav className="input-workflow-tabs" aria-label="คำขอของผู้รับเหมา">
        <button type="button" aria-current={!history ? 'page' : undefined} disabled={busy} onClick={() => setSearch({})}>ส่งคำขอ</button>
        <button type="button" aria-current={history ? 'page' : undefined} disabled={busy} onClick={() => setSearch({ view: 'history' })}>คำขอของฉัน</button>
      </nav>
      {history ? <InputRequestHistory /> : (
        <form className="input-workflow-surface" onSubmit={(event) => { event.preventDefault(); if (!busy) { if (step === 3) onSubmit(); else onNext(); } }}>
          <ol className="input-stepper" aria-label="ขั้นตอนส่งคำขอ">{['แนบบิล', 'ตรวจข้อมูล', 'สรุปและส่ง'].map((label, index) => <li key={label} aria-current={step === index + 1 ? 'step' : undefined}><span>{index + 1}</span>{label}</li>)}</ol>
          <h2 ref={headingRef} tabIndex={-1} className="input-step-heading">{['แนบบิล', 'ตรวจข้อมูลในบิล', 'ตรวจสรุปก่อนส่ง'][step - 1]}</h2>
          {error ? <div className="input-notice error" role="alert">{outcomeUnknown ? 'ยังยืนยันผลการส่งไม่ได้ กรุณาตรวจคำขอของฉันก่อนส่งอีกครั้ง' : error}{outcomeUnknown ? <button className="input-button secondary" type="button" onClick={() => setSearch({ view: 'history' })}>ตรวจคำขอของฉัน</button> : null}</div> : null}
          <fieldset disabled={busy} className="input-workflow-fields">
            {step === 1 ? <>
              {field('projectId', 'โครงการ', { options: projectOptions, placeholder: 'เลือกโครงการ', disabled: !projectOptions.length }, SelectField)}
              {!projectOptions.length ? <p className="input-notice warning">ยังไม่มีโครงการที่ได้รับมอบหมาย กรุณาติดต่อผู้ดูแล</p> : null}
              <div data-input-field="receiptFile" className="input-workflow-upload">
                <input ref={fileInputRef} type="file" accept="image/*,application/pdf" onChange={onFileChange} hidden />
                <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" onChange={onFileChange} hidden />
                <div className="input-capture-actions"><button className="input-button primary" type="button" onClick={onPickCamera}><Camera size={20} aria-hidden="true" />ถ่ายรูปบิล</button><button className="input-button secondary" type="button" onClick={onPickFile}><Upload size={20} aria-hidden="true" />เลือกไฟล์</button></div>
                <small>รูปภาพ หรือ PDF</small>
                {selectedFile ? <div className="input-selected-receipt">{localPreviewUrl && selectedFile.type.startsWith('image/') ? <img src={localPreviewUrl} alt="บิลที่เลือก" /> : null}<strong>{selectedFile.name}</strong></div> : null}
                {extracting ? <p className="input-reading-status" role="status"><LoaderCircle size={18} className="spin" />กำลังอ่านข้อมูลจากบิล…</p> : extractData ? <p className="input-reading-status" role="status">อ่านข้อมูลแล้ว ตรวจให้ถูกต้องในขั้นถัดไป</p> : selectedFile ? <p>ตรวจและกรอกข้อมูลในขั้นถัดไปได้</p> : null}
                {requirements.receiptFile.error ? <small className="input-field-error">{requirements.receiptFile.error}</small> : null}
              </div>
            </> : null}
            {step === 2 ? <>
              {selectedFile ? <p className="input-current-receipt">บิล: {selectedFile.name} <button type="button" className="input-text-button" onClick={() => onStepChange(1)}>เปลี่ยนบิล</button></p> : null}
              {field('amount', 'ยอดชำระจริง (บาท)', { type: 'number', inputMode: 'decimal' })}
              {field('vendorName', 'ผู้ขาย / ร้านค้า')}
              <div className="input-workflow-grid">{field('receiptNo', 'เลขที่ใบเสร็จ')}{field('documentDate', 'วันที่เอกสาร', { type: 'date' })}</div>
              <div className="input-workflow-grid">{field('workType', 'ประเภทงาน', { options: workTypeOptions, placeholder: 'เลือกประเภทงาน' }, SelectField)}{field('requestType', 'ประเภทการเบิก', { options: requestTypeOptions, placeholder: 'เลือกประเภทการเบิก' }, SelectField)}</div>
              {form.workType === otherWorkType ? field('customWorkType', 'ระบุประเภทงาน') : null}
              {field('accountingVatMode', 'รูปแบบ VAT', { options: vatOptions, placeholder: 'เลือกรูปแบบ VAT' }, SelectField)}
              <details className="input-disclosure" open={needsTax || taxOpen || taxFields.includes(errorField)} onToggle={(event) => setTaxOpen(event.currentTarget.open)}>
                <summary>ข้อมูลภาษีผู้ขาย{needsTax ? ' (จำเป็น)' : ''}</summary>
                {field('vendorTaxId', 'เลขผู้เสียภาษีผู้ขาย', { inputMode: 'numeric' })}{field('vendorBranch', 'สาขาผู้ขาย')}{field('vendorAddress', 'ที่อยู่ผู้ขาย', {}, TextAreaField)}
              </details>
              <div data-input-field="lineItems"><InputLineItemsEditor value={lineItems} onChange={onLineItemsChange} disabled={busy} entryType="EXPENSE" workTypeOptions={workTypeOptions.filter((option) => option.value !== otherWorkType)} requestTypeOptions={requestTypeOptions} fallbackWorkType={form.workType === otherWorkType ? form.customWorkType : form.workType} fallbackRequestType={form.requestType} title="รายการในบิล" required error={requirements.lineItems.error} /></div>
              <details className="input-disclosure" open={profileOpen || profileIncomplete || profileFields.includes(errorField)} onToggle={(event) => setProfileOpen(event.currentTarget.open)}>
                <summary>ผู้ยื่น: {form.requesterName || 'กรอกชื่อผู้ยื่น'} <span>แก้ไข</span></summary>
                {field('requesterName', 'ชื่อ - นามสกุล')}{field('phone', 'เบอร์ติดต่อ', { inputMode: 'tel' })}{field('requestDate', 'วันที่ส่งคำขอ', { type: 'date' })}
              </details>
              <details className="input-disclosure" open={extrasOpen} onToggle={(event) => setExtrasOpen(event.currentTarget.open)}><summary>แท็กและหมายเหตุ (ถ้ามี)</summary><TagInput label="แท็ก" {...tagProps} hint="" />{field('note', 'หมายเหตุ', {}, TextAreaField)}</details>
              {extractData ? <details className="input-disclosure"><summary>ดูบิลและผลการอ่านข้อมูล</summary><ReceiptOcrInspector mode="extract" extractData={extractData} warningText={ocrWarning} selectedFile={selectedFile} localReceiptPreviewUrl={localPreviewUrl} formatEntryTypeLabel={formatEntryTypeLabel} /></details> : null}
            </> : null}
            {step === 3 ? <>
              <div className="input-summary-amount"><span>ยอดคำขอ</span><strong>{inputMoney(payable)} <small>บาท</small></strong></div>
              <dl className="input-summary-list"><div><dt>โครงการ</dt><dd>{projectOptions.find((option) => String(option.value) === String(form.projectId))?.label}</dd></div><div><dt>บิล</dt><dd>{selectedFile?.name}</dd></div><div><dt>ผู้ขาย</dt><dd>{form.vendorName}</dd></div><div><dt>เลขบิล</dt><dd>{form.receiptNo || '—'}</dd></div><div><dt>วันที่เอกสาร</dt><dd>{inputDate(form.documentDate)}</dd></div><div><dt>ผู้ยื่น</dt><dd>{form.requesterName}</dd></div><div><dt>รายการในบิล</dt><dd>{lineItems.filter((item) => item.description.trim()).length} รายการ · {inputMoney(lineTotal)} บาท</dd></div></dl>
              <details className="input-disclosure" open={bankOpen || !form.bankName || !form.accountNo || !form.accountName} onToggle={(event) => setBankOpen(event.currentTarget.open)}><summary>บัญชีรับเงิน <span>แก้ไข</span></summary>{field('bankName', 'ธนาคาร')}{field('accountNo', 'เลขที่บัญชี', { inputMode: 'numeric' })}{field('accountName', 'ชื่อบัญชี')}</details>
              <p className="input-bank-summary">{[form.bankName, form.accountNo, form.accountName].filter(Boolean).join(' · ') || 'ยังไม่ได้ระบุบัญชี'}</p>
              {reviewWarnings.map((warning) => <div className="input-notice warning" key={warning.title}><strong>{warning.title}</strong><p>{warning.detail}</p></div>)}
              {reviewWarnings.length ? <p className="input-confirm-copy">กดส่งเมื่อคุณตรวจข้อมูลและคำเตือนด้านบนแล้ว</p> : null}
            </> : null}
          </fieldset>
          <footer className="input-workflow-actions">
            {step > 1 ? <button type="button" className="input-button secondary" disabled={busy} onClick={() => onStepChange(step - 1)}>ย้อนกลับ</button> : <button type="button" className="input-text-button" disabled={busy} onClick={onClear}>ล้างข้อมูล</button>}
            <button type="submit" className="input-button primary" disabled={busy || !projectOptions.length}>{busy ? extracting ? 'กำลังอ่านบิล…' : 'กำลังส่ง…' : step === 3 ? 'ส่งให้ผู้ดูแลตรวจสอบ' : step === 1 ? 'ตรวจข้อมูล' : 'ดูสรุป'}</button>
          </footer>
        </form>
      )}
    </div>
  );
}
