import assert from 'node:assert/strict';
import test from 'node:test';

import { getPublishedPhotoMedia } from './customerReportMedia.js';

test('keeps every published photo when a report has more than eight images', () => {
  const photos = Array.from({ length: 11 }, (_, index) => ({
    id: `photo-${index + 1}`,
    content_type: 'image/jpeg',
  }));

  const result = getPublishedPhotoMedia([
    ...photos,
    { id: 'walkthrough', content_type: 'video/mp4' },
  ]);

  assert.equal(result.length, 11);
  assert.deepEqual(result.map((item) => item.id), photos.map((item) => item.id));
});

test('handles missing media and image content-type casing', () => {
  assert.deepEqual(getPublishedPhotoMedia(), []);
  assert.deepEqual(
    getPublishedPhotoMedia([
      null,
      { id: 'photo', content_type: 'IMAGE/PNG' },
      { id: 'voice', content_type: 'audio/mpeg' },
    ]).map((item) => item.id),
    ['photo'],
  );
});
