'use client';

import { useState } from 'react';

interface GalleryImage {
  url: string;
  alt: string;
  attribution?: string;
}

interface ImageGalleryProps {
  images: GalleryImage[];
  stationName: string;
}

function GalleryImage({ image }: { image: GalleryImage }) {
  const [failed, setFailed] = useState(false);

  if (failed) return null;

  return (
    <div className="relative group overflow-hidden rounded-lg bg-gray-100 aspect-[4/3]">
      <img
        src={image.url}
        alt={image.alt}
        loading="lazy"
        onError={() => setFailed(true)}
        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
      {image.attribution && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1">
          <span className="text-[10px] text-white/80">{image.attribution}</span>
        </div>
      )}
    </div>
  );
}

export default function ImageGallery({ images, stationName }: ImageGalleryProps) {
  const [visibleCount, setVisibleCount] = useState(0);

  // Track how many actually loaded
  const handleLoad = () => setVisibleCount((c) => c + 1);

  if (images.length === 0) return null;

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">Gallery</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {images.map((img, i) => (
          <GalleryImage key={i} image={img} />
        ))}
      </div>
      <p className="text-[10px] text-gray-400 mt-2">
        Images via Wikimedia Commons (CC-BY-SA)
      </p>
    </section>
  );
}
