'use client';

import { useState, useRef } from 'react';

interface TooltipProps {
  text: string;
  children: React.ReactNode;
}

export default function Tooltip({ text, children }: TooltipProps) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleEnter = () => {
    clearTimeout(timeoutRef.current);
    // 400ms enter delay so briefly brushing the `?` icon during scroll
    // doesn't trigger a tooltip flash. CRTKY-67.
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };

  const handleLeave = () => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

  return (
    <span
      className="relative inline-flex items-center gap-1"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      {children}
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 text-gray-500 text-[9px] font-bold cursor-help shrink-0">
        ?
      </span>
      {show && (
        <span className="absolute left-0 bottom-full mb-1.5 z-50 w-56 px-2.5 py-1.5 text-xs text-white bg-gray-800 rounded-md shadow-lg leading-relaxed pointer-events-none">
          {text}
        </span>
      )}
    </span>
  );
}
