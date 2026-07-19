import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Camera,
  Check,
  ClipboardCheck,
  CloudUpload,
  HardHat,
  LoaderCircle,
  Plus,
  Save,
  Send,
  Trash2,
  Users,
} from 'lucide-react';

import {
  createDailyReportSubmission,
  deleteDailyReportMedia,
  getDailyReportProjects,
  getMyDailyReportSubmissions,
  submitDailyReportSubmission,
  updateDailyReportSubmission,
  uploadDailyReportMedia,
} from '../../api';
import {
  DailyReportNotice,
  DailyReportStatusBadge,
} from './dailyReportUi';
import { formatReportDate, todayIso } from './dailyReportUtils';

const EMPTY_FORM = {
  work_summary: '',
  work_areas: '',
  manpower_total: 0,
  progress_percent: '',
  checklist: {
    safety_ok: true,
    quality_ok: true,
    schedule_ok: true,
    materials_ready: true,
    customer_decision_needed: false,
  },
  site_conditions: {
    weather: '',
    site_access: '',
  },
  issues: [],
  tomorrow_plan: '',
  notes: '',
};

function formFromSubmission(submission) {
  if (!submission) return EMPTY_FORM;
  return {
    ...EMPTY_FORM,
    work_summary: submission.work_summary || '',
    work_areas: (submission.work_areas || []).join(', '),
    manpower_total: submission.manpower_total || 0,
    progress_percent: submission.progress_percent ?? '',
    checklist: { ...EMPTY_FORM.checklist, ...(submission.checklist || {}) },
    site_conditions: { ...EMPTY_FORM.site_conditions, ...(submission.site_conditions || {}) },
    issues: Array.isArray(submission.issues) ? submission.issues : [],
    tomorrow_plan: submission.tomorrow_plan || '',
    notes: submission.notes || '',
  };
}

function payloadFromForm(form) {
  return {
    work_summary: form.work_summary.trim(),
    work_areas: form.work_areas.split(',').map((item) => item.trim()).filter(Boolean),
    manpower_total: Number(form.manpower_total || 0),
    progress_percent: form.progress_percent === '' ? null : Number(form.progress_percent),
    checklist: form.checklist,
    site_conditions: form.site_conditions,
    issues: form.issues
      .filter((issue) => issue.title.trim())
      .map((issue) => ({ ...issue, title: issue.title.trim(), detail: issue.detail?.trim() || null })),
    tomorrow_plan: form.tomorrow_plan.trim(),
    notes: form.notes.trim() || null,
  };
}

