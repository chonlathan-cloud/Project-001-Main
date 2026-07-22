import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  RotateCcw,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

const SWIPE_THRESHOLD = 48;
const DOUBLE_TAP_DELAY = 320;
const MIN_SCALE = 1;
const MAX_SCALE = 4;
const DOUBLE_TAP_SCALE = 2.5;
const INITIAL_VIEW = { scale: MIN_SCALE, x: 0, y: 0 };

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function touchDistance(first, second) {
  return Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY);
}

function touchMidpoint(first, second) {
  return {
    x: (first.clientX + second.clientX) / 2,
    y: (first.clientY + second.clientY) / 2,
  };
}

export default function CustomerPhotoLightbox({
  photos,
  activeIndex,
  onIndexChange,
  onClose,
}) {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const viewportRef = useRef(null);
  const gestureRef = useRef(null);
  const lastTapRef = useRef(0);
  const [view, setView] = useState(INITIAL_VIEW);
  const [loadState, setLoadState] = useState('loading');
  const [retryKey, setRetryKey] = useState(0);
  const activePhoto = photos[activeIndex];
  const hasPrevious = activeIndex > 0;
  const hasNext = activeIndex < photos.length - 1;
  const isZoomed = view.scale > MIN_SCALE + 0.01;

  const clampView = useCallback((scale, x, y) => {
    const bounds = viewportRef.current?.getBoundingClientRect();
    if (!bounds || scale <= MIN_SCALE) return INITIAL_VIEW;
    const maxX = (bounds.width * (scale - MIN_SCALE)) / 2;
    const maxY = (bounds.height * (scale - MIN_SCALE)) / 2;
    return {
      scale,
      x: clamp(x, -maxX, maxX),
      y: clamp(y, -maxY, maxY),
    };
  }, []);

  const resetZoom = useCallback(() => {
    setView(INITIAL_VIEW);
  }, []);

  const zoomBy = useCallback((amount) => {
    setView((current) => {
      const scale = clamp(current.scale + amount, MIN_SCALE, MAX_SCALE);
      return clampView(scale, current.x, current.y);
    });
  }, [clampView]);

  const toggleZoomAt = useCallback((clientX, clientY) => {
    setView((current) => {
      if (current.scale > MIN_SCALE + 0.01) return INITIAL_VIEW;
      const bounds = viewportRef.current?.getBoundingClientRect();
      if (!bounds) return { scale: DOUBLE_TAP_SCALE, x: 0, y: 0 };
      const focalX = clientX - bounds.left - (bounds.width / 2);
      const focalY = clientY - bounds.top - (bounds.height / 2);
      return clampView(
        DOUBLE_TAP_SCALE,
        -focalX * (DOUBLE_TAP_SCALE - MIN_SCALE),
        -focalY * (DOUBLE_TAP_SCALE - MIN_SCALE),
      );
    });
  }, [clampView]);

  const selectPhoto = useCallback((nextIndex) => {
    setView(INITIAL_VIEW);
    setLoadState('loading');
    setRetryKey(0);
    gestureRef.current = null;
    lastTapRef.current = 0;
    onIndexChange(nextIndex);
  }, [onIndexChange]);

  const showPrevious = useCallback(() => {
    if (hasPrevious && !isZoomed) selectPhoto(activeIndex - 1);
  }, [activeIndex, hasPrevious, isZoomed, selectPhoto]);

  const showNext = useCallback(() => {
    if (hasNext && !isZoomed) selectPhoto(activeIndex + 1);
  }, [activeIndex, hasNext, isZoomed, selectPhoto]);

  useEffect(() => {
    const scrollY = window.scrollY;
    const body = document.body;
    const previousStyles = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
    };

    body.style.position = 'fixed';
    body.style.top = `-${scrollY}px`;
    body.style.left = '0';
    body.style.right = '0';
    body.style.width = '100%';
    body.style.overflow = 'hidden';

    const focusFrame = window.requestAnimationFrame(() => closeButtonRef.current?.focus());

    return () => {
      window.cancelAnimationFrame(focusFrame);
      Object.assign(body.style, previousStyles);
      window.scrollTo(0, scrollY);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === 'ArrowLeft' && hasPrevious && !isZoomed) {
        event.preventDefault();
        showPrevious();
        return;
      }

      if (event.key === 'ArrowRight' && hasNext && !isZoomed) {
        event.preventDefault();
        showNext();
        return;
      }

      if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        zoomBy(0.5);
        return;
      }

      if (event.key === '-') {
        event.preventDefault();
        zoomBy(-0.5);
        return;
      }

      if (event.key === '0') {
        event.preventDefault();
        resetZoom();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll(
          'button:not(:disabled), [href], input:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        ),
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (!firstElement || !lastElement) {
        event.preventDefault();
      } else if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [hasNext, hasPrevious, isZoomed, onClose, resetZoom, showNext, showPrevious, zoomBy]);

  useEffect(() => {
    if (loadState !== 'loaded') return undefined;
    const preloadTimer = window.setTimeout(() => {
      [photos[activeIndex + 1], photos[activeIndex - 1]].forEach((photo) => {
        if (!photo?.url) return;
        const image = new window.Image();
        image.decoding = 'async';
        image.src = photo.url;
      });
    }, 250);
    return () => window.clearTimeout(preloadTimer);
  }, [activeIndex, loadState, photos]);

  if (!activePhoto) return null;

  const handleTouchStart = (event) => {
    if (event.touches.length >= 2) {
      event.preventDefault();
      const first = event.touches[0];
      const second = event.touches[1];
      const midpoint = touchMidpoint(first, second);
      const bounds = viewportRef.current?.getBoundingClientRect();
      gestureRef.current = {
        type: 'pinch',
        distance: touchDistance(first, second),
        scale: view.scale,
        x: view.x,
        y: view.y,
        midpoint,
        focalX: bounds ? midpoint.x - bounds.left - (bounds.width / 2) : 0,
        focalY: bounds ? midpoint.y - bounds.top - (bounds.height / 2) : 0,
      };
      return;
    }

    const touch = event.touches[0];
    gestureRef.current = {
      type: isZoomed ? 'pan' : 'swipe',
      startX: touch.clientX,
      startY: touch.clientY,
      x: view.x,
      y: view.y,
      scale: view.scale,
      startedAt: Date.now(),
    };
  };

  const handleTouchMove = (event) => {
    const gesture = gestureRef.current;
    if (!gesture) return;

    if (gesture.type === 'pinch' && event.touches.length >= 2) {
      event.preventDefault();
      const first = event.touches[0];
      const second = event.touches[1];
      const midpoint = touchMidpoint(first, second);
      const distance = touchDistance(first, second);
      const scale = clamp(
        gesture.scale * (distance / Math.max(gesture.distance, 1)),
        MIN_SCALE,
        MAX_SCALE,
      );
      const scaleRatio = scale / gesture.scale;
      setView(clampView(
        scale,
        gesture.x + (midpoint.x - gesture.midpoint.x) - (gesture.focalX * (scaleRatio - 1)),
        gesture.y + (midpoint.y - gesture.midpoint.y) - (gesture.focalY * (scaleRatio - 1)),
      ));
      return;
    }

    if (gesture.type === 'pan' && event.touches.length === 1) {
      event.preventDefault();
      const touch = event.touches[0];
      setView(clampView(
        gesture.scale,
        gesture.x + touch.clientX - gesture.startX,
        gesture.y + touch.clientY - gesture.startY,
      ));
    }
  };

  const handleTouchEnd = (event) => {
    const gesture = gestureRef.current;
    if (!gesture || event.touches.length > 0) {
      if (gesture?.type === 'pinch') gestureRef.current = null;
      return;
    }
    gestureRef.current = null;
    const touch = event.changedTouches[0];
    if (!touch || gesture.type === 'pinch') return;

    const deltaX = touch.clientX - gesture.startX;
    const deltaY = touch.clientY - gesture.startY;
    const isTap = Math.abs(deltaX) < 12
      && Math.abs(deltaY) < 12
      && Date.now() - gesture.startedAt < 280;

    if (isTap) {
      const now = Date.now();
      if (now - lastTapRef.current <= DOUBLE_TAP_DELAY) {
        lastTapRef.current = 0;
        toggleZoomAt(touch.clientX, touch.clientY);
      } else {
        lastTapRef.current = now;
      }
      return;
    }

    if (
      gesture.type === 'swipe'
      && Math.abs(deltaX) >= SWIPE_THRESHOLD
      && Math.abs(deltaX) > Math.abs(deltaY)
    ) {
      if (deltaX < 0) showNext();
      else showPrevious();
    }
  };

  return createPortal(
    <div
      className="dr-photo-lightbox-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="dr-photo-lightbox"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dr-photo-lightbox-title"
        aria-describedby="dr-photo-lightbox-help"
      >
        <header className="dr-photo-lightbox-header">
          <div className="dr-photo-lightbox-title">
            <h2 id="dr-photo-lightbox-title">รูปภาพหน้างาน</h2>
            <span aria-live="polite">รูปที่ {activeIndex + 1} จาก {photos.length}</span>
          </div>
          <div className="dr-photo-lightbox-tools" role="toolbar" aria-label="เครื่องมือขยายรูป">
            <button
              type="button"
              onClick={() => zoomBy(-0.5)}
              disabled={view.scale <= MIN_SCALE}
              aria-label="ย่อรูป"
              title="ย่อรูป"
            >
              <ZoomOut />
            </button>
            <span aria-live="polite">{Math.round(view.scale * 100)}%</span>
            <button
              type="button"
              onClick={() => zoomBy(0.5)}
              disabled={view.scale >= MAX_SCALE}
              aria-label="ขยายรูป"
              title="ขยายรูป"
            >
              <ZoomIn />
            </button>
            <button
              type="button"
              onClick={resetZoom}
              disabled={!isZoomed}
              aria-label="คืนขนาดรูป"
              title="คืนขนาดรูป"
            >
              <RotateCcw />
            </button>
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              aria-label="ปิดรูปภาพ"
              title="ปิดรูปภาพ"
            >
              <X />
            </button>
          </div>
        </header>

        <div className="dr-photo-lightbox-stage">
          <button
            type="button"
            className="dr-photo-lightbox-nav previous"
            onClick={showPrevious}
            disabled={!hasPrevious || isZoomed}
            aria-label="ดูรูปก่อนหน้า"
            title={isZoomed ? 'คืนขนาดรูปก่อนเปลี่ยนรูป' : 'รูปก่อนหน้า'}
          >
            <ChevronLeft />
          </button>

          <figure>
            <div
              ref={viewportRef}
              className={`dr-photo-lightbox-viewport${isZoomed ? ' is-zoomed' : ''}`}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              onTouchCancel={() => { gestureRef.current = null; }}
            >
              <div
                className="dr-photo-lightbox-image-layer"
                style={{
                  transform: `translate3d(${view.x}px, ${view.y}px, 0) scale(${view.scale})`,
                }}
              >
                {activePhoto.thumbnailUrl && activePhoto.thumbnailUrl !== activePhoto.url && loadState !== 'loaded' ? (
                  <img
                    className="dr-photo-lightbox-placeholder"
                    src={activePhoto.thumbnailUrl}
                    alt=""
                    aria-hidden="true"
                    draggable="false"
                  />
                ) : null}
                <img
                  key={`${activePhoto.id}-${retryKey}`}
                  className={`dr-photo-lightbox-original is-${loadState}`}
                  src={activePhoto.url}
                  alt={activePhoto.alt}
                  draggable="false"
                  decoding="async"
                  fetchPriority="high"
                  onLoad={() => setLoadState('loaded')}
                  onError={() => setLoadState('error')}
                />
              </div>

              {loadState === 'loading' ? (
                <div className="dr-photo-lightbox-loading" role="status">
                  <LoaderCircle className="spin" /> กำลังโหลดรูปความละเอียดสูง…
                </div>
              ) : null}
              {loadState === 'error' ? (
                <div className="dr-photo-lightbox-error" role="alert">
                  <span>โหลดรูปความละเอียดสูงไม่สำเร็จ</span>
                  <button
                    type="button"
                    onClick={() => {
                      setLoadState('loading');
                      setRetryKey((current) => current + 1);
                    }}
                  >
                    ลองอีกครั้ง
                  </button>
                </div>
              ) : null}
            </div>
            {activePhoto.fileName ? <figcaption>{activePhoto.fileName}</figcaption> : null}
          </figure>

          <button
            type="button"
            className="dr-photo-lightbox-nav next"
            onClick={showNext}
            disabled={!hasNext || isZoomed}
            aria-label="ดูรูปถัดไป"
            title={isZoomed ? 'คืนขนาดรูปก่อนเปลี่ยนรูป' : 'รูปถัดไป'}
          >
            <ChevronRight />
          </button>
        </div>

        <footer id="dr-photo-lightbox-help">
          ใช้สองนิ้วถ่างเพื่อขยาย · ลากเพื่อเลื่อน · แตะสองครั้งเพื่อขยายหรือคืนขนาด · ที่ขนาดปกติปัดซ้ายหรือขวาเพื่อเปลี่ยนรูป
        </footer>
      </section>
    </div>,
    document.body,
  );
}
