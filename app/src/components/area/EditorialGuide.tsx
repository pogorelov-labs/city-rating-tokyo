'use client';

/**
 * Editorial guide (E-1/P2-dark) — narrative + evidence for one entity.
 *
 * Renders NOTHING unless (a) the EDITORIAL_ENABLED flag is on and (b) the
 * adapter marked the entity copy-eligible (E-5 human-sign-off key). While
 * dark it is structurally inert: no fetch, no DOM.
 */
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { editorialCardMeta, editorialRecord } from '@/lib/editorial-research';
import styles from './editorial-guide.module.css';

interface GuideItem { en: string; claims: string[] }
interface GuideChunk {
  key: string;
  guide: {
    lead: { en: string; claims: string[] };
    sections: Record<string, GuideItem[]>;
    uncertainties: string[];
    attribution_required: string[];
  };
  claims: { id: string; status: string; kind: string;
            temporal: { event: string | null; observed: string | null; recheck: string | null };
            limitations: string[]; conflicts_with: string[] }[];
  sources: { id: string; url: string; body_read: boolean;
             attribution: { publisher: string; family: string } }[];
}

const SECTION_ORDER: { key: string; label: 'strengths' | 'consider' }[] = [
  { key: 'strengths', label: 'strengths' },
  { key: 'tradeoffs', label: 'consider' },
];

export default function EditorialGuide({ areaId, chunkHref }: { areaId: string; chunkHref: string | null }) {
  const t = useTranslations('areaGuide');
  const [chunk, setChunk] = useState<GuideChunk | null>(null);
  const [failed, setFailed] = useState(false);

  const eligible = editorialCardMeta(areaId) !== null && !editorialCardMeta(areaId)?.dataOnly
    && Boolean(editorialRecord(areaId)?.copy_eligible);

  const load = useCallback(() => {
    if (!chunkHref) return;
    fetch(chunkHref)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((c: GuideChunk) => setChunk(c))
      .catch(() => setFailed(true));
  }, [chunkHref]);

  useEffect(() => {
    if (eligible && chunkHref && !chunk && !failed) load();
  }, [eligible, chunkHref, chunk, failed, load]);

  // DARK: no flag, or no human sign-off -> structurally inert.
  if (!eligible || failed || !chunk) return null;

  const attribution = new Set(chunk.guide.attribution_required);

  return (
    <div className={styles.guide} aria-label={t('editorial.guide')}>
      {chunk.guide.lead.en && (
        <p className={styles.lead}>{chunk.guide.lead.en}
          {chunk.guide.lead.claims.some(id => attribution.has(id))
            && <span className={styles.attribution}> ({t('editorial.attributionNotice')})</span>}
        </p>
      )}
      {SECTION_ORDER.map(({ key, label }) => {
        const items = chunk.guide.sections[key] ?? [];
        if (!items.length) return null;
        return (
          <section key={key}>
            <h3>{t(label)}</h3>
            <ul>
              {items.map((it, i) => (
                <li key={i}>
                  {it.en}
                  {it.claims.some(id => attribution.has(id))
                    && <span className={styles.attribution}> ({t('editorial.attributionNotice')})</span>}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {chunk.guide.uncertainties.length > 0 && (
        <details className={styles.uncertainties}>
          <summary>{t('editorial.uncertainties')}</summary>
          <ul>{chunk.guide.uncertainties.map((u, i) => <li key={i}>{u}</li>)}</ul>
        </details>
      )}
      <details className={styles.evidence}>
        <summary>{t('editorial.evidence')}</summary>
        <dl>
          {[...attribution, ...chunk.guide.lead.claims].slice(0, 0).map(id => <dt key={id}>{id}</dt>)}
          {chunk.claims.map(c => (
            <div key={c.id}>
              {(() => { const ek: EvidenceKey = statusKey(c.status); return <dt>{c.id} · {t(`evidence.${ek}`)}</dt>; })()}
              <dd>
                {c.temporal.event && <p>{t('editorial.eventDate', { date: c.temporal.event })}</p>}
                {c.limitations.map((l, i) => <p key={i}>{l}</p>)}
              </dd>
            </div>
          ))}
        </dl>
        <ul className={styles.sources}>
          {chunk.sources.map(s => (
            <li key={s.id}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.attribution.publisher}</a></li>
          ))}
        </ul>
      </details>
    </div>
  );
}

type EvidenceKey = 'strong' | 'estimate' | 'unknown';
function statusKey(status: string): EvidenceKey {
  return status === 'corroborated' ? 'strong' : status === 'proposed' ? 'estimate' : 'unknown';
}
