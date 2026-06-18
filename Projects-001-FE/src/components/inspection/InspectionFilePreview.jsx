import { FileImage, ImageOff, Loader2 } from 'lucide-react';
import useInspectionSignedUrl from './useInspectionSignedUrl';

export default function InspectionFilePreview({ fileId, label = 'Inspection file', compact = false }) {
  const { signedUrl, contentType, filename, loading, error } = useInspectionSignedUrl(fileId);
  const isImage = contentType ? contentType.startsWith('image/') : true;

  if (!fileId) {
    return (
      <div className={`inspection-file-preview${compact ? ' compact' : ''}`}>
        <ImageOff size={18} />
        <span>No file</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`inspection-file-preview${compact ? ' compact' : ''}`}>
        <Loader2 size={18} className="inspection-spin" />
        <span>Loading preview</span>
      </div>
    );
  }

  if (error || !signedUrl) {
    return (
      <div className={`inspection-file-preview danger${compact ? ' compact' : ''}`}>
        <ImageOff size={18} />
        <span>{error || 'Preview unavailable'}</span>
      </div>
    );
  }

  return (
    <a
      className={`inspection-file-preview ready${compact ? ' compact' : ''}`}
      href={signedUrl}
      target="_blank"
      rel="noreferrer"
      title={filename || label}
    >
      {isImage ? (
        <img src={signedUrl} alt={filename || label} />
      ) : (
        <span className="inspection-file-preview-icon">
          <FileImage size={18} />
        </span>
      )}
      <span>{filename || label}</span>
    </a>
  );
}
