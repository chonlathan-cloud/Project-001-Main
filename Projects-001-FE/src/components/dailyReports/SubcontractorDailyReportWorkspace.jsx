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

const VALID_ISSUE_SEVERITIES = new Set(['low', 'normal', 'high', 'critical']);

const SUBMISSION_FIELD_MESSAGES = {
  work_summary: 'กรุณากรอกสรุปงานที่ทำวันนี้',
  manpower_total: 'จำนวนคนงานต้องเป็นจำนวนเต็มตั้งแต่ 0 ถึง 10,000 คน',
  progress_percent: 'ความคืบหน้าต้องเป็นตัวเลขตั้งแต่ 0 ถึง 100',
  checklist: 'ข้อมูลการตรวจสอบหน้างานไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง',
  site_conditions: 'ข้อมูลสภาพหน้างานไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง',
  issues: 'ข้อมูลปัญหาหน้างานไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง',
  tomorrow_plan: 'กรุณากรอกแผนงานวันพรุ่งนี้',
};

function normalizeStringRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, String(item ?? '').trim()]),
  );
}

function normalizeBooleanRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, Boolean(item)]),
  );
}

function prepareSubmissionPayload(form) {
  const errors = {};
  const manpowerTotal = Number(form.manpower_total);
  const progressPercent = form.progress_percent === '' || form.progress_percent == null
    ? null
    : Number(form.progress_percent);

  if (
    !Number.isFinite(manpowerTotal)
    || !Number.isInteger(manpowerTotal)
    || manpowerTotal < 0
    || manpowerTotal > 10000
  ) {
    errors.manpower_total = SUBMISSION_FIELD_MESSAGES.manpower_total;
  }

  if (
    progressPercent != null
    && (!Number.isFinite(progressPercent) || progressPercent < 0 || progressPercent > 100)
  ) {
    errors.progress_percent = SUBMISSION_FIELD_MESSAGES.progress_percent;
  }

  const rawIssues = Array.isArray(form.issues) ? form.issues : [];
  const issues = rawIssues
    .map((issue) => {
      const title = String(issue?.title ?? '').trim();
      const severity = String(issue?.severity ?? 'normal').trim().toLowerCase();
      return {
        title,
        detail: String(issue?.detail ?? '').trim() || null,
        severity: VALID_ISSUE_SEVERITIES.has(severity) ? severity : 'normal',
        needs_customer_decision: Boolean(issue?.needs_customer_decision),
      };
    })
    .filter((issue) => issue.title);

  const workAreas = Array.isArray(form.work_areas)
    ? form.work_areas.map((item) => String(item).trim()).filter(Boolean)
    : String(form.work_areas ?? '').split(',').map((item) => item.trim()).filter(Boolean);

  return {
    errors,
    payload: {
      work_summary: String(form.work_summary ?? '').trim(),
      work_areas: workAreas,
      manpower_total: errors.manpower_total ? 0 : manpowerTotal,
      progress_percent: errors.progress_percent ? null : progressPercent,
      checklist: normalizeBooleanRecord(form.checklist),
      site_conditions: normalizeStringRecord(form.site_conditions),
      issues,
      tomorrow_plan: String(form.tomorrow_plan ?? '').trim(),
      notes: String(form.notes ?? '').trim() || null,
    },
  };
}

function validationStep(errors) {
  return errors.issues || errors.checklist || errors.tomorrow_plan ? 2 : 1;
}

function apiSubmissionValidationErrors(error) {
  if (error?.status !== 422 || !Array.isArray(error?.payload?.detail)) return {};

  return error.payload.detail.reduce((errors, item) => {
    const location = Array.isArray(item?.loc) ? item.loc : [];
    const field = location.find((part) => SUBMISSION_FIELD_MESSAGES[part]);
    if (field) errors[field] = SUBMISSION_FIELD_MESSAGES[field];
    return errors;
  }, {});
}

function requiredSubmissionErrors(form) {
  const errors = {};
  if (!String(form.work_summary ?? '').trim()) {
    errors.work_summary = SUBMISSION_FIELD_MESSAGES.work_summary;
  }
  if (!String(form.tomorrow_plan ?? '').trim()) {
    errors.tomorrow_plan = SUBMISSION_FIELD_MESSAGES.tomorrow_plan;
  }
  return errors;
}

