import { statusTone } from './dailyReportUtils';

const STATUS_LABELS = {
  th: {
    SCHEDULED: 'กำหนดเวลาแล้ว',
    COLLECTING: 'กำลังรวบรวมข้อมูล',
    DRAFT: 'ฉบับร่าง',
    DRAFTING: 'กำลังจัดทำร่าง',
    SUBMITTED: 'ส่งแล้ว',
    RESUBMITTED: 'ส่งฉบับแก้ไขแล้ว',
    PENDING_REVIEW: 'รอตรวจสอบ',
    CHANGES_REQUESTED: 'กรุณาแก้ไข',
    INCLUDED: 'รวมในรายงานแล้ว',
    EXCLUDED: 'ไม่นำไปรวมในรายงาน',
    LOCKED: 'ล็อกแล้ว',
    WITHDRAWN: 'ถอนรายงานแล้ว',
    CORRECTION_DRAFT: 'ร่างฉบับแก้ไข',
    APPROVED: 'อนุมัติแล้ว',
    PUBLISHED: 'เผยแพร่แล้ว',
    CLOSED: 'ปิดรอบแล้ว',
    ACCEPTED: 'รับทราบแล้ว',
    SENT: 'ส่งสำเร็จ',
    FAILED: 'ส่งไม่สำเร็จ',
    OVERDUE: 'เกินกำหนด',
    CANCELLED: 'ยกเลิกแล้ว',
    NO_WORK: 'ไม่มีงาน',
    PARTIALLY_SUBMITTED: 'ส่งข้อมูลบางส่วนแล้ว',
    UNKNOWN: 'ไม่ทราบสถานะ',
  },
};

export function DailyReportStatusBadge({ status, locale = 'en' }) {
  const normalizedStatus = String(status || 'UNKNOWN').toUpperCase();
  const label = locale === 'th'
    ? STATUS_LABELS.th[normalizedStatus] || STATUS_LABELS.th.UNKNOWN
    : normalizedStatus.replaceAll('_', ' ');

  return (
    <span className={`dr-status tone-${statusTone(status)}`}>
      {label}
    </span>
  );
}

export function DailyReportNotice({ tone = 'info', children }) {
  if (!children) return null;
  return <div className={`dr-notice tone-${tone}`}>{children}</div>;
}
