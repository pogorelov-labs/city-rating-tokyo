'use client';

import { useEffect } from 'react';
import { getVisitorId } from '@/lib/visitor-id';

export default function VisitorIdentify() {
  useEffect(() => {
    const id = getVisitorId();
    if (id) {
      window.umami?.identify({ visitor_id: id });
    }
  }, []);

  return null;
}
