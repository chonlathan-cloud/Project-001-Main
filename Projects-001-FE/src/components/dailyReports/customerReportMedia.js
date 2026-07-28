export function getPublishedPhotoMedia(media) {
  if (!Array.isArray(media)) return [];

  return media.filter((item) => (
    String(item?.content_type || '').toLowerCase().startsWith('image/')
  ));
}
