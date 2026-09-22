import assert from 'node:assert/strict';
import test from 'node:test';

import {
  addMediaToVisualPages,
  chunkScopeRows,
  defaultDocumentSections,
  legacyPagesFromSections,
  moveDocumentSection,
  normalizeDocumentSections,
  removeVisualEntry,
  toggleDocumentSection,
} from './quotationDocumentState.js';

test('document sections preserve required placement and legacy defaults', () => {
  const sections = defaultDocumentSections(['BOQ', 'PAYMENT_TERMS', 'COMMERCIAL_TERMS']);
  assert.equal(sections[0].section_type, 'SUMMARY');
  assert.equal(sections[0].enabled, true);
  assert.equal(sections[1].section_type, 'DETAILED_BOQ');
  assert.equal(sections.find((item) => item.section_type === 'VISUAL').enabled, false);
  assert.equal(sections.at(-1).section_type, 'ACCEPTANCE');
  assert.deepEqual(legacyPagesFromSections(sections), ['BOQ', 'PAYMENT_TERMS', 'COMMERCIAL_TERMS']);
});

test('required sections cannot be disabled and acceptance remains last', () => {
  const sections = defaultDocumentSections();
  assert.equal(toggleDocumentSection(sections, 'SUMMARY', false)[0].enabled, true);
  const accepted = toggleDocumentSection(sections, 'ACCEPTANCE', true);
  const moved = moveDocumentSection(accepted, 'ACCEPTANCE', 'up');
  assert.equal(moved.at(-1).section_type, 'ACCEPTANCE');
  assert.equal(moved.at(-1).enabled, true);
});

test('normalization repairs missing sections without duplicating types', () => {
  const normalized = normalizeDocumentSections([
    { section_type: 'SUMMARY', enabled: false, position: 4 },
    { section_type: 'DETAILED_BOQ', enabled: true, position: 2 },
  ]);
  assert.equal(normalized.length, 6);
  assert.equal(new Set(normalized.map((item) => item.section_type)).size, 6);
  assert.equal(normalized[0].section_type, 'SUMMARY');
  assert.equal(normalized[0].enabled, true);
});

test('visual media fills the current layout then creates a new page', () => {
  const first = addMediaToVisualPages([], 'media-1');
  const second = addMediaToVisualPages(first, 'media-2');
  const third = addMediaToVisualPages(second, 'media-3');
  assert.equal(second.length, 1);
  assert.equal(second[0].entries.length, 2);
  assert.equal(third.length, 2);
  assert.deepEqual(third.map((page) => page.position), [0, 1]);
});

test('removing the final visual entry also removes its invalid empty page', () => {
  const pages = addMediaToVisualPages([], 'media-1');
  assert.deepEqual(removeVisualEntry(pages, 0, 'media-1'), []);
});

test('scope pagination preserves all included rows and removes excluded rows', () => {
  const rows = Array.from({ length: 15 }, (_, index) => ({
    logical_id: `row-${index}`,
    node_kind: 'ITEM',
    inclusion_state: index === 3 ? 'EXCLUDED' : 'REQUIRED',
  }));
  const chunks = chunkScopeRows(rows, 5);
  assert.equal(chunks.flat().length, 14);
  assert.ok(chunks.every((chunk) => chunk.length <= 5));
});
