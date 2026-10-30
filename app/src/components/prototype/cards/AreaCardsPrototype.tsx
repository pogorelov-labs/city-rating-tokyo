'use client';

import dynamic from 'next/dynamic';
import Image from 'next/image';
import Link from 'next/link';
import { Fragment, useState } from 'react';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from '@/lib/types';
import { calculateWeightedScore } from '@/lib/scoring';
import { CATEGORIES, GROUP_NAMES, HUB_NAMES, evidenceLabel, money, peerLabel, sourceLabel, type AreaGroup, type CardArea, type RatingKey } from './model';
import styles from './cards.module.css';

const AreaMap = dynamic(() => import('./AreaMap'), {
  ssr: false,
  loading: () => <div className={styles.mapLoading} role="status">Loading the area map…</div>,
});

const PROFILES = [
  { id: 'balanced', name: 'Balanced', weights: DEFAULT_WEIGHTS },
  ...PRESET_PROFILES.map(p => ({ id: p.id, name: ({ 'young-pro': 'Young professional', family: 'Family', 'foodie-budget': 'Food & budget', 'digital-nomad': 'Digital nomad' })[p.id], weights: p.weights })),
];

function setPreviewUrl(area: string, view: 'detail' | 'compact') {
  const url = new URL(window.location.href);
  url.searchParams.set('area', area);
  if (view === 'compact') url.searchParams.set('view', view);
  else url.searchParams.delete('view');
  window.history.replaceState(null, '', url);
}

