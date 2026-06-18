import { useEffect, useState } from 'react';
import { getInspectionFileSignedUrl } from '../../api';

const EMPTY_SIGNED_FILE = {
  fileId: '',
  signedUrl: '',
  contentType: '',
  filename: '',
  loading: false,
  error: '',
};

export default function useInspectionSignedUrl(fileId) {
  const [state, setState] = useState(EMPTY_SIGNED_FILE);

  useEffect(() => {
    if (!fileId) return undefined;

    let cancelled = false;
    getInspectionFileSignedUrl(fileId)
      .then((payload) => {
        if (cancelled) return;
        setState({
          fileId,
          signedUrl: payload?.signed_url || '',
          contentType: payload?.content_type || '',
          filename: payload?.original_filename || '',
          loading: false,
          error: '',
        });
      })
      .catch((error) => {
        if (cancelled) return;
        setState({
          fileId,
          signedUrl: '',
          contentType: '',
          filename: '',
          loading: false,
          error: error.message || 'Failed to load file preview.',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [fileId]);

  if (!fileId) return EMPTY_SIGNED_FILE;
  if (state.fileId !== fileId) {
    return { ...EMPTY_SIGNED_FILE, fileId, loading: true };
  }
  return state;
}