export default function SubcontractorDailyReportWorkspace() {
  const [searchParams] = useSearchParams();
  const linkedProjectId = searchParams.get('project') || '';
  const linkedReportDate = searchParams.get('date') || '';
  const [projects, setProjects] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [projectId, setProjectId] = useState('');
  const [reportDate, setReportDate] = useState(linkedReportDate || todayIso());
  const [activeSubmission, setActiveSubmission] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [files, setFiles] = useState([]);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState(null);

  const isEditable = !activeSubmission || ['DRAFT', 'CHANGES_REQUESTED'].includes(activeSubmission.status);
  const matchingSubmission = useMemo(
    () => submissions.find(
      (item) => item.project_id === projectId && item.report_date === reportDate,
    ) || null,
    [projectId, reportDate, submissions],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [projectItems, submissionItems] = await Promise.all([
        getDailyReportProjects(),
        getMyDailyReportSubmissions(),
      ]);
      setProjects(projectItems);
      setSubmissions(submissionItems);
      setProjectId((current) => (
        current
        || (projectItems.some((item) => item.id === linkedProjectId) ? linkedProjectId : '')
        || projectItems[0]?.id
        || ''
      ));
    } catch (error) {
      console.error('Unable to load daily reports.', error);
      setNotice({ tone: 'danger', message: 'ไม่สามารถโหลดรายงานประจำวันได้ กรุณาลองใหม่อีกครั้ง' });
    } finally {
      setLoading(false);
    }
  }, [linkedProjectId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setActiveSubmission(matchingSubmission);
    setForm(formFromSubmission(matchingSubmission));
    setFiles([]);
    setStep(1);
  }, [matchingSubmission]);

  const updateForm = (field, value) => setForm((current) => ({ ...current, [field]: value }));
  const updateNested = (section, field, value) => {
    setForm((current) => ({
      ...current,
      [section]: { ...current[section], [field]: value },
    }));
  };

  const ensureDraft = async () => {
    if (activeSubmission) return activeSubmission;
    if (!projectId) throw new Error('กรุณาเลือกโครงการก่อน');
    const created = await createDailyReportSubmission({
      project_id: projectId,
      report_date: reportDate,
    });
    setActiveSubmission(created);
    setSubmissions((current) => [created, ...current.filter((item) => item.id !== created.id)]);
    return created;
  };

  const saveDraft = async ({ quiet = false, manageBusy = true } = {}) => {
    if (manageBusy) setBusy('save');
    setNotice(null);
    try {
      const draft = await ensureDraft();
      const updated = await updateDailyReportSubmission(draft.id, payloadFromForm(form));
      setActiveSubmission(updated);
      setSubmissions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      if (!quiet) setNotice({ tone: 'success', message: 'บันทึกร่างเรียบร้อยแล้ว' });
      return updated;
    } catch (error) {
      console.error('Unable to save the draft.', error);
      setNotice({ tone: 'danger', message: error.message === 'กรุณาเลือกโครงการก่อน' ? error.message : 'ไม่สามารถบันทึกร่างได้ กรุณาลองใหม่อีกครั้ง' });
      throw error;
    } finally {
      if (manageBusy) setBusy('');
    }
  };

  const uploadSelectedFiles = async (draft, selectedFiles) => {
    let next = draft;

    for (let index = 0; index < selectedFiles.length; index += 1) {
      try {
        const uploaded = await uploadDailyReportMedia(draft.id, selectedFiles[index]);
        next = {
          ...next,
          media_ids: [...new Set([...(next.media_ids || []), uploaded.id])],
        };
        setActiveSubmission(next);
        setSubmissions((current) => (
          current.some((item) => item.id === next.id)
            ? current.map((item) => (item.id === next.id ? next : item))
            : [next, ...current]
        ));
      } catch (error) {
        setFiles(selectedFiles.slice(index));
        throw error;
      }
    }

    setFiles([]);
    return next;
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;
    const selectedFiles = [...files];
    setBusy('upload');
    setNotice(null);
    try {
      const draft = await ensureDraft();
      await uploadSelectedFiles(draft, selectedFiles);
      setNotice({ tone: 'success', message: `อัปโหลดหลักฐาน ${selectedFiles.length} ไฟล์เรียบร้อยแล้ว` });
    } catch (error) {
      console.error('Evidence upload failed.', error);
      setNotice({ tone: 'danger', message: 'อัปโหลดหลักฐานไม่สำเร็จ กรุณาลองใหม่อีกครั้ง' });
    } finally {
      setBusy('');
    }
  };

  const removeMedia = async (mediaId) => {
    setBusy(`delete-${mediaId}`);
    try {
      await deleteDailyReportMedia(mediaId);
      const next = {
        ...activeSubmission,
        media_ids: (activeSubmission.media_ids || []).filter((item) => item !== mediaId),
      };
      setActiveSubmission(next);
      setSubmissions((current) => current.map((item) => (item.id === next.id ? next : item)));
    } catch (error) {
      console.error('Unable to delete evidence.', error);
      setNotice({ tone: 'danger', message: 'ไม่สามารถลบหลักฐานได้ กรุณาลองใหม่อีกครั้ง' });
    } finally {
      setBusy('');
    }
  };

  const addIssue = () => {
    updateForm('issues', [
      ...form.issues,
      { title: '', detail: '', severity: 'normal', needs_customer_decision: false },
    ]);
  };

  const updateIssue = (index, field, value) => {
    updateForm(
      'issues',
      form.issues.map((issue, issueIndex) => (
        issueIndex === index ? { ...issue, [field]: value } : issue
      )),
    );
  };

  const handleSubmit = async () => {
    const pendingFiles = [...files];
    setBusy('submit');
    setNotice(null);
    try {
      const saved = await saveDraft({ quiet: true, manageBusy: false });
      const readyToSubmit = pendingFiles.length > 0
        ? await uploadSelectedFiles(saved, pendingFiles)
        : saved;

      if ((readyToSubmit.media_ids || []).length === 0) {
        setStep(1);
        setNotice({ tone: 'danger', message: 'กรุณาเพิ่มรูปหน้างานอย่างน้อย 1 รูปก่อนส่งรายงาน' });
        return;
      }

      const submitted = await submitDailyReportSubmission(readyToSubmit.id);
      setActiveSubmission(submitted);
      setSubmissions((current) => current.map((item) => (item.id === submitted.id ? submitted : item)));
      setNotice({ tone: 'success', message: 'ส่งรายงานให้ผู้ดูแลหรือเจ้าของโครงการตรวจสอบแล้ว' });
    } catch (error) {
      console.error('Unable to submit the report.', error);
      const isMissingPhoto = String(error?.detail || '').includes('At least one site photo');
      const isUploadFailure = String(error?.path || '').endsWith('/media');
      if (isMissingPhoto || isUploadFailure) setStep(1);
      setNotice({
        tone: 'danger',
        message: isMissingPhoto
          ? 'กรุณาเพิ่มรูปหน้างานอย่างน้อย 1 รูปก่อนส่งรายงาน'
          : isUploadFailure
            ? 'อัปโหลดหลักฐานไม่สำเร็จ กรุณาตรวจสอบไฟล์และลองใหม่อีกครั้ง'
            : 'ไม่สามารถส่งรายงานได้ กรุณาตรวจสอบข้อมูลแล้วลองใหม่อีกครั้ง',
      });
    } finally {
      setBusy('');
    }
  };

  if (loading) {
    return <div className="dr-loading"><LoaderCircle className="spin" /> กำลังโหลดรายงานประจำวัน…</div>;
  }

  return (
    <div className="dr-workspace dr-subcontractor">
      <section className="dr-hero">
        <div>
          <span className="dr-eyebrow">อัปเดตหน้างาน</span>
          <h2>รายงานประจำวัน</h2>
          <p>บันทึกงานที่ทำวันนี้ หลักฐานหน้างาน การตรวจสอบ และแผนงานวันพรุ่งนี้</p>
        </div>
        {activeSubmission ? <DailyReportStatusBadge status={activeSubmission.status} locale="th" /> : null}
      </section>

      <DailyReportNotice tone={notice?.tone}>{notice?.message}</DailyReportNotice>
      {activeSubmission?.change_request_reason ? (
        <DailyReportNotice tone="danger">
          <strong>ผู้ดูแลขอให้แก้ไข:</strong> {activeSubmission.change_request_reason}
        </DailyReportNotice>
      ) : null}

      <section className="dr-card dr-context-card">
        <label>
          <span>โครงการ</span>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span>วันที่รายงาน</span>
          <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
        </label>
        <div className="dr-context-summary">
          <span>หลักฐานที่อัปโหลดแล้ว</span>
          <strong>{activeSubmission?.media_ids?.length || 0}</strong>
        </div>
      </section>

      {projects.length === 0 ? (
        <DailyReportNotice tone="warning">ยังไม่มีโครงการที่มอบหมายให้คุณในขณะนี้</DailyReportNotice>
      ) : (
        <>
          <div className="dr-stepper" aria-label="ขั้นตอนการกรอกรายงานประจำวัน">
            {[
              [1, 'งานและหลักฐาน'],
              [2, 'ตรวจสอบหน้างาน'],
              [3, 'ตรวจทานและส่ง'],
            ].map(([number, label]) => (
              <button
                type="button"
                key={number}
                className={step === number ? 'active' : step > number ? 'complete' : ''}
                onClick={() => setStep(number)}
              >
                <span>{step > number ? <Check size={14} /> : number}</span>
                {label}
              </button>
            ))}
          </div>

          <section className="dr-card dr-form-card">
            {step === 1 ? (
              <div className="dr-form-section">
                <div className="dr-section-heading">
                  <HardHat />
                  <div><h3>วันนี้ทำอะไรที่หน้างานบ้าง?</h3><p>ระบุงานที่ทำให้ชัดเจน เพื่อให้ตรวจสอบได้ง่าย</p></div>
                </div>
                <label className="dr-field full">
                  <span>สรุปงานที่ทำ *</span>
                  <textarea
                    rows="5"
                    value={form.work_summary}
                    onChange={(event) => updateForm('work_summary', event.target.value)}
                    disabled={!isEditable}
                    placeholder="เช่น ติดตั้งโครงฝ้าบริเวณทางเดินชั้น 2 และเริ่มประสานงานระบบ…"
                  />
                </label>
                <div className="dr-form-grid">
                  <label className="dr-field">
                    <span>พื้นที่ปฏิบัติงาน</span>
                    <input
                      value={form.work_areas}
                      onChange={(event) => updateForm('work_areas', event.target.value)}
                      disabled={!isEditable}
                      placeholder="เช่น ชั้น 2, โถงต้อนรับ, ปีกอาคารด้านตะวันออก"
                    />
                  </label>
                  <label className="dr-field">
                    <span><Users size={14} /> จำนวนคนงาน</span>
                    <input
                      type="number"
                      min="0"
                      value={form.manpower_total}
                      onChange={(event) => updateForm('manpower_total', event.target.value)}
                      disabled={!isEditable}
                    />
                  </label>
                  <label className="dr-field">
                    <span>ความคืบหน้าโดยรวม (%)</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={form.progress_percent}
                      onChange={(event) => updateForm('progress_percent', event.target.value)}
                      disabled={!isEditable}
                    />
                  </label>
                  <label className="dr-field">
                    <span>สภาพอากาศ</span>
                    <input
                      value={form.site_conditions.weather}
                      onChange={(event) => updateNested('site_conditions', 'weather', event.target.value)}
                      disabled={!isEditable}
                      placeholder="เช่น ท้องฟ้าแจ่มใส, ฝนตกเล็กน้อย…"
                    />
                  </label>
                </div>

                <div className="dr-upload">
                  <div><Camera /><strong>หลักฐานหน้างาน *</strong><span>ต้องมีรูปภาพอย่างน้อย 1 รูป ส่วนวิดีโอและเสียงบันทึกไม่บังคับ</span></div>
                  <input
                    id="daily-report-evidence"
                    className="dr-file-input"
                    type="file"
                    multiple
                    accept="image/*,video/*,audio/*"
                    onChange={(event) => setFiles(Array.from(event.target.files || []))}
                    disabled={!isEditable}
                  />
                  <label className={`dr-file-picker${isEditable ? '' : ' disabled'}`} htmlFor="daily-report-evidence">
                    <Camera size={16} /> เลือกไฟล์จากอุปกรณ์
                  </label>
                  {files.length > 0 ? (
                    <div className="dr-file-list">
                      {files.map((file) => (
                        <span key={`${file.name}-${file.size}`}>{file.name} · รออัปโหลด</span>
                      ))}
                    </div>
                  ) : null}
                  <button
                    type="button"
                    className="dr-button secondary"
                    onClick={uploadFiles}
                    disabled={!isEditable || files.length === 0 || busy === 'upload'}
                  >
                    {busy === 'upload' ? <LoaderCircle className="spin" /> : <CloudUpload />}
                    อัปโหลดไฟล์ที่เลือก
                  </button>
                  {(activeSubmission?.media_ids || []).length > 0 ? (
                    <div className="dr-media-chips">
                      {activeSubmission.media_ids.map((mediaId, index) => (
                        <span key={mediaId}>
                          <Camera size={14} /> หลักฐาน {index + 1}
                          {isEditable ? (
                            <button type="button" onClick={() => removeMedia(mediaId)} aria-label={`ลบหลักฐาน ${index + 1}`}>
                              {busy === `delete-${mediaId}` ? <LoaderCircle className="spin" /> : <Trash2 />}
                            </button>
                          ) : null}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="dr-form-section">
                <div className="dr-section-heading">
                  <ClipboardCheck />
                  <div><h3>การตรวจสอบและปัญหาหน้างาน</h3><p>ระบุเรื่องสำคัญที่ผู้ตรวจสอบหรือลูกค้าควรทราบ</p></div>
                </div>
                <div className="dr-check-grid">
                  {[
                    ['safety_ok', 'มีมาตรการความปลอดภัยครบถ้วน'],
                    ['quality_ok', 'ผ่านการตรวจสอบคุณภาพ'],
                    ['schedule_ok', 'งานเป็นไปตามกำหนด'],
                    ['materials_ready', 'วัสดุพร้อมใช้งาน'],
                    ['customer_decision_needed', 'ต้องการการตัดสินใจจากลูกค้า'],
                  ].map(([key, label]) => (
                    <label key={key}>
                      <input
                        type="checkbox"
                        checked={Boolean(form.checklist[key])}
                        onChange={(event) => updateNested('checklist', key, event.target.checked)}
                        disabled={!isEditable}
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </div>
                <div className="dr-issues">
                  <div className="dr-inline-heading">
                    <h4><AlertTriangle size={17} /> ปัญหา / อุปสรรค</h4>
                    <button type="button" className="dr-text-button" onClick={addIssue} disabled={!isEditable}>
                      <Plus /> เพิ่มปัญหา
                    </button>
                  </div>
                  {form.issues.length === 0 ? <p className="dr-empty-copy">ยังไม่มีปัญหา</p> : null}
                  {form.issues.map((issue, index) => (
                    <div className="dr-issue-editor" key={`issue-${index}`}>
                      <input
                        value={issue.title}
                        onChange={(event) => updateIssue(index, 'title', event.target.value)}
                        placeholder="หัวข้อปัญหา"
                        disabled={!isEditable}
                      />
                      <textarea
                        rows="2"
                        value={issue.detail || ''}
                        onChange={(event) => updateIssue(index, 'detail', event.target.value)}
                        placeholder="เกิดอะไรขึ้น และต้องการให้ช่วยดำเนินการอย่างไร?"
                        disabled={!isEditable}
                      />
                      <select
                        value={issue.severity || 'normal'}
                        onChange={(event) => updateIssue(index, 'severity', event.target.value)}
                        disabled={!isEditable}
                      >
                        <option value="low">เล็กน้อย</option>
                        <option value="normal">ทั่วไป</option>
                        <option value="high">สูง</option>
                        <option value="critical">วิกฤต</option>
                      </select>
                      <button
                        type="button"
                        onClick={() => updateForm('issues', form.issues.filter((_, issueIndex) => issueIndex !== index))}
                        disabled={!isEditable}
                        aria-label={`ลบปัญหารายการที่ ${index + 1}`}
                      >
                        <Trash2 />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {step === 3 ? (
              <div className="dr-form-section">
                <div className="dr-section-heading">
                  <Send />
                  <div><h3>แผนวันพรุ่งนี้และตรวจทานครั้งสุดท้าย</h3><p>ผู้ดูแลหรือเจ้าของโครงการจะตรวจรายงานนี้ก่อนส่งข้อมูลให้ลูกค้า</p></div>
                </div>
                <label className="dr-field full">
                  <span>แผนงานวันพรุ่งนี้ *</span>
                  <textarea
                    rows="4"
                    value={form.tomorrow_plan}
                    onChange={(event) => updateForm('tomorrow_plan', event.target.value)}
                    disabled={!isEditable}
                    placeholder="เช่น ดำเนินงานติดตั้งโครงฝ้าต่อ และสรุปงานประสานระบบที่ค้างอยู่…"
                  />
                </label>
                <label className="dr-field full">
                  <span>หมายเหตุภายใน</span>
                  <textarea
                    rows="3"
                    value={form.notes}
                    onChange={(event) => updateForm('notes', event.target.value)}
                    disabled={!isEditable}
                    placeholder="ผู้ตรวจสอบจะเห็นข้อความนี้ แต่ระบบจะไม่ส่งให้ลูกค้าโดยอัตโนมัติ"
                  />
                </label>
                <div className="dr-review-summary">
                  <div><span>สรุปงานที่ทำ</span><strong>{form.work_summary || 'ยังไม่ได้กรอก'}</strong></div>
                  <div>
                    <span>หลักฐาน</span>
                    <strong>
                      {activeSubmission?.media_ids?.length || 0} ไฟล์ที่อัปโหลด
                      {files.length > 0 ? ` · ${files.length} ไฟล์รออัปโหลด` : ''}
                    </strong>
                  </div>
                  <div><span>ปัญหา</span><strong>{form.issues.filter((issue) => issue.title.trim()).length} รายการ</strong></div>
                  <div><span>แผนงานวันพรุ่งนี้</span><strong>{form.tomorrow_plan || 'ยังไม่ได้กรอก'}</strong></div>
                </div>
              </div>
            ) : null}

            <footer className="dr-form-actions">
              <button
                type="button"
                className="dr-button ghost"
                onClick={() => setStep((current) => Math.max(1, current - 1))}
                disabled={step === 1}
              >
                <ArrowLeft /> ย้อนกลับ
              </button>
              <div>
                {isEditable ? (
                  <button type="button" className="dr-button secondary" onClick={() => saveDraft()} disabled={Boolean(busy)}>
                    {busy === 'save' ? <LoaderCircle className="spin" /> : <Save />} บันทึกร่าง
                  </button>
                ) : null}
                {step < 3 ? (
                  <button type="button" className="dr-button primary" onClick={() => setStep(step + 1)}>
                    ถัดไป <ArrowRight />
                  </button>
                ) : isEditable ? (
                  <button type="button" className="dr-button primary" onClick={handleSubmit} disabled={Boolean(busy)}>
                    {busy === 'submit' ? <LoaderCircle className="spin" /> : <Send />}
                    {activeSubmission?.status === 'CHANGES_REQUESTED' ? 'ส่งรายงานที่แก้ไขแล้ว' : 'ส่งให้ตรวจสอบ'}
                  </button>
                ) : null}
              </div>
            </footer>
          </section>
        </>
      )}

      <section className="dr-card dr-history">
        <div className="dr-inline-heading"><h3>รายงานล่าสุดของฉัน</h3><span>ทั้งหมด {submissions.length} รายการ</span></div>
        {submissions.length === 0 ? <p className="dr-empty-copy">ยังไม่มีรายงานประจำวัน</p> : (
          <div className="dr-history-list">
            {submissions.slice(0, 8).map((submission) => (
              <button
                type="button"
                key={submission.id}
                onClick={() => {
                  setProjectId(submission.project_id);
                  setReportDate(submission.report_date);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
              >
                <div>
                  <strong>{submission.project_name || submission.project_id}</strong>
                  <span>{formatReportDate(submission.report_date, 'th-TH')} · หลักฐาน {submission.media_ids?.length || 0} รายการ</span>
                </div>
                <DailyReportStatusBadge status={submission.status} locale="th" />
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
