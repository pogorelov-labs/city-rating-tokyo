'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { trackError } from '@/lib/track-error';

interface GalleryImage {
  url: string;
  alt: string;
  attribution?: string;
  photographer?: string;
  photographer_url?: string;
  source?: string;
  lqip?: string;
}

interface ImageGalleryProps {
  images: GalleryImage[];
  stationName: string;
}

function GalleryImageCard({
  image,
  onClick,
}: {
  image: GalleryImage;
  onClick: () => void;
}) {
  const [inView, setInView] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Manual IntersectionObserver replaces loading="lazy" which Chrome
  // refuses to trigger for opacity:0 images behind an LQIP layer.
  useEffect(() => {
    const el = cardRef.current;
    if (!el || inView) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); obs.disconnect(); } },
      { rootMargin: '200px' },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [inView]);

  return (
    <div
      ref={cardRef}
      className="relative group overflow-hidden rounded-lg bg-gray-100 aspect-[4/3] cursor-pointer"
      onClick={failed ? undefined : onClick}
    >
      {/* LQIP blur layer — shown until full image loads (or permanently if load fails) */}
      {image.lqip && !loaded && (
        <img
          src={image.lqip}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover"
          style={{ filter: 'blur(20px)', transform: 'scale(1.1)' }}
        />
      )}
      {/* Full-res image — src set only after card enters viewport */}
      {inView && !failed && (
        <img
          src={image.url}
          alt={image.alt}
          onLoad={() => setLoaded(true)}
          onError={() => { setFailed(true); trackError('image', { src: image.url, context: 'gallery' }); }}
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          style={{
            opacity: loaded ? 1 : 0,
            transition: 'opacity 200ms ease-in, transform 300ms',
          }}
        />
      )}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1">
        {image.source === 'unsplash' && image.photographer ? (
          <a
            href={image.photographer_url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-white/80 hover:text-white"
            onClick={(e) => e.stopPropagation()}
          >
            Photo by {image.photographer} on Unsplash
          </a>
        ) : image.attribution ? (
          <span className="text-[10px] text-white/80">{image.attribution}</span>
        ) : null}
      </div>
    </div>
  );
}

function Lightbox({
  image,
  onClose,
  onPrev,
  onNext,
}: {
  image: GalleryImage;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 text-white text-3xl hover:text-gray-300 z-10"
        onClick={onClose}
      >
        &times;
      </button>
      <button
        className="absolute left-4 top-1/2 -translate-y-1/2 text-white text-3xl hover:text-gray-300 z-10 p-2"
        onClick={(e) => { e.stopPropagation(); onPrev(); }}
      >
        &#8249;
      </button>
      <button
        className="absolute right-4 top-1/2 -translate-y-1/2 text-white text-3xl hover:text-gray-300 z-10 p-2"
        onClick={(e) => { e.stopPropagation(); onNext(); }}
      >
        &#8250;
      </button>
      <img
        src={image.url}
        alt={image.alt}
        className="max-h-[85vh] max-w-[90vw] object-contain rounded-lg"
        onClick={(e) => e.stopPropagation()}
        onError={() => trackError('image', { src: image.url, context: 'lightbox' })}
      />
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
        {image.alt}
      </div>
    </div>
  );
}

const INITIAL_SHOW = 6;

export default function ImageGallery({ images, stationName }: ImageGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  const visibleImages = showAll ? images : images.slice(0, INITIAL_SHOW);
  const hasMore = images.length > INITIAL_SHOW;

  const openLightbox = useCallback((i: number) => setLightboxIndex(i), []);
  const closeLightbox = useCallback(() => setLightboxIndex(null), []);
  const prevImage = useCallback(
    () => setLightboxIndex((i) => (i !== null ? (i - 1 + images.length) % images.length : null)),
    [images.length]
  );
  const nextImage = useCallback(
    () => setLightboxIndex((i) => (i !== null ? (i + 1) % images.length : null)),
    [images.length]
  );

  if (images.length === 0) return null;

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">Gallery</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {visibleImages.map((img, i) => (
          <GalleryImageCard key={img.url} image={img} onClick={() => openLightbox(i)} />
        ))}
      </div>
      {hasMore && !showAll && (
        <button
          onClick={() => setShowAll(true)}
          data-umami-event="show-all-photos"
          className="mt-3 text-sm text-blue-600 hover:underline"
        >
          Show all {images.length} photos
        </button>
      )}
      <p className="text-[10px] text-gray-400 mt-2">
        Images via Wikimedia Commons (CC-BY-SA) & Unsplash
      </p>

      {lightboxIndex !== null && images[lightboxIndex] && (
        <Lightbox
          image={images[lightboxIndex]}
          onClose={closeLightbox}
          onPrev={prevImage}
          onNext={nextImage}
        />
      )}
    </section>
  );
}