function apiSubmissionBusinessErrors(error) {
  if (error?.status !== 400) return {};
  const detail = String(error?.detail || '').toLowerCase();
  if (detail.includes('work summary')) {
    return { work_summary: SUBMISSION_FIELD_MESSAGES.work_summary };
  }
  if (detail.includes('tomorrow plan')) {
    return { tomorrow_plan: SUBMISSION_FIELD_MESSAGES.tomorrow_plan };
  }
  return {};
}

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

function fileKey(file) {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

function appendUniqueFiles(currentFiles, selectedFiles) {
  const items = new Map(currentFiles.map((file) => [fileKey(file), file]));
  selectedFiles.forEach((file) => items.set(fileKey(file), file));
  return [...items.values()];
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
  const [fileUploadStates, setFileUploadStates] = useState({});
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const isEditable = !activeSubmission || ['DRAFT', 'CHANGES_REQUESTED'].includes(activeSubmission.status);
  const matchingSubmission = useMemo(
    () => submissions.find(
      (item) => item.project_id === projectId && item.report_date === reportDate,
    ) || null,
    [projectId, reportDate, submissions],
  );
  const filePreviews = useMemo(
    () => files.map((file) => ({
      file,
      key: fileKey(file),
      url: file.type.startsWith('image/') || file.type.startsWith('video/')
        ? URL.createObjectURL(file)
        : '',
    })),
    [files],
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
    setFileUploadStates({});
    setFieldErrors({});
    setStep(1);
  }, [matchingSubmission]);

  useEffect(() => () => {
    filePreviews.forEach((preview) => {
      if (preview.url) URL.revokeObjectURL(preview.url);
    });
  }, [filePreviews]);

  const clearFieldError = (field) => {
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const updateForm = (field, value) => {
    clearFieldError(field);
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateNested = (section, field, value) => {
    clearFieldError(section);
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

  const saveDraft = async ({ quiet = false, manageBusy = true, rethrow = false } = {}) => {
    const prepared = prepareSubmissionPayload(form);
    if (Object.keys(prepared.errors).length > 0) {
      const message = Object.values(prepared.errors)[0];
      setFieldErrors(prepared.errors);
      setStep(validationStep(prepared.errors));
      setNotice({ tone: 'danger', message });
      const validationError = new Error(message);
      validationError.code = 'DAILY_REPORT_FORM_INVALID';
      validationError.fieldErrors = prepared.errors;
      if (rethrow) throw validationError;
      return null;
    }

    if (manageBusy) setBusy('save');
    setNotice(null);
    try {
      const draft = await ensureDraft();
      const updated = await updateDailyReportSubmission(draft.id, prepared.payload);
      setActiveSubmission(updated);
      setSubmissions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setFieldErrors({});
      if (!quiet) setNotice({ tone: 'success', message: 'บันทึกร่างเรียบร้อยแล้ว' });
      return updated;
    } catch (error) {
      console.error('Unable to save the draft.', error);
      const apiErrors = apiSubmissionValidationErrors(error);
      const validationMessage = Object.values(apiErrors)[0];
      if (validationMessage) {
        setFieldErrors(apiErrors);
        setStep(validationStep(apiErrors));
      }
      setNotice({
        tone: 'danger',
        message: error.message === 'กรุณาเลือกโครงการก่อน'
          ? error.message
          : validationMessage || 'ไม่สามารถบันทึกร่างได้ กรุณาลองใหม่อีกครั้ง',
      });
      if (rethrow) throw error;
      return null;
    } finally {
      if (manageBusy) setBusy('');
    }
  };

  const addSelectedFiles = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length === 0) return;
    setFiles((current) => appendUniqueFiles(current, selectedFiles));
    setFileUploadStates((current) => ({
      ...current,
      ...Object.fromEntries(selectedFiles.map((file) => [fileKey(file), 'waiting'])),
    }));
    event.target.value = '';
  };

  const removeSelectedFile = (targetKey) => {
    setFiles((current) => current.filter((file) => fileKey(file) !== targetKey));
    setFileUploadStates((current) => {
      const next = { ...current };
      delete next[targetKey];
      return next;
    });
  };

  const uploadSelectedFiles = async (draft, selectedFiles) => {
    let next = draft;

    for (let index = 0; index < selectedFiles.length; index += 1) {
      const selectedKey = fileKey(selectedFiles[index]);
      setFileUploadStates((current) => ({ ...current, [selectedKey]: 'uploading' }));
      try {
        const uploaded = await uploadDailyReportMedia(draft.id, selectedFiles[index]);
        setFileUploadStates((current) => ({ ...current, [selectedKey]: 'uploaded' }));
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
        const remainingFiles = selectedFiles.slice(index);
        const remainingKeys = new Set(remainingFiles.map((file) => fileKey(file)));
        setFiles(remainingFiles);
        setFileUploadStates((current) => Object.fromEntries(
          Object.entries({ ...current, [selectedKey]: 'failed' })
            .filter(([key]) => remainingKeys.has(key)),
        ));
        throw error;
      }
    }

    setFiles([]);
    setFileUploadStates({});
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
      const requiredErrors = requiredSubmissionErrors(form);
      if (Object.keys(requiredErrors).length > 0) {
        setFieldErrors((current) => ({ ...current, ...requiredErrors }));
        setStep(validationStep(requiredErrors));
        setNotice({ tone: 'danger', message: Object.values(requiredErrors)[0] });
        return;
      }

      const saved = await saveDraft({ quiet: true, manageBusy: false, rethrow: true });
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
      if (error?.code === 'DAILY_REPORT_FORM_INVALID' || error?.status === 422) {
        const validationErrors = error.fieldErrors || apiSubmissionValidationErrors(error);
        const validationMessage = Object.values(validationErrors)[0]
          || 'ข้อมูลบางส่วนไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง';
        setFieldErrors(validationErrors);
        setStep(validationStep(validationErrors));
        setNotice({ tone: 'danger', message: validationMessage });
        return;
      }
      const businessErrors = apiSubmissionBusinessErrors(error);
      if (Object.keys(businessErrors).length > 0) {
        setFieldErrors((current) => ({ ...current, ...businessErrors }));
        setStep(validationStep(businessErrors));
        setNotice({ tone: 'danger', message: Object.values(businessErrors)[0] });
        return;
      }
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
                <label className={`dr-field full dr-work-summary${fieldErrors.work_summary ? ' has-error' : ''}`}>
                  <span>สรุปงานที่ทำ *</span>
                  <textarea
                    rows="5"
                    value={form.work_summary}
                    onChange={(event) => updateForm('work_summary', event.target.value)}
                    disabled={!isEditable}
                    placeholder="เช่น ติดตั้งโครงฝ้าบริเวณทางเดินชั้น 2 และเริ่มประสานงานระบบ…"
                    aria-invalid={Boolean(fieldErrors.work_summary)}
                    aria-describedby={fieldErrors.work_summary ? 'daily-report-work-summary-error' : undefined}
                  />
                  {fieldErrors.work_summary ? (
                    <small id="daily-report-work-summary-error" className="dr-field-error" role="alert">
                      {fieldErrors.work_summary}
                    </small>
                  ) : null}
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
                  <label className={`dr-field${fieldErrors.manpower_total ? ' has-error' : ''}`}>
                    <span><Users size={14} /> จำนวนคนงาน</span>
                    <input
                      type="number"
                      min="0"
                      max="10000"
                      step="1"
                      inputMode="numeric"
                      value={form.manpower_total}
                      onChange={(event) => updateForm('manpower_total', event.target.value)}
                      disabled={!isEditable}
                      aria-invalid={Boolean(fieldErrors.manpower_total)}
                      aria-describedby={fieldErrors.manpower_total ? 'daily-report-manpower-error' : undefined}
                    />
                    {fieldErrors.manpower_total ? (
                      <small id="daily-report-manpower-error" className="dr-field-error" role="alert">
                        {fieldErrors.manpower_total}
                      </small>
                    ) : null}
                  </label>
                  <label className={`dr-field${fieldErrors.progress_percent ? ' has-error' : ''}`}>
                    <span>ความคืบหน้าโดยรวม (%)</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      inputMode="decimal"
                      value={form.progress_percent}
                      onChange={(event) => updateForm('progress_percent', event.target.value)}
                      disabled={!isEditable}
                      aria-invalid={Boolean(fieldErrors.progress_percent)}
                      aria-describedby={fieldErrors.progress_percent ? 'daily-report-progress-error' : undefined}
                    />
                    {fieldErrors.progress_percent ? (
                      <small id="daily-report-progress-error" className="dr-field-error" role="alert">
                        {fieldErrors.progress_percent}
                      </small>
                    ) : null}
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
                    id="daily-report-camera"
                    className="dr-file-input"
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={addSelectedFiles}
                    disabled={!isEditable || Boolean(busy)}
                  />
                  <input
                    id="daily-report-evidence"
                    className="dr-file-input"
                    type="file"
                    multiple
                    accept="image/*,video/*,audio/*"
                    onChange={addSelectedFiles}
                    disabled={!isEditable || Boolean(busy)}
                  />
                  <div className="dr-upload-actions">
                    <label className={`dr-file-picker primary${isEditable && !busy ? '' : ' disabled'}`} htmlFor="daily-report-camera">
                      <Camera size={17} /> ถ่ายรูปหน้างาน
                    </label>
                    <label className={`dr-file-picker${isEditable && !busy ? '' : ' disabled'}`} htmlFor="daily-report-evidence">
                      <CloudUpload size={17} /> เลือกจากเครื่อง
                    </label>
                  </div>
                  {files.length > 0 ? (
                    <div className="dr-pending-media" aria-label="ไฟล์ที่รออัปโหลด">
                      {filePreviews.map((preview) => (
                        <article key={preview.key}>
                          <div className="dr-pending-media-preview">
                            {preview.file.type.startsWith('image/') ? (
                              <img src={preview.url} alt="" />
                            ) : preview.file.type.startsWith('video/') ? (
                              <video src={preview.url} muted />
                            ) : (
                              <CloudUpload aria-hidden="true" />
                            )}
                          </div>
                          <div>
                            <strong>{preview.file.name}</strong>
                            <span className={`state-${fileUploadStates[preview.key] || 'waiting'}`}>
                              {fileUploadStates[preview.key] === 'uploading'
                                ? 'กำลังอัปโหลด…'
                                : fileUploadStates[preview.key] === 'failed'
                                  ? 'อัปโหลดไม่สำเร็จ · พร้อมลองใหม่'
                                  : 'รออัปโหลด'}
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeSelectedFile(preview.key)}
                            disabled={fileUploadStates[preview.key] === 'uploading'}
                            aria-label={`นำ ${preview.file.name} ออกจากรายการ`}
                          >
                            <Trash2 size={16} />
                          </button>
                        </article>
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
                  {files.length > 0 ? (
                    <small className="dr-upload-helper">
                      หากยังไม่กดอัปโหลด ระบบจะอัปโหลดไฟล์เหล่านี้ให้อัตโนมัติก่อนส่งรายงาน
                    </small>
                  ) : null}
                  {(activeSubmission?.media_ids || []).length > 0 ? (
                    <div className="dr-media-chips">
                      {activeSubmission.media_ids.map((mediaId, index) => (
                        <span key={mediaId}>
                          <Check size={14} /> หลักฐาน {index + 1} · อัปโหลดแล้ว
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
                <label className={`dr-field full${fieldErrors.tomorrow_plan ? ' has-error' : ''}`}>
                  <span>แผนงานวันพรุ่งนี้ *</span>
                  <textarea
                    rows="4"
                    value={form.tomorrow_plan}
                    onChange={(event) => updateForm('tomorrow_plan', event.target.value)}
                    disabled={!isEditable}
                    placeholder="เช่น ดำเนินงานติดตั้งโครงฝ้าต่อ และสรุปงานประสานระบบที่ค้างอยู่…"
                    aria-invalid={Boolean(fieldErrors.tomorrow_plan)}
                    aria-describedby={fieldErrors.tomorrow_plan ? 'daily-report-tomorrow-plan-error' : undefined}
                  />
                  {fieldErrors.tomorrow_plan ? (
                    <small id="daily-report-tomorrow-plan-error" className="dr-field-error" role="alert">
                      {fieldErrors.tomorrow_plan}
                    </small>
                  ) : null}
                </label>
              </div>
            ) : null}

            {step === 3 ? (
              <div className="dr-form-section">
                <div className="dr-section-heading">
                  <Send />
                  <div><h3>แผนวันพรุ่งนี้และตรวจทานครั้งสุดท้าย</h3><p>ผู้ดูแลหรือเจ้าของโครงการจะตรวจรายงานนี้ก่อนส่งข้อมูลให้ลูกค้า</p></div>
                </div>
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
