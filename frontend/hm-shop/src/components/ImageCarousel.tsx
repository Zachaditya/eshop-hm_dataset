"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";

type Slide = { src: string; alt?: string };

export default function ImageCarousel({
  slides,
  autoPlay = true,
  intervalMs = 4500,
  className = "",
  heightClass = "h-[400px]",
}: {
  slides: Slide[];
  autoPlay?: boolean;
  intervalMs?: number;
  className?: string;
  heightClass?: string;
}) {
  const safeSlides = useMemo(() => slides.slice(0, 6), [slides]);
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);

  const n = safeSlides.length;

  const go = (next: number) => {
    if (n === 0) return;
    setIdx((next + n) % n);
  };

  const next = () => go(idx + 1);
  const prev = () => go(idx - 1);

  useEffect(() => {
    if (!autoPlay || paused || n <= 1) return;
    const t = setInterval(() => {
      setIdx((i) => (i + 1) % n);
    }, intervalMs);
    return () => clearInterval(t);
  }, [autoPlay, paused, intervalMs, n]);

  if (n === 0) return null;

  return (
    <div
      className={`relative overflow-hidden rounded-3xl border border-neutral-200 bg-neutral-100 shadow-sm ${className}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-roledescription="carousel"
    >
      {/* slides */}
      <div className="relative aspect-[16/9] w-full">
        {safeSlides.map((s, i) => (
          <div
            key={s.src}
            className={`absolute inset-0 transition-opacity duration-500 ${
              i === idx ? "opacity-100" : "opacity-0"
            }`}
            aria-hidden={i !== idx}
          >
            <Image
              src={s.src}
              alt={s.alt ?? ""} // decorative? keep empty string
              fill
              priority={i === 0}
              className="object-cover"
              sizes="(min-width: 1024px) 900px, 100vw"
            />
          </div>
        ))}
      </div>

      {/* gradient for readability */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/35 to-transparent" />

      {/* arrows */}
      <button
        type="button"
        onClick={prev}
        aria-label="Previous slide"
        className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-white/85 px-3 py-2 text-sm font-medium text-neutral-900 shadow hover:bg-white"
      >
        ←
      </button>
      <button
        type="button"
        onClick={next}
        aria-label="Next slide"
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-white/85 px-3 py-2 text-sm font-medium text-neutral-900 shadow hover:bg-white"
      >
        →
      </button>

      {/* dots */}
      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-2">
        {safeSlides.map((_, i) => (
          <button
            key={i}
            type="button"
            onClick={() => go(i)}
            aria-label={`Go to slide ${i + 1}`}
            className={`h-2.5 w-2.5 rounded-full transition ${
              i === idx ? "bg-white" : "bg-white/50 hover:bg-white/70"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
