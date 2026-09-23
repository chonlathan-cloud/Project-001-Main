import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildLegacySheetOptions,
  getLegacyBoqPresentation,
} from './legacyBoqPresentation.js';

test('native V2 project without legacy rows hides the legacy workbench', () => {
  assert.deepEqual(
    getLegacyBoqPresentation({ legacyHistoryOnly: true }),
    {
      hasLegacyRows: false,
      nativeOnly: true,
      collapseHistory: false,
      showIncompleteWarning: false,
      navigationLabel: 'Legacy BOQ History',
    },
  );
});

test('native V2 project with retained rows exposes a collapsed read-only archive', () => {
  const presentation = getLegacyBoqPresentation({
    legacyHistoryOnly: true,
    hasCustomerBoq: true,
  });
  assert.equal(presentation.nativeOnly, false);
  assert.equal(presentation.collapseHistory, true);
  assert.equal(presentation.showIncompleteWarning, false);
});

test('active legacy project keeps its incomplete dual-BOQ warning', () => {
  const presentation = getLegacyBoqPresentation({
    hasCustomerBoq: true,
    hasSubcontractorBoq: false,
  });
  assert.equal(presentation.nativeOnly, false);
  assert.equal(presentation.collapseHistory, false);
  assert.equal(presentation.showIncompleteWarning, true);
  assert.equal(presentation.navigationLabel, 'BOQ Comparison');
});

test('sheet filters include only sheet names represented by visible legacy rows', () => {
  const options = buildLegacySheetOptions([
    { sheetName: 'EE' },
    { sheetName: 'ee' },
    { sheetName: 'Custom' },
    { sheetName: '' },
  ], 'All legacy sheets');

  assert.deepEqual(options, [
    { value: 'ALL', label: 'All legacy sheets', count: 4 },
    { value: 'EE', label: 'EE', count: 2 },
    { value: 'CUSTOM', label: 'Custom', count: 1 },
  ]);
  assert.equal(options.some((option) => option.label === 'AC'), false);
});
