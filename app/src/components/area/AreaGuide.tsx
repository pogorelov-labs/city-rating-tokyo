'use client';

import dynamic from 'next/dynamic';
import Image from 'next/image';
import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import LocaleSwitcher from '@/components/LocaleSwitcher';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from '@/lib/types';
import { calculateWeightedScore } from '@/lib/scoring';
import { useAppStore } from '@/lib/store';
import { decodeParamsToState } from '@/lib/url-state';
import { guideMapHref } from '@/lib/guide-map-url';
import { dataLabel } from '@/i18n/message-key';
import { GUIDE_CATEGORIES, guideMoney, guideTraits, rentDefinitionKey, withGuideWeights, type AreaGuideData, type RatingKey } from '@/lib/area-guide';
import type { Locale } from '@/i18n/routing';
import styles from './area-guide.module.css';

const LoadedMap = dynamic(() => import('./AreaGuideMap'), { ssr: false });

function queryValue(key: string, value: string | null) {
  const url = new URL(window.location.href);
  if (value == null) url.searchParams.delete(key);
  else url.searchParams.set(key, value);
  window.history.replaceState(null, '', url);
}

function sourceDate(date: string | null, locale: Locale): string | null {
  if (!date) return null;
  const monthOnly = /^\d{4}-\d{2}$/.test(date);
  const parsed = new Date(monthOnly ? `${date}-01T00:00:00Z` : `${date.slice(0, 10)}T00:00:00Z`);
  if (!Number.isFinite(parsed.getTime())) return date;
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'short', ...(monthOnly ? {} : { day: 'numeric' }), timeZone: 'UTC' }).format(parsed);
}

function VisibleMap({ area }: { area: AreaGuideData }) {
  const t = useTranslations('areaGuide');
  const element = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!element.current) return;
    if (typeof IntersectionObserver === 'undefined') {
      queueMicrotask(() => setVisible(true));
      return;
    }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: '160px' });
    observer.observe(element.current);
    return () => observer.disconnect();
  }, []);
  return <div ref={element} className={styles.inlineMap}>
    {visible ? <LoadedMap area={area} /> : <div className={styles.mapLoading} role="status">{t('map.loading')}</div>}
  </div>;
}

function Essentials({ area, hub, onHub, mobile = false }: {
  area: AreaGuideData; hub: string; onHub: (value: string) => void; mobile?: boolean;
}) {
  const t = useTranslations('areaGuide');
  const locale = useLocale() as Locale;
  const all = useTranslations();
  const destinationId = mobile ? 'mobile-destination' : 'headline-destination';
  const origin = area.city === 'tokyo' ? 'tokyo' : area.kind;
  return (
    <section className={`${styles.essentials} ${mobile ? styles.mobileEssentials : styles.desktopEssentials}`} aria-label={t('rent.title')}>
      {area.rent.values.map(value => (
        <div key={value.layout} className={styles.essentialStat}>
          <span>{t(`rent.${value.layout}`)} <small>{t('rent.perMonth')}</small></span>
          <strong>{guideMoney(area.city, value.value, locale) ?? t('unavailable')}</strong>
          <p className={area.rent.skewed ? styles.rentWarning : undefined}>
            {t(area.rent.skewed ? 'rent.skewShort' : `rent.provenance.${area.rent.provenance}`)}
          </p>
        </div>
      ))}
      <div className={styles.essentialStat}>
        <label htmlFor={destinationId}>{t('commute.to')}
          <select id={destinationId} aria-label={t(mobile ? 'commute.mobileDestination' : 'commute.destination')}
            value={hub} onChange={event => onHub(event.target.value)} disabled={!Object.keys(area.commute).length}>
            {Object.keys(area.commute).map(key => <option key={key} value={key}>{dataLabel(all, 'hubs', key)}</option>)}
          </select>
        </label>
        <strong>{area.commute[hub] ?? '—'}<small> {t('units.min')}</small></strong>
        <p>{t(`commute.origin.${origin}`)}</p>
      </div>
      <div className={styles.essentialStat}>
        <span>{t('rail.title')}</span>
        <strong>{t('rail.services', { count: area.lines.length })}</strong>
        <p>{area.kind === 'district'
          ? t(area.stationCount ? 'rail.districtStations' : 'rail.none', { count: area.stationCount })
          : area.city === 'bangkok' ? t('rail.stations', { count: area.stationCount }) : t('rail.atStation')}</p>
      </div>
    </section>
  );
}

