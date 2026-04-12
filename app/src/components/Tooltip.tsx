'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useIsTouch } from '@/lib/use-is-touch';

interface TooltipProps {
  /** Tooltip body. Accepts any ReactNode so callers can render rich multi-line layouts. */
  content: React.ReactNode;
  /** The interactive element (label, bar, icon) that triggers the tooltip on hover. */
  children: React.ReactNode;
  /**
   * When true (default), a plain `?` glyph is rendered after `children` as a
   * small helper icon. Call sites wrapping a bar or another visual can set
   * this to false to suppress the extra icon. CRTKY-68.
   */
  showHelpIcon?: boolean;
  /**
   * Wrapper element. `'span'` (default) is inline and suitable for wrapping
   * a text label. `'div'` is block-level and safe for wrapping block children
   * like a flex-sized bar. Span-wrapping a div produces invalid HTML and
   * breaks flex-1 sizing.
   */
  wrapper?: 'span' | 'div';
  /**
   * Extra classes appended to the wrapper. Needed when the wrapper itself
   * needs a sizing rule from its parent flex context (e.g. `flex-1` so the
   * bar inside can fill the row). Without this escape hatch, wrapping a
   * flex-sized child collapses the wrapper to 0 width.
   */
  className?: string;
}

export default function Tooltip({
  content,
  children,
  showHelpIcon = true,
  wrapper = 'span',
  className = '',
}: TooltipProps) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapperRef = useRef<HTMLElement>(null);
  const isTouch = useIsTouch();

  // Desktop: hover handlers
  const handleEnter = () => {
    if (isTouch) return;
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };

  const handleLeave = () => {
    if (isTouch) return;
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

  // Touch: tap to toggle
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isTouch) return;
      e.preventDefault();
      e.stopPropagation();
      setShow((prev) => !prev);
    },
    [isTouch],
  );

  // Touch: close on tap outside
  useEffect(() => {
    if (!isTouch || !show) return;
    const handleOutside = (e: PointerEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShow(false);
      }
    };
    document.addEventListener('pointerdown', handleOutside);
    return () => document.removeEventListener('pointerdown', handleOutside);
  }, [isTouch, show]);

  const Wrapper = wrapper;
  const baseClass = wrapper === 'div'
    ? 'relative flex items-center gap-1'
    : 'relative inline-flex items-center gap-1';
  const wrapperClass = className ? `${baseClass} ${className}` : baseClass;

  return (
    <Wrapper
      ref={wrapperRef as React.Ref<HTMLDivElement & HTMLSpanElement>}
      className={wrapperClass}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={handleClick}
    >
      {children}
      {showHelpIcon && (
        <span className="text-gray-300 text-[13px] leading-none cursor-help shrink-0">
          ?
        </span>
      )}
      {show && (
        <span className="absolute left-0 bottom-full mb-1.5 z-50 w-56 px-2.5 py-1.5 text-xs text-white bg-gray-800 rounded-md shadow-lg leading-relaxed pointer-events-none">
          {content}
        </span>
      )}
    </Wrapper>
  );
}
