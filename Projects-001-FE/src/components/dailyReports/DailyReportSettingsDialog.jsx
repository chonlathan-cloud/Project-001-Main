import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Building2,
  Clock3,
  LoaderCircle,
  MapPinned,
  Save,
  X,
} from 'lucide-react';

const WORKING_DAY_OPTIONS = [
  { value: 1, label: 'จ.' },
  { value: 2, label: 'อ.' },
  { value: 3, label: 'พ.' },
  { value: 4, label: 'พฤ.' },
  { value: 5, label: 'ศ.' },
  { value: 6, label: 'ส.' },
  { value: 7, label: 'อา.' },
];

function compactLineTargetId(value) {
  const targetId = String(value || '').trim();
  if (targetId.length <= 10) return targetId;
  return `${targetId.slice(0, 4)}…${targetId.slice(-3)}`;
}

function candidateLabel(candidate) {
  const displayName = String(candidate?.display_name || '').trim();
  const lastSeen = candidate?.last_seen_at
    ? new Date(candidate.last_seen_at).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' })
    : 'ยังไม่มีเวลาล่าสุด';
  return `${displayName || 'กลุ่มที่ยังไม่พบชื่อ'} · ${lastSeen} · ${compactLineTargetId(candidate?.line_target_id)}`;
}