function RentDisclosure({ area }: { area: CardArea }) {
  return <details className={styles.disclosure}>
    <summary>Rent sources & definition <span aria-hidden="true">+</span></summary>
    <div className={styles.disclosureBody}>
      <p>{area.rent.detail}</p>
      {area.rent.samples && <p>{area.rent.samples}</p>}
      <ul>{area.rent.limitations.map(text => <li key={text}>{text}</li>)}</ul>
      <p>Rent snapshot: {area.rent.date ?? 'Date unavailable'}.</p>
      <div className={styles.sourceLinks}>{area.rent.sources.map((source, i) => <a key={`${source.href}-${i}`} href={source.href} target={source.href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">{source.label} <span aria-hidden="true">↗</span></a>)}</div>
    </div>
  </details>;
}

function ComparisonPlot({ area, areas }: { area: CardArea; areas: CardArea[] }) {
  const [referenceId, setReferenceId] = useState('median');
  const [expanded, setExpanded] = useState<RatingKey | null>(null);
  const peer = areas.find(a => a.id === referenceId && a.group === area.group && a.id !== area.id);
  const reference = peer?.ratings ?? area.medians;
  const referenceName = peer?.name ?? 'Typical area';
  const referenceInSentence = peer?.name ?? 'the typical area';
  return <section className={styles.comparison} aria-labelledby="comparison-heading">
    <div className={styles.sectionHeader}>
      <div><p className={styles.eyebrow}>THE LOCAL PICTURE</p><h2 id="comparison-heading">How it compares</h2></div>
      <label className={styles.selectLabel}>Compare with
        <select aria-label="Comparison reference" value={peer ? referenceId : 'median'} onChange={e => setReferenceId(e.target.value)}>
          <option value="median">Typical {area.kind === 'district' ? 'district' : 'station area'}</option>
          {areas.filter(a => a.group === area.group && a.id !== area.id).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </label>
    </div>
    <p className={styles.sectionNote}>{peer ? `Comparing two ${peerLabel(area)}.` : `The median of ${area.peerCount.toLocaleString('en-US')} ${peerLabel(area)}.`} Higher scores mean more of the named quality.</p>
    <div className={styles.plotLegend}><span><i className={styles.areaDot} />{area.name}</span><span><i className={styles.referenceDot} />{referenceName}</span></div>
    <table className={styles.comparisonTable}>
      <caption className={styles.srOnly}>Category scores out of ten. Select a category to read its definition and evidence.</caption>
      <thead><tr><th scope="col">Category</th><th scope="col" className={styles.chartHeading}><span>0</span><span>5</span><span>10</span></th><th scope="col">Area</th><th scope="col">{peer ? 'Peer' : 'Typical'}</th></tr></thead>
      <tbody>{CATEGORIES.map(category => {
        const value = area.ratings[category.key];
        const typical = reference[category.key];
        const difference = value - typical;
        const open = expanded === category.key;
        return <Fragment key={category.key}>
          <tr className={open ? styles.openRow : undefined}>
            <th scope="row"><button className={styles.categoryButton} onClick={() => setExpanded(open ? null : category.key)} aria-expanded={open} aria-controls={`evidence-${category.key}`}>{category.label}<span className={styles.categoryPlus} aria-hidden="true">{open ? '−' : '+'}</span></button></th>
            <td><div className={styles.dotPlot} aria-hidden="true">
              <span className={styles.plotTrack} />
              <span className={styles.plotMiddle} />
              <span className={`${styles.plotConnection} ${difference < 0 ? styles.plotBelow : ''}`} style={{ left: `${Math.min(value, typical) * 10}%`, width: `${Math.abs(difference) * 10}%` }} />
              <span className={styles.plotReference} style={{ left: `${typical * 10}%` }} />
              <span className={`${styles.plotArea} ${difference < 0 ? styles.plotAreaBelow : ''}`} style={{ left: `${value * 10}%` }} />
            </div></td>
            <td className={styles.numeric}>{value}</td><td className={styles.referenceNumber}>{typical}</td>
          </tr>
          {open && <tr id={`evidence-${category.key}`} className={styles.evidenceRow}><td colSpan={4}>
            <div><span className={styles.evidenceTag}>{evidenceLabel(area.confidence[category.key])}</span><strong>{difference === 0 ? `Same score as ${referenceInSentence}.` : `${Math.abs(difference)} ${Math.abs(difference) === 1 ? 'point' : 'points'} ${difference > 0 ? 'above' : 'below'} ${referenceInSentence}.`}</strong></div>
            <p>{category.explanation}</p>
            <p className={styles.evidenceSources}>Inputs: {area.sources[category.key]?.map(sourceLabel).join(', ') || 'Source metadata unavailable'} · Score snapshot: {area.dataDate ?? 'Date unavailable'}.</p>
          </td></tr>}
        </Fragment>;
      })}</tbody>
    </table>
    <p className={styles.chartFootnote}>Select a category for its evidence. Comparisons stay within the same city and area type.</p>
  </section>;
}

function CommutePlot({ area, hub, onHub }: { area: CardArea; hub: string; onHub: (hub: string) => void }) {
  const entries = Object.entries(area.commute);
  const maximum = Math.max(60, Math.ceil(Math.max(0, ...entries.map(([, value]) => value)) / 10) * 10);
  return <section className={styles.commuteSection} aria-labelledby="commute-heading">
    <div className={styles.sectionHeader}><div><p className={styles.eyebrow}>YOUR CONNECTIONS</p><h2 id="commute-heading">Getting around</h2></div><span className={styles.modelLabel}>Estimated minutes</span></div>
    <p className={styles.sectionNote}>{area.kind === 'district' ? 'From the median resident’s home, at peak time.' : area.city === 'bangkok' ? 'From the station, at peak time.' : 'Existing estimates to five city hubs.'}</p>
    <div className={styles.commuteAxis} aria-hidden="true"><span>0 min</span><span>{maximum / 2}</span><span>{maximum}</span></div>
    <div className={styles.commuteRows}>
      {entries.map(([key, value]) => <button key={key} className={`${styles.commuteRow} ${hub === key ? styles.selectedCommute : ''}`} onClick={() => onHub(key)} aria-pressed={hub === key}>
        <span className={styles.hubName}>{HUB_NAMES[key] ?? key}</span><span className={styles.commuteTrack} aria-hidden="true"><span style={{ width: `${value / maximum * 100}%` }} /></span><span className={styles.commuteNumber}>{value}<small>min</small></span>
      </button>)}
      {!entries.length && <p className={styles.sectionNote}>Commute estimates are unavailable for this area.</p>}
    </div>
    <p className={styles.chartFootnote}>{area.commuteNote}</p>
    {area.lastTrain && <p className={styles.lastTrain}>Last train reference <strong>{area.lastTrain}</strong><span>Weekday · departure depends on line and direction.</span></p>}
  </section>;
}

function Essentials({ area, hub, onHub, mobile = false }: { area: CardArea; hub: string; onHub: (hub: string) => void; mobile?: boolean }) {
  const destinationId = mobile ? 'mobile-destination' : 'headline-destination';
  return <section className={`${styles.essentials} ${mobile ? styles.mobileEssentials : styles.desktopEssentials}`} aria-label="Rent and connections">
    {area.rent.values.map(value => <div key={value.label} className={styles.essentialStat}><span>{value.label} rent <small>/ month</small></span><strong>{money(area, value.value)}</strong><p className={area.rent.skewed ? styles.rentWarning : undefined}>{area.rent.skewed ? 'Larger / luxury sample · median' : area.rent.label}</p></div>)}
    <div className={styles.essentialStat}><label htmlFor={destinationId}>Commute to<select id={destinationId} aria-label={mobile ? 'Choose commute destination' : 'Commute destination'} value={hub} onChange={e => onHub(e.target.value)}>{Object.keys(area.commute).map(key => <option key={key} value={key}>{HUB_NAMES[key] ?? key}</option>)}</select></label><strong>{area.commute[hub] ?? '—'}<small> min</small></strong><p>{area.kind === 'district' ? 'Median resident · peak model' : area.city === 'bangkok' ? 'From the station · peak model' : 'Existing hub estimate'}</p></div>
    <div className={styles.essentialStat}><span>Rail connections</span><strong>{area.lines.length}<small> {area.lines.length === 1 ? 'service' : 'services'}</small></strong><p>{area.kind === 'district' ? `${area.stationCount} stations in the district` : area.city === 'bangkok' ? `${area.stationCount} ${area.stationCount === 1 ? 'station' : 'stations'} in this interchange` : 'At this station'}</p></div>
  </section>;
}

function CompactCard({ area, score, profileName, hub, onDetails }: { area: CardArea; score: number; profileName: string; hub: string; onDetails: () => void }) {
  return <article className={styles.compactCard} aria-label={`${area.name} map card`}>
    {area.photo && <Image className={styles.compactPhoto} src={area.photo.url} alt={area.photo.alt} width={700} height={240} unoptimized />}
    <div className={styles.compactBody}>
      <p className={styles.eyebrow}>{area.location}</p>
      <div className={styles.compactTitle}><div><h1>{area.name}</h1><span className={styles.localName}>{area.localName}</span></div><div className={styles.compactScore}>{score.toFixed(1)}<small>/10</small></div></div>
      <p className={styles.compactSummary}>{area.summary}</p>
      <div className={styles.compactStats}><div><span>{area.rent.values[0].label} / month</span><strong>{money(area, area.rent.values[0].value)}</strong></div><div><span>To {HUB_NAMES[hub] ?? hub}</span><strong>{area.commute[hub] ?? '—'}<small> min</small></strong></div></div>
      <p className={styles.compactQualifier}>{area.rent.label}{area.rent.skewed ? ' · Larger / luxury sample' : ''}</p>
      <p className={styles.compactQualifier}>{area.kind === 'district' ? 'Commute: median resident · peak model' : area.city === 'bangkok' ? 'Commute: from the station · peak model' : 'Commute: existing hub estimate'}</p>
      <p className={styles.compactScope}>{profileName} weights · Relative to {peerLabel(area)}</p>
      <button className={styles.primaryButton} onClick={onDetails}>Explore this area <span aria-hidden="true">↗</span></button>
      <a className={styles.compactOriginal} href={area.mapHref}>Open full city map <span aria-hidden="true">↗</span></a>
    </div>
    {area.photo && <a className={styles.compactCredit} href={area.photo.href} target="_blank" rel="noreferrer">Photo: {area.photo.credit} · {area.photo.license}</a>}
  </article>;
}

export default function AreaCardsPrototype({ areas, initialArea, initialView }: { areas: CardArea[]; initialArea: string; initialView: 'detail' | 'compact' }) {
  const [areaId, setAreaId] = useState(initialArea);
  const [view, setView] = useState(initialView);
  const [profileId, setProfileId] = useState('balanced');
  const [hubChoice, setHubChoice] = useState<Record<string, string>>({ tokyo: 'shinjuku', bangkok: 'siam' });
  const area = areas.find(a => a.id === areaId) ?? areas[0];
  const profile = PROFILES.find(p => p.id === profileId) ?? PROFILES[0];
  const score = calculateWeightedScore(area.ratings, profile.weights);
  const hub = hubChoice[area.city];
  const chooseArea = (id: string) => { setAreaId(id); setPreviewUrl(id, view); };
  const chooseView = (next: 'detail' | 'compact') => { setView(next); setPreviewUrl(area.id, next); window.scrollTo({ top: 0, behavior: 'instant' }); };
  const chooseHub = (next: string) => setHubChoice(previous => ({ ...previous, [area.city]: next }));
  return <div className={styles.prototype} lang="en">
    <a className={styles.skipLink} href="#area-content">Skip to area guide</a>
    <header className={styles.siteHeader}>
        <Link href="/" className={styles.brand}><Image src="/icon.svg" width={27} height={27} alt="" unoptimized />City Rating<span>Neighborhood guide</span></Link>
      <div className={styles.headerRight}><span className={styles.prototypeBadge}>Prototype</span><a href={area.detailHref}>Current area page <span aria-hidden="true">↗</span></a></div>
    </header>
    <div className={styles.previewToolbar} aria-label="Prototype controls">
      <label className={styles.areaSelectLabel}>Explore an area<select aria-label="Explore an area" value={area.id} onChange={e => chooseArea(e.target.value)}>
        {(Object.keys(GROUP_NAMES) as AreaGroup[]).map(group => <optgroup key={group} label={GROUP_NAMES[group]}>{areas.filter(a => a.group === group).map(a => <option key={a.id} value={a.id}>{a.name} · {a.city === 'tokyo' ? 'Tokyo' : 'Bangkok'}{a.kind === 'district' ? ' district' : ''}</option>)}</optgroup>)}
      </select></label>
      <div className={styles.toolbarActions}>
        <label className={styles.priorityLabel}>Score priorities<select aria-label="Score priorities" value={profileId} onChange={e => setProfileId(e.target.value)}>{PROFILES.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <div className={styles.viewSwitcher} role="group" aria-label="Preview layout"><button aria-pressed={view === 'detail'} onClick={() => chooseView('detail')}>Area guide</button><button aria-pressed={view === 'compact'} onClick={() => chooseView('compact')}>Map card</button></div>
      </div>
    </div>
    <p className={styles.srOnly} aria-live="polite">{area.name}. {profile.name} score {score.toFixed(1)} out of ten. Selected destination {HUB_NAMES[hub]}.</p>
    {view === 'compact' ? <main id="area-content" className={styles.mapWorkspace}>
      <AreaMap key={area.id} area={area} expanded />
      <CompactCard area={area} score={score} profileName={profile.name} hub={hub} onDetails={() => chooseView('detail')} />
    </main> : <main id="area-content" className={styles.main}>
      <section className={styles.hero} aria-labelledby="area-name">
        <div className={styles.heroContent}>
          <p className={styles.eyebrow}>{area.location}</p>
          <div className={styles.titleRow}><div><h1 id="area-name">{area.name}</h1><p className={styles.localName}>{area.localName}</p></div><div className={styles.score}><strong>{score.toFixed(1)}<span>/10</span></strong><span>{profile.name} score</span><span className={styles.scoreScope}>{peerLabel(area)}</span></div></div>
          <p className={styles.summary}>{area.summary}</p>
          <Essentials area={area} hub={hub} onHub={chooseHub} mobile />
          <div className={styles.tradeoffs}><div><h2>What stands out</h2><ul>{area.strengths.map(text => <li key={text}>{text}</li>)}</ul></div><div><h2>Consider</h2><ul>{area.tradeoffs.map(text => <li key={text}>{text}</li>)}</ul></div></div>
        </div>
        <figure className={styles.heroVisual}>
          {area.photo && <><Image className={styles.heroPhoto} src={area.photo.url} alt={area.photo.alt} width={960} height={600} unoptimized preload /><figcaption><a href={area.photo.href} target="_blank" rel="noreferrer">{area.photo.credit} · {area.photo.license} <span aria-hidden="true">↗</span></a></figcaption></>}
          <a className={styles.scopeLink} href="#area-map">{area.map.scope}<span aria-hidden="true">↓</span></a>
        </figure>
      </section>
      <Essentials area={area} hub={hub} onHub={chooseHub} />
      {area.rent.skewed && <p className={styles.materialNote}><strong>Rent sample:</strong> this provider’s inventory skews toward larger or luxury apartments. These medians are not typical fixed-size rents.</p>}
      <div className={styles.rentMeta}><span>Rent snapshot: {area.rent.date ?? 'date unavailable'} · {area.city === 'tokyo' ? 'Different apartment layouts' : area.rent.label.startsWith('Asking') ? 'Mixed floor areas · one provider' : '30–35 m² 1BR / 60–70 m² 2BR'}</span><a href="#data-details">Sources & definitions <span aria-hidden="true">↓</span></a></div>
      <div className={styles.comparisonLayout}>
        <ComparisonPlot key={area.id} area={area} areas={areas} />
        <aside className={styles.localFacts} aria-labelledby="local-facts-heading"><p className={styles.eyebrow}>EVERYDAY LIFE</p><h2 id="local-facts-heading">Around the area</h2><dl>{area.facts.map(fact => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value.toLocaleString('en-US')}<span>{fact.unit}</span></dd></div>)}</dl><p className={styles.chartFootnote}>{area.factsNote}</p><div className={styles.linesList}><h3>Rail services</h3>{area.lines.map(line => <div key={line.name}><i style={{ backgroundColor: line.color ?? '#324b63' }} aria-hidden="true" />{line.name}</div>)}</div><a className={styles.textLink} href={area.mapHref}>Explore on the city map <span aria-hidden="true">↗</span></a></aside>
      </div>
      <div className={styles.connectionsLayout}>
        <CommutePlot area={area} hub={hub} onHub={chooseHub} />
        <section id="area-map" className={styles.areaMapSection} aria-labelledby="map-heading"><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>PUT IT IN CONTEXT</p><h2 id="map-heading">The area on the map</h2></div><a className={styles.textLink} href={area.mapHref}>Full map <span aria-hidden="true">↗</span></a></div><div className={styles.inlineMap}><AreaMap key={area.id} area={area} /></div><p className={styles.chartFootnote}>{area.map.scope}.{area.city === 'tokyo' ? ' This circle is for orientation; the score inputs use different catchments.' : area.kind === 'district' ? ' A district covers many different streets and residential settings.' : ' The outline follows the published nearest-station area, rather than an 800 m circle.'}</p></section>
      </div>
      {area.noise && <section className={styles.conditions} aria-labelledby="conditions-heading"><div><p className={styles.eyebrow}>A CLOSER LOOK</p><h2 id="conditions-heading">Noise & local conditions</h2><p className={styles.sectionNote}>Separate facts that do not change the area’s ranking.</p></div>
        {area.noise ? <div className={styles.noisePanel}><div className={styles.noiseTop}><h3>Outdoor quietness</h3><span className={styles.modelLabel}>Model estimate · higher is quieter</span></div><div className={styles.noiseValues}>{(['day', 'night'] as const).map(period => <div key={period}><span>{period === 'day' ? 'Day · 06–22' : 'Night · 22–06'}</span><strong>{area.noise![period].toFixed(1)}<small>/10</small></strong><div className={styles.noiseTrack} aria-hidden="true"><i style={{ left: `${area.noise![period] * 10}%` }} /></div></div>)}</div><p>Based on road proximity and nightlife. Indoor sound and building insulation are not measured.{area.noise.transferred ? ' Bangkok uses an uncalibrated transfer of the Tokyo model; local accuracy is unknown.' : ' This is separate from the crowding-based ranking above.'} Proxy snapshot: {area.noise.date}.</p></div> : <p className={styles.noiseUnavailable}>{area.kind === 'district' ? 'Outdoor noise estimates are available for station areas, rather than whole districts. Choose a station area to explore them.' : 'An outdoor-noise estimate is unavailable for this station area.'}</p>}
      </section>}
      <section id="data-details" className={styles.dataDetails} aria-label="Sources and assumptions">
        <RentDisclosure area={area} />
        <details className={styles.disclosure}><summary>Score basis & data coverage <span aria-hidden="true">+</span></summary><div className={styles.disclosureBody}><p>The headline uses the existing {profile.name.toLowerCase()} weight profile. Scores are relative within {peerLabel(area)}; other cities and area types use different reference populations.</p><dl className={styles.weightList}>{CATEGORIES.map(category => <div key={category.key}><dt>{category.label}</dt><dd>{profile.weights[category.key]}%</dd></div>)}</dl><p>Category-score snapshot: {area.dataDate ?? 'Date unavailable'}. Rent, noise and other source dates can differ. Data-backed describes the inputs; every displayed category score is derived.</p><a href={area.methodologyHref}>Read the methodology ↗</a></div></details>
        <details className={styles.disclosure}><summary>Environmental context <span aria-hidden="true">+</span></summary><div className={styles.disclosureBody}>{area.context.map(item => <div key={item.title}><h3>{item.title}</h3><p>{item.text}</p></div>)}<h3>Air quality</h3><p>{area.city === 'tokyo' ? 'The available Shinjuku monitor describes one measured location, not the air at this neighborhood.' : 'Publishable current and seasonal air observations are unavailable in this snapshot.'}</p><Link href="/methodology#air">Air sources and coverage ↗</Link></div></details>
      </section>
      <footer className={styles.footer}><span>City Rating <span aria-hidden="true">/</span> {area.name}</span><a href={area.detailHref}>View the current area page <span aria-hidden="true">↗</span></a></footer>
    </main>}
  </div>;
}
