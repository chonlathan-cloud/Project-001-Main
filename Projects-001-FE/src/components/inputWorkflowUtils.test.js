import test from 'node:test';
import assert from 'node:assert/strict';
import { createInputSubmissionLock, findOwnedInputRequest, inputErrorStep, isInputOutcomeUnknown, inputStatusLabel } from './inputWorkflowUtils.js';

test('rapid submissions invoke the operation once until it completes; failure permits retry', async () => {
  const lock = createInputSubmissionLock();
  let calls = 0;
  let finish;
  const pending = new Promise((resolve) => { finish = resolve; });
  const submit = async () => {
    if (!lock.acquire()) return;
    try { calls++; await pending; } finally { lock.release(); }
  };
  const first = submit();
  await submit();
  await submit();
  assert.equal(calls, 1);
  finish();
  await first;
  await submit();
  assert.equal(calls, 2);
});

test('transport and server errors require checking history; rejected validation is definite', () => {
  for (const error of [{code:'NETWORK_ERROR'}, {code:'REQUEST_TIMEOUT'}, {code:'UNCONFIRMED_RESULT'}, {status:500}]) assert.equal(isInputOutcomeUnknown(error), true);
  for (const error of [{status:422}, {status:403}, {code:'BAD_REQUEST'}]) assert.equal(isInputOutcomeUnknown(error), false);
});

test('validation returns to capture or details including collapsed tax/profile fields', () => {
  for (const field of ['projectId','receiptFile']) assert.equal(inputErrorStep(field), 1);
  for (const field of ['vendorTaxId','vendorBranch','vendorAddress','requesterName','requestDate','lineItems','customWorkType']) assert.equal(inputErrorStep(field), 2);
});

test('success recovery finds only the requested record in the authenticated list', () => {
  const own = {request_id:'own'};
  assert.equal(findOwnedInputRequest([own], 'own'), own);
  assert.equal(findOwnedInputRequest([own], 'someone-else'), null);
  assert.equal(findOwnedInputRequest([], 'own'), null);
});

test('submitted is distinct from approved or paid; unknown status is not invented', () => {
  assert.equal(inputStatusLabel('PENDING_ADMIN'), 'รอผู้ดูแลตรวจสอบ');
  assert.equal(inputStatusLabel('APPROVED'), 'อนุมัติแล้ว');
  assert.equal(inputStatusLabel('PAID'), 'จ่ายเงินแล้ว');
  assert.equal(inputStatusLabel('UNEXPECTED'), 'ไม่ทราบสถานะ');
});