export default function DailyReportSettingsDialog({
  projects,
  projectId,
  settings,
  destination,
  candidates,
  busy,
  dirty,
  onProjectChange,
  onSettingsChange,
  onDestinationChange,
  onClose,
  onSave,
}) {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled)',
      ) || [],
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const currentCandidateExists = candidates.some(
    (item) => item.line_target_id === destination?.line_target_id,
  );
  const selectedDays = settings?.working_days || [1, 2, 3, 4, 5, 6];

  return createPortal(
    <div
      className="dr-settings-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !dirty) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="dr-settings-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dr-settings-title"
        onKeyDown={handleKeyDown}
      >
        <header>
          <div>
            <span className="dr-eyebrow">OWNER CONFIGURATION</span>
            <h2 id="dr-settings-title">Project report settings</h2>
            <p>Configure the reporting company, schedule, and customer LINE group for this project.</p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="dr-settings-close"
            onClick={onClose}
            aria-label="Close settings"
          >
            <X />
          </button>
        </header>

        <div className="dr-settings-dialog-body">
          <section className="dr-settings-section">
            <div className="dr-section-heading">
              <Building2 />
              <div>
                <h3>บริษัทเจ้าของรายงาน</h3>
                <p>ชื่อนี้จะแสดงใน Customer Report และถูกบันทึกไว้กับแต่ละฉบับที่เผยแพร่</p>
              </div>
            </div>
            <div className="dr-form-grid">
              <label className="dr-field full">
                <span>ชื่อบริษัทที่ใช้ในรายงานลูกค้า</span>
                <input
                  value={settings?.reporting_company_name || ''}
                  onChange={(event) => onSettingsChange({ reporting_company_name: event.target.value })}
                  disabled={!settings}
                  placeholder="เช่น บริษัท ระย้าดี จำกัด"
                  autoComplete="organization"
                  maxLength="200"
                  required
                />
                <small>ค่าเริ่มต้นมาจาก Company ในโปรไฟล์ Owner/Admin และสามารถกำหนดแยกในแต่ละโครงการได้</small>
              </label>
            </div>
          </section>

          <section className="dr-settings-section">
            <div className="dr-section-heading">
              <Clock3 />
              <div><h3>Schedule and deadlines</h3><p>All times use the selected project timezone.</p></div>
            </div>
            <div className="dr-form-grid">
              <label className="dr-field">
                <span>Project</span>
                <select value={projectId} onChange={(event) => onProjectChange(event.target.value)}>
                  {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label className="dr-field">
                <span>Timezone</span>
                <input
                  value={settings?.timezone || 'Asia/Bangkok'}
                  onChange={(event) => onSettingsChange({ timezone: event.target.value })}
                  disabled={!settings}
                />
              </label>
              {[
                ['cycle_creation_time', 'สร้างรอบรายงาน', '06:00'],
                ['first_reminder_time', 'แจ้งเตือนครั้งแรก', '16:00'],
                ['submission_due_time', 'กำหนดส่งของผู้รับเหมา', '17:00'],
                ['draft_time', 'สร้างร่างสรุป', '18:00'],
                ['review_target_time', 'เป้าหมายเวลาตรวจ', '19:00'],
              ].map(([field, label, fallback]) => (
                <label className="dr-field" key={field}>
                  <span>{label}</span>
                  <input
                    type="time"
                    value={settings?.[field] || fallback}
                    onChange={(event) => onSettingsChange({ [field]: event.target.value })}
                    disabled={!settings}
                  />
                </label>
              ))}
              <label className="dr-field">
                <span>แจ้งว่าส่งช้าหลังครบกำหนด (นาที)</span>
                <input
                  type="number"
                  min="0"
                  max="1440"
                  value={settings?.overdue_grace_minutes ?? 15}
                  onChange={(event) => onSettingsChange({ overdue_grace_minutes: Number(event.target.value) })}
                  disabled={!settings}
                />
              </label>
              <label className="dr-field">
                <span>แจ้งเตือนก่อนกำหนด (นาที)</span>
                <input
                  value={(settings?.reminder_minutes_before || [60]).join(', ')}
                  onChange={(event) => onSettingsChange({
                    reminder_minutes_before: event.target.value
                      .split(',')
                      .map((item) => Number(item.trim()))
                      .filter((item) => Number.isFinite(item) && item >= 0),
                  })}
                  disabled={!settings}
                  placeholder="60, 15"
                />
              </label>
              <fieldset className="dr-field dr-working-days">
                <legend>วันทำงานของโครงการ</legend>
                <div>
                  {WORKING_DAY_OPTIONS.map((day) => {
                    const checked = selectedDays.includes(day.value);
                    return (
                      <label key={day.value} className={checked ? 'selected' : ''}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => onSettingsChange({
                            working_days: checked
                              ? selectedDays.filter((value) => value !== day.value)
                              : [...selectedDays, day.value].sort((left, right) => left - right),
                          })}
                          disabled={!settings}
                        />
                        <span>{day.label}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
              <label className="dr-settings-toggle">
                <input
                  type="checkbox"
                  checked={settings?.enabled !== false}
                  onChange={(event) => onSettingsChange({ enabled: event.target.checked })}
                  disabled={!settings}
                />
                <span><strong>Daily reporting enabled</strong>Create cycles and send reminders.</span>
              </label>
            </div>
          </section>

          <section className="dr-settings-section">
            <div className="dr-section-heading">
              <MapPinned />
              <div><h3>Customer LINE group</h3><p>Only groups discovered from verified LINE webhook activity are available.</p></div>
            </div>
            <div className="dr-form-grid">
              <label className="dr-field full">
                <span>กลุ่ม LINE ที่ระบบค้นพบ</span>
                <select
                  value={destination?.line_target_id || ''}
                  onChange={(event) => {
                    const candidate = candidates.find((item) => item.line_target_id === event.target.value);
                    onDestinationChange({
                      line_target_id: candidate?.line_target_id || null,
                      display_name: candidate?.display_name || null,
                      target_type: 'group',
                    });
                  }}
                  disabled={!destination}
                >
                  <option value="">ยังไม่เลือกกลุ่ม LINE</option>
                  {destination?.line_target_id && !currentCandidateExists ? (
                    <option value={destination.line_target_id} disabled>
                      ปลายทางเดิมไม่ใช่กลุ่มที่ระบบค้นพบ — กรุณาเลือกใหม่
                    </option>
                  ) : null}
                  {candidates.map((item) => (
                    <option key={item.line_target_id} value={item.line_target_id}>
                      {candidateLabel(item)}
                    </option>
                  ))}
                </select>
                {candidates.length === 0 ? (
                  <small>ยังไม่พบกลุ่ม ให้เพิ่มบอตเข้ากลุ่มและส่งข้อความหนึ่งครั้ง แล้วเปิดหน้าต่างนี้ใหม่</small>
                ) : null}
              </label>
              <label className="dr-settings-toggle">
                <input
                  type="checkbox"
                  checked={destination?.status === 'ACTIVE'}
                  onChange={(event) => onDestinationChange({
                    status: event.target.checked ? 'ACTIVE' : 'INACTIVE',
                  })}
                  disabled={!destination || (!destination.line_target_id && destination.status !== 'ACTIVE')}
                />
                <span><strong>LINE delivery active</strong>Send the approved summary to the selected project group.</span>
              </label>
            </div>
          </section>
        </div>

        <footer>
          <span>{dirty ? 'You have unsaved changes.' : 'Settings are up to date.'}</span>
          <div>
            <button type="button" className="dr-button secondary" onClick={onClose}>Cancel</button>
            <button
              type="button"
              className="dr-button primary"
              onClick={onSave}
              disabled={
                !settings
                || !String(settings.reporting_company_name || '').trim()
                || busy === 'settings-save'
                || !dirty
              }
            >
              {busy === 'settings-save' ? <LoaderCircle className="spin" /> : <Save />} Save settings
            </button>
          </div>
        </footer>
      </section>
    </div>,
    document.body,
  );
}
