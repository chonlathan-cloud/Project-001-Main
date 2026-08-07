const MINOR_UNITS = 100n;

function cleanMoneyInput(value) {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '';
    return value.toFixed(2);
  }

  return String(value ?? '')
    .trim()
    .replace(/,/g, '')
    .replace(/^(-?)\./, '$10.');
}

export function moneyToMinorUnits(value) {
  const cleaned = cleanMoneyInput(value);
  const match = cleaned.match(/^([+-]?)(\d+)(?:\.(\d{0,2}))?$/);
  if (!match) return null;

  const sign = match[1] === '-' ? -1n : 1n;
  const whole = BigInt(match[2]);
  const fraction = BigInt((match[3] || '').padEnd(2, '0'));
  return sign * ((whole * MINOR_UNITS) + fraction);
}

export function minorUnitsToMoney(value) {
  const minor = typeof value === 'bigint' ? value : 0n;
  const sign = minor < 0n ? '-' : '';
  const absolute = minor < 0n ? -minor : minor;
  const whole = absolute / MINOR_UNITS;
  const fraction = String(absolute % MINOR_UNITS).padStart(2, '0');
  return `${sign}${whole}.${fraction}`;
}

export function normalizeMoney(value, fallback = '0.00') {
  const minor = moneyToMinorUnits(value);
  return minor == null ? fallback : minorUnitsToMoney(minor);
}

export function addMoney(left, right) {
  const leftMinor = moneyToMinorUnits(left) ?? 0n;
  const rightMinor = moneyToMinorUnits(right) ?? 0n;
  return minorUnitsToMoney(leftMinor + rightMinor);
}

export function subtractMoney(left, right) {
  const leftMinor = moneyToMinorUnits(left) ?? 0n;
  const rightMinor = moneyToMinorUnits(right) ?? 0n;
  return minorUnitsToMoney(leftMinor - rightMinor);
}

export function compareMoney(left, right) {
  const leftMinor = moneyToMinorUnits(left);
  const rightMinor = moneyToMinorUnits(right);
  if (leftMinor == null || rightMinor == null) return null;
  if (leftMinor === rightMinor) return 0;
  return leftMinor > rightMinor ? 1 : -1;
}

export function isPositiveMoney(value) {
  const minor = moneyToMinorUnits(value);
  return minor != null && minor > 0n;
}

export function formatMoney(value, currency = 'THB') {
  const minor = moneyToMinorUnits(value) ?? 0n;
  const negative = minor < 0n;
  const absolute = negative ? -minor : minor;
  const whole = absolute / MINOR_UNITS;
  const fraction = String(absolute % MINOR_UNITS).padStart(2, '0');
  const groupedWhole = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(whole);
  return `${negative ? '-' : ''}${currency} ${groupedWhole}.${fraction}`;
}

export function createIdempotencyKey() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `fund-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