function ComparisonPlot({ area }: { area: AreaGuideData }) {
  const t = useTranslations('areaGuide');
  const all = useTranslations();
  const nf = useMemo(() => new Intl.NumberFormat(area.locale, { maximumFractionDigits: 1 }), [area.locale]);
  const [referenceKey, setReferenceKey] = useState('median');
  const [expanded, setExpanded] = useState<RatingKey | null>(null);
  useEffect(() => {
    const path = window.location.pathname;
    const restore = () => {
      if (window.location.pathname !== path) return;
      const reference = new URLSearchParams(window.location.search).get('reference');
      setReferenceKey(reference && area.peers.some(peer => peer.key === reference) ? reference : 'median');
    };
    queueMicrotask(restore);
    window.addEventListener('popstate', restore);
    return () => window.removeEventListener('popstate', restore);
  }, [area.peers]);
  const peer = area.peers.find(item => item.key === referenceKey);
  const reference = peer?.ratings ?? area.medians;
  if (!area.ratings) return <p className={styles.ratingsUnavailable}>{t('score.empty')}</p>;
  return (
    <section className={styles.comparison} aria-labelledby="comparison-heading">
      <div className={styles.sectionHeader}>
        <div><p className={styles.eyebrow}>{t('comparison.eyebrow')}</p><h2 id="comparison-heading">{t('comparison.title')}</h2></div>
        <label className={styles.selectLabel}>{t('comparison.reference')}
          <select aria-label={t('comparison.reference')} value={peer ? referenceKey : 'median'} onChange={event => {
            setReferenceKey(event.target.value);
            queryValue('reference', event.target.value === 'median' ? null : event.target.value);
          }}>
            <option value="median">{t(area.kind === 'district' ? 'comparison.typicalDistrict' : 'comparison.typicalStation')}</option>
            {area.peers.map(item => <option key={item.key} value={item.key}>{item.name}</option>)}
          </select>
        </label>
      </div>
      <p className={styles.sectionNote}>
        {peer ? t('comparison.peer') : t(`comparison.population.${area.kind}`, { count: area.peerCount, city: t(`cities.${area.city}`) })} {t('comparison.higher')}
      </p>
      <div className={styles.plotLegend}>
        <span><i className={styles.areaDot} /><i className={`${styles.areaDot} ${styles.belowLegend}`} />{area.name}</span>
        <span><i className={styles.referenceDot} />{peer?.name ?? t('comparison.typical')}</span>
      </div>
      <table className={styles.comparisonTable}>
        <caption className={styles.srOnly}>{t('comparison.caption')}</caption>
        <thead><tr>
          <th scope="col">{t('comparison.category')}</th>
          <th scope="col" className={styles.chartHeading}><span>0</span><span>5</span><span>10</span></th>
          <th scope="col">{t('comparison.area')}</th>
          <th scope="col">{t(peer ? 'comparison.peerShort' : 'comparison.typicalShort')}</th>
        </tr></thead>
        <tbody>{GUIDE_CATEGORIES.map(key => {
          const value = area.ratings![key];
          const typical = reference[key];
          const difference = value - typical;
          const open = expanded === key;
          return <Fragment key={key}>
            <tr className={open ? styles.openRow : undefined}>
              <th scope="row"><button className={styles.categoryButton} onClick={() => setExpanded(open ? null : key)}
                aria-expanded={open} aria-controls={open ? `evidence-${key}` : undefined}>
                {t(`categories.${key}`)}<span className={styles.categoryPlus} aria-hidden="true">{open ? '−' : '+'}</span>
              </button></th>
              <td><div className={styles.dotPlot} aria-hidden="true">
                <span className={styles.plotTrack} /><span className={styles.plotMiddle} />
                <span className={`${styles.plotConnection} ${difference < 0 ? styles.plotBelow : ''}`}
                  style={{ left: `${Math.min(value, typical) * 10}%`, width: `${Math.abs(difference) * 10}%` }} />
                <span className={styles.plotReference} style={{ left: `${typical * 10}%` }} />
                <span className={`${styles.plotArea} ${difference < 0 ? styles.plotAreaBelow : ''}`} style={{ left: `${value * 10}%` }} />
              </div></td>
              <td className={styles.numeric}>{nf.format(value)}</td><td className={styles.referenceNumber}>{nf.format(typical)}</td>
            </tr>
            {open && <tr id={`evidence-${key}`} className={styles.evidenceRow}><td colSpan={4}>
              <div><span className={styles.evidenceTag}>{t(`evidence.${area.confidence[key] ?? 'unknown'}`)}</span>
                <strong>{t('comparison.difference', { difference: `${difference > 0 ? '+' : ''}${nf.format(difference)}` })}</strong></div>
              <p>{t(`explanations.${key}`)}</p>
              <p className={styles.evidenceSources}>{t('comparison.inputs', {
                sources: area.sources[key]?.map(source => dataLabel(all, 'sources', source)).join(', ') || t('evidence.unknown'),
              })} · {t('snapshot', { date: sourceDate(area.date, area.locale) ?? t('unknownDate') })}</p>
            </td></tr>}
          </Fragment>;
        })}</tbody>
      </table>
      <p className={styles.chartFootnote}>{t('comparison.note')}</p>
    </section>
  );
}

