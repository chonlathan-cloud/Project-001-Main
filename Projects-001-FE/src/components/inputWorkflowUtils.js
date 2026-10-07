export const inputStatusLabel = (status) => ({
  DRAFT: 'แบบร่าง', PENDING: 'รอตรวจสอบ', PENDING_ADMIN: 'รอผู้ดูแลตรวจสอบ',
  APPROVED: 'อนุมัติแล้ว', PAID: 'จ่ายเงินแล้ว', REJECTED: 'ไม่อนุมัติ',
}[status] || 'ไม่ทราบสถานะ');

export const inputMoney = (value) => Number(value || 0).toLocaleString('th-TH', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

export function inputDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok' });
}

export function inputErrorStep(field) {
  return ['projectId', 'receiptFile'].includes(field) ? 1 : 2;
}

// A failed transport response cannot establish whether the server committed the POST.
export function isInputOutcomeUnknown(error) {
  return ['REQUEST_TIMEOUT', 'NETWORK_ERROR', 'UNCONFIRMED_RESULT'].includes(error?.code) || Number(error?.status) >= 500;
}

export function createInputSubmissionLock() {
  let locked = false;
  return {
    acquire() { if (locked) return false; locked = true; return true; },
    release() { locked = false; },
  };
}

export function findOwnedInputRequest(items, requestId) {
  return items.find((item) => String(item.request_id) === String(requestId)) || null;
}
