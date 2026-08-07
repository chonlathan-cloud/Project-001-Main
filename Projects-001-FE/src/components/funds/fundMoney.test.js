import assert from 'node:assert/strict';
import test from 'node:test';
import {
  addMoney,
  compareMoney,
  formatMoney,
  moneyToMinorUnits,
  normalizeMoney,
  subtractMoney,
} from './fundMoney.js';

test('normalizes decimal money without floating-point calculation', () => {
  assert.equal(normalizeMoney('1000000.5'), '1000000.50');
  assert.equal(addMoney('0.10', '0.20'), '0.30');
  assert.equal(subtractMoney('900000.00', '550000.00'), '350000.00');
});

test('supports the full NUMERIC(15,2) range as exact minor units', () => {
  assert.equal(moneyToMinorUnits('999999999999999.99'), 99999999999999999n);
  assert.equal(compareMoney('999999999999999.99', '999999999999999.98'), 1);
  assert.equal(formatMoney('999999999999999.99'), 'THB 999,999,999,999,999.99');
});

test('rejects values with more than two decimal places', () => {
  assert.equal(moneyToMinorUnits('10.001'), null);
  assert.equal(compareMoney('10.001', '10.00'), null);
});