function CommutePlot({ area, hub, onHub }: { area: AreaGuideData; hub: string; onHub: (value: string) => void }) {
  const t = useTranslations('areaGuide');
  const all = useTranslations();
  const entries = Object.entries(area.commute);
  const maximum = Math.max(60, Math.ceil(Math.max(0, ...entries.map(([, value]) => value)) / 10) * 10);
  const origin = area.city === 'tokyo' ? 'tokyo' : area.kind;
  return (
    <section className={styles.commuteSection} aria-labelledby="commute-heading">
      <div className={styles.sectionHeader}>
        <div><p className={styles.eyebrow}>{t('commute.eyebrow')}</p><h2 id="commute-heading">{t('commute.title')}</h2></div>
        <span className={styles.modelLabel}>{t('commute.estimated')}</span>
      </div>
      <p className={styles.sectionNote}>{t(`commute.origin.${origin}`)}</p>
      <div className={styles.commuteAxis} aria-hidden="true"><span>0 {t('units.min')}</span><span>{maximum / 2}</span><span>{maximum}</span></div>
      <div className={styles.commuteRows}>
        {entries.map(([key, value]) => (
          <button key={key} className={`${styles.commuteRow} ${hub === key ? styles.selectedCommute : ''}`} onClick={() => onHub(key)} aria-pressed={hub === key}>
            <span className={styles.hubName}>{dataLabel(all, 'hubs', key)}</span>
            <span className={styles.commuteTrack} aria-hidden="true"><span style={{ width: `${value / maximum * 100}%` }} /></span>
            <span className={styles.commuteNumber}>{value}<small>{t('units.min')}</small></span>
          </button>
        ))}
        {!entries.length && <p className={styles.sectionNote}>{t('commute.empty')}</p>}
      </div>
      <p className={styles.chartFootnote}>{t(`commute.note.${origin}`)}</p>
      {area.lastTrain && <p className={styles.lastTrain}>{t('commute.lastTrain')} <strong>{area.lastTrain}</strong><span>{t('commute.lastTrainNote')}</span></p>}
    </section>
  );
}

