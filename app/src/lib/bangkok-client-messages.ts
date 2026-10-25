import type messages from '@/messages/en/common.json';

/** Rent notes render on the client; district narratives stay server-only. */
export function bangkokClientMessages(all: typeof messages) {
  const shared = Object.fromEntries(Object.entries(all).filter(([namespace]) =>
    !['bangkok', 'quietness', 'air', 'safetyFacts', 'institutions'].includes(namespace)));
  return { ...shared, bangkok: { rent: all.bangkok.rent } };
}
