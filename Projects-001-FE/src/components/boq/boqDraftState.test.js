import assert from 'node:assert/strict';
import test from 'node:test';

import {
  addDraftNode,
  buildSavePayload,
  duplicateDraftItem,
  moveDraftNode,
  moveDraftNodeTo,
  normalizeQuotationDraft,
  removeDraftNode,
  updateDraftComponent,
} from './boqDraftState.js';

function fixture() {
  let nodes = addDraftNode([], 'SECTION');
  const section = nodes[0];
  nodes = addDraftNode(nodes, 'CATEGORY', section.logical_id);
  const category = nodes.find((node) => node.node_kind === 'CATEGORY');
  nodes = addDraftNode(nodes, 'ITEM', category.logical_id);
  nodes = addDraftNode(nodes, 'ITEM', category.logical_id);
  return nodes;
}

test('stable logical IDs survive reorder and move operations', () => {
  const nodes = fixture();
  const items = nodes.filter((node) => node.node_kind === 'ITEM');
  const reordered = moveDraftNode(nodes, items[1].logical_id, 'up');
  assert.deepEqual(
    reordered.filter((node) => node.node_kind === 'ITEM').map((node) => node.logical_id),
    [items[1].logical_id, items[0].logical_id]
  );

  const section = nodes.find((node) => node.node_kind === 'SECTION');
  const moved = moveDraftNodeTo(reordered, items[0].logical_id, section.logical_id);
  assert.equal(
    moved.find((node) => node.logical_id === items[0].logical_id).parent_logical_id,
    section.logical_id
  );
  assert.deepEqual(new Set(moved.map((node) => node.logical_id)), new Set(nodes.map((node) => node.logical_id)));
});

test('quotation save strips calculated payment amounts and preserves immutable identity inputs', () => {
  const quotation = normalizeQuotationDraft({
    title: 'ใบเสนอราคา',
    customer_name: 'บริษัท ทดสอบ จำกัด',
    vat_rate: '7.0000',
    grand_total: '1070.00',
    payment_schedule: [
      { label: 'มัดจำ', percentage: '50.0000', amount: '535.00' },
      { label: 'ส่งมอบ', percentage: '50.0000', amount: '535.00' },
    ],
    commercial_terms: ['ยืนราคา 30 วัน'],
  });
  const payload = buildSavePayload(7, [], quotation);
  assert.equal(payload.expected_version, 7);
  assert.equal(payload.quotation.customer_name, 'บริษัท ทดสอบ จำกัด');
  assert.equal(payload.quotation.payment_schedule[0].amount, undefined);
  assert.equal(payload.quotation.grand_total, undefined);
  assert.deepEqual(payload.quotation.payment_schedule[0], {
    label: 'มัดจำ',
    percentage: '50.0000',
    fixed_amount: null,
  });
});

test('duplicate gets new persistence and logical identity while preserving values', () => {
  const nodes = fixture();
  const source = nodes.find((node) => node.node_kind === 'ITEM');
  const duplicated = duplicateDraftItem(nodes, source.logical_id);
  const copies = duplicated.filter((node) => node.node_kind === 'ITEM');
  assert.equal(copies.length, 3);
  assert.equal(copies[1].id, null);
  assert.notEqual(copies[1].logical_id, source.logical_id);
  assert.equal(copies[1].source_logical_id, source.logical_id);
  assert.equal(copies[1].quantity, source.quantity);
});

test('catalog identity is copied into save payload without creating live master linkage', () => {
  const nodes = fixture();
  const item = nodes.find((node) => node.node_kind === 'ITEM');
  item.catalog_item_id = '11111111-1111-4111-8111-111111111111';
  item.catalog_item_version = 3;
  item.source_logical_id = '22222222-2222-4222-8222-222222222222';
  const payload = buildSavePayload(2, nodes);
  const saved = payload.nodes.find((node) => node.logical_id === item.logical_id);
  assert.equal(saved.catalog_item_id, item.catalog_item_id);
  assert.equal(saved.catalog_item_version, 3);
  assert.equal(saved.source_logical_id, item.source_logical_id);
});

test('remove deletes the complete subtree and save keeps null cost distinct from zero', () => {
  const nodes = fixture();
  const category = nodes.find((node) => node.node_kind === 'CATEGORY');
  assert.equal(removeDraftNode(nodes, category.logical_id).length, 1);

  const item = nodes.find((node) => node.node_kind === 'ITEM');
  let next = updateDraftComponent(nodes, item.logical_id, 'MATERIAL', {
    cost_state: 'PRICED',
    unit_rate: '0.0000',
    explicit_zero_reason: 'Included at no additional cost',
  });
  next = updateDraftComponent(next, item.logical_id, 'LABOR', {
    cost_state: 'NOT_APPLICABLE',
    unit_rate: null,
  });
  const payload = buildSavePayload(4, next);
  const savedItem = payload.nodes.find((node) => node.logical_id === item.logical_id);
  assert.equal(savedItem.components[0].unit_rate, '0.0000');
  assert.equal(savedItem.components[0].explicit_zero_reason, 'Included at no additional cost');
  assert.equal(savedItem.components[1].unit_rate, null);
  assert.equal(payload.expected_version, 4);
});