export default function AreaGuide({ area, children }: { area: AreaGuideData; children?: ReactNode }) {
  const t = useTranslations('areaGuide');
  const all = useTranslations();
  const weights = useAppStore(state => state.weights);
  const setAllWeights = useAppStore(state => state.setAllWeights);
  // Subscribe to the map slice and shared overlays so navigation follows changes.
  const mapState = useAppStore(state => state.cities[area.city]);
  const heatmapMode = useAppStore(state => state.heatmapMode);
  const heatmapDimension = useAppStore(state => state.heatmapDimension);
  const [hydrated, setHydrated] = useState(false);
  const [hub, setHub] = useState(area.city === 'tokyo' ? 'shinjuku' : 'siam');
  const [photoFailed, setPhotoFailed] = useState(false);
  const rentDetails = useRef<HTMLDetailsElement>(null);
  const guidePath = useRef<string | null>(null);
  const defaultProfile = GUIDE_CATEGORIES.every(key => weights[key] === DEFAULT_WEIGHTS[key]);
  const matchedProfile = PRESET_PROFILES.find(profile => GUIDE_CATEGORIES.every(key => profile.weights[key] === weights[key]));
  const profileId = defaultProfile ? 'balanced' : matchedProfile?.id ?? 'custom';
  const profileName = matchedProfile ? all(`presets.${matchedProfile.id}`) : t(defaultProfile ? 'score.balanced' : 'score.custom');
  const score = area.ratings ? calculateWeightedScore(area.ratings, weights) : null;
  const traits = guideTraits(area.ratings, area.medians);
  const nf = useMemo(() => new Intl.NumberFormat(area.locale, { maximumFractionDigits: 1 }), [area.locale]);
  const origin = area.city === 'tokyo' ? 'tokyo' : area.kind;
  const visibleHub = Object.hasOwn(area.commute, hub) ? hub : Object.keys(area.commute)[0] ?? '';

  useEffect(() => {
    let active = true;
    const path = window.location.pathname;
    guidePath.current = path;
    const restore = () => {
      if (!active || window.location.pathname !== path) return;
      const params = new URLSearchParams(window.location.search);
      const incoming = decodeParamsToState(params, area.city).weights;
      const valid = incoming && GUIDE_CATEGORIES.every(key => Number.isFinite(incoming[key]) && incoming[key] >= 0 && incoming[key] <= 100);
      setAllWeights(valid ? incoming : DEFAULT_WEIGHTS);
      const destination = params.get('hub');
      setHub(destination && Object.hasOwn(area.commute, destination) ? destination : area.city === 'tokyo' ? 'shinjuku' : 'siam');
      setHydrated(true);
    };
    queueMicrotask(restore);
    window.addEventListener('popstate', restore);
    return () => { active = false; window.removeEventListener('popstate', restore); };
  }, [area.city, area.commute, setAllWeights]);

  useEffect(() => {
    // A queued render from the previous history entry must never overwrite the
    // destination's URL before its state has been restored.
    if (!hydrated || window.location.pathname !== guidePath.current || weights !== useAppStore.getState().weights) return;
    const href = window.location.pathname + window.location.search + window.location.hash;
    window.history.replaceState(null, '', withGuideWeights(href, weights));
  }, [hydrated, weights]);

  const chooseHub = (value: string) => { setHub(value); queryValue('hub', value); };
  const chooseProfile = (id: string) => {
    if (id === 'balanced') setAllWeights(DEFAULT_WEIGHTS);
    else {
      const profile = PRESET_PROFILES.find(item => item.id === id);
      if (profile) setAllWeights(profile.weights);
    }
  };
  const mapHref = guideMapHref(area.mapHref, area.city, {
    ...mapState, weights, heatmapMode, heatmapDimension,
  });
  const scope = t(`map.scope.${origin}`);
  const photo = area.photo && !photoFailed ? area.photo : null;
  const factNote = area.city === 'tokyo' ? t('facts.tokyoNote') : t(`facts.${area.kind}Note`, { area: nf.format(area.areaKm2 ?? 0) });
  return (
    <div className={styles.guide} lang={area.locale}>
      <a className={styles.skipLink} href="#area-content">{t('skip')}</a>
      <header className={styles.siteHeader}>
        <Link href={mapHref} className={styles.brand}><Image src="/icon.svg" width={27} height={27} alt="" unoptimized />City Rating<span>{t('guide')}</span></Link>
        <div className={styles.headerRight}><LocaleSwitcher /></div>
      </header>
      <div className={styles.guideControls}>
        <Link href={mapHref} data-umami-event="back-to-map">← {t('back')}</Link>
        <label>{t('score.priorities')}<select aria-label={t('score.priorities')} value={profileId} onChange={event => chooseProfile(event.target.value)}>
          <option value="balanced">{t('score.balanced')}</option>
          {PRESET_PROFILES.map(profile => <option key={profile.id} value={profile.id}>{all(`presets.${profile.id}`)}</option>)}
          {profileId === 'custom' && <option value="custom">{t('score.custom')}</option>}
        </select></label>
      </div>
      <main id="area-content" className={styles.main}>
        <section className={`${styles.hero} ${photo ? '' : styles.noPhoto}`} aria-labelledby="area-name">
          <div className={styles.heroContent}>
            <p className={styles.eyebrow}>{t(`cities.${area.city}`)} · {t(`kinds.${area.kind}`)}</p>
            <div className={styles.titleRow}>
              <div><h1 id="area-name">{area.name}</h1><p className={styles.localName}>{area.localName}</p></div>
              <div className={styles.score} aria-live="polite">
                <strong>{score == null ? '—' : nf.format(score)}<span>/10</span></strong>
                <span>{score == null ? t('score.empty') : t('score.label', { profile: profileName })}</span>
                <span className={styles.scoreScope}>{t(`cities.${area.city}`)} · {t(`kindsPlural.${area.kind}`)}</span>
              </div>
            </div>
            <p className={styles.summary}>{area.summary}</p>
            <Essentials area={area} hub={visibleHub} onHub={chooseHub} mobile />
            {(traits.strengths.length > 0 || traits.tradeoffs.length > 0) && <div className={styles.tradeoffs}>
              {traits.strengths.length > 0 && <div><h2>{t('strengths')}</h2><ul>{traits.strengths.map(key => <li key={key}>{t(`positive.${key}`)}</li>)}</ul></div>}
              {traits.tradeoffs.length > 0 && <div><h2>{t('consider')}</h2><ul>{traits.tradeoffs.map(key => <li key={key}>{t(`negative.${key}`)}</li>)}</ul></div>}
            </div>}
          </div>
          {photo && <figure className={styles.heroVisual}>
            <Image className={styles.heroPhoto} src={photo.url} alt={t('photoAlt', { name: area.name })} width={960} height={600} unoptimized fetchPriority="high" loading="eager" onError={() => setPhotoFailed(true)} />
            <figcaption><a href={photo.href} target="_blank" rel="noopener noreferrer">{photo.credit} · {photo.license} ↗</a></figcaption>
            <a className={styles.scopeLink} href="#area-map">{scope}<span aria-hidden="true">↓</span></a>
          </figure>}
        </section>
        <Essentials area={area} hub={visibleHub} onHub={chooseHub} />
        {area.rent.skewed && <p className={styles.materialNote}>{t('rent.skew')}</p>}
        <div className={styles.rentMeta}>
          <span>{t('snapshot', { date: sourceDate(area.rent.date, area.locale) ?? t('unknownDate') })} · {t(area.city === 'tokyo' ? 'rent.referenceUnit' : area.rent.provenance === 'bedroomMedian' ? 'rent.mixedSizes' : 'rent.fixedSizes')}</span>
          <a href="#data-details" onClick={() => { if (rentDetails.current) rentDetails.current.open = true; }}>{t('rent.sources')} ↓</a>
        </div>
        <div className={styles.comparisonLayout}>
          <ComparisonPlot area={area} />
          <aside className={styles.localFacts} aria-labelledby="local-facts-heading">
            <p className={styles.eyebrow}>{t('facts.eyebrow')}</p><h2 id="local-facts-heading">{t('facts.title')}</h2>
            <dl>{area.facts.slice(0, 4).map(fact => <div key={fact.key}><dt>{t(`facts.${fact.key}`)}</dt><dd>{nf.format(fact.value)}<span>{fact.unit ? t(`units.${fact.unit}`) : ''}</span></dd></div>)}</dl>
            <p className={styles.chartFootnote}>{factNote}</p>
            <div className={styles.linesList}><h3>{t('rail.title')}</h3>{area.lines.length
              ? area.lines.map(line => <div key={line.name}><i style={{ backgroundColor: line.color }} aria-hidden="true" />{line.name}</div>)
              : <p>{t('rail.none')}</p>}</div>
            <Link className={styles.textLink} href={mapHref}>{t('map.full')} ↗</Link>
          </aside>
        </div>
        <div className={styles.connectionsLayout}>
          <CommutePlot area={area} hub={visibleHub} onHub={chooseHub} />
          <section id="area-map" className={styles.areaMapSection} aria-labelledby="map-heading">
            <div className={styles.sectionHeader}><div><p className={styles.eyebrow}>{t('map.eyebrow')}</p><h2 id="map-heading">{t('map.title')}</h2></div>
              <Link className={styles.textLink} href={mapHref}>{t('map.full')} ↗</Link></div>
            <VisibleMap area={area} />
            <p className={styles.chartFootnote}>{scope}. {area.city === 'tokyo' ? t('facts.tokyoNote') : factNote}</p>
          </section>
        </div>
        {area.noise && <section className={styles.conditions} aria-labelledby="conditions-heading">
          <div><p className={styles.eyebrow}>{t('noise.eyebrow')}</p><h2 id="conditions-heading">{t('noise.title')}</h2><p className={styles.sectionNote}>{t('noise.intro')}</p></div>
          <div className={styles.noisePanel}>
            <div className={styles.noiseTop}><h3>{t('noise.outdoor')}</h3><span className={styles.modelLabel}>{t('noise.model')}</span></div>
            <div className={styles.noiseValues}>{(['day', 'night'] as const).map(period => <div key={period}>
              <span>{t(`noise.${period}`)}</span><strong>{nf.format(area.noise![period])}<small>/10</small></strong>
              <div className={styles.noiseTrack} aria-hidden="true"><i style={{ left: `${area.noise![period] * 10}%` }} /></div>
            </div>)}</div>
            <p>{t('noise.limits')} {area.noise.transferred ? t('noise.transfer') : ''} {t('noise.snapshot', { date: sourceDate(area.noise.date, area.locale) ?? t('unknownDate') })}</p>
          </div>
        </section>}
        <section id="data-details" className={styles.dataDetails} aria-label={t('rent.sources')}>
          <details ref={rentDetails} className={styles.disclosure}><summary>{t('rent.sources')}<span aria-hidden="true">+</span></summary>
            <div className={styles.disclosureBody}>
              <p>{t(rentDefinitionKey(area.city, area.rent.provenance))}</p>
              {area.rent.samples && <p>{t('rent.samples', area.rent.samples)}</p>}
              {area.rent.skewed && <p className={styles.materialNote}>{t('rent.skew')}</p>}
              <p>{t('rent.notLease')}</p><p>{t('snapshot', { date: sourceDate(area.rent.date, area.locale) ?? t('unknownDate') })}</p>
              <div className={styles.sourceLinks}>{area.rent.sources.map((source, index) => source.href.startsWith('http')
                ? <a key={`${source.href}-${index}`} href={source.href} target="_blank" rel="noopener noreferrer">{source.label} ↗</a>
                : <Link key={`${source.href}-${index}`} href={source.href}>{source.label} ↗</Link>)}</div>
            </div>
          </details>
          <details className={styles.disclosure}><summary>{t('score.basis')}<span aria-hidden="true">+</span></summary>
            <div className={styles.disclosureBody}><p>{t('score.explain')}</p>
              <dl className={styles.weightList}>{GUIDE_CATEGORIES.map(key => <div key={key}><dt>{t(`categories.${key}`)}</dt><dd>{nf.format(weights[key])}%</dd></div>)}</dl>
              <p>{t('score.snapshot', { date: sourceDate(area.date, area.locale) ?? t('unknownDate') })}</p><p>{t('score.derived')}</p>
              <Link href={area.methodologyHref}>{t('methodology')} ↗</Link>
            </div>
          </details>
        </section>
        {area.peers.length > 0 && <section className={styles.relatedSection}><h2>{t('extras.neighbors')}</h2>
          <div className={styles.related}>{area.peers.map(peer => <Link key={peer.key} href={withGuideWeights(peer.href, weights)}>{peer.name} ↗</Link>)}</div>
        </section>}
        {children}
        <footer className={styles.footer}><span>City Rating / {area.name}</span>
          <a href={area.mapsHref} target="_blank" rel="noopener noreferrer">{all('station.mapsLink')} ↗</a></footer>
      </main>
    </div>
  );
}
