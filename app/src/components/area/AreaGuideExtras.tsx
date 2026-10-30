import type { ReactNode } from 'react';
import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { getStation } from '@/lib/data';
import { getBangkokDistrict, getBangkokStationArea } from '@/lib/bangkok-data';
import { stationDisplayName } from '@/lib/station-name';
import { getInstitutions } from '@/lib/institutions';
import { getQuietness } from '@/lib/quietness';
import { InstitutionFacts } from '@/components/InstitutionFacts';
import { QuietnessFacts } from '@/components/QuietnessFacts';
import { NaturalEnvironment } from '@/components/NaturalEnvironment';
import AirPanel from '@/components/AirPanel';
import NearbyPlaces from '@/components/NearbyPlaces';
import FeedbackWidget from '@/components/FeedbackWidget';
import ImageGallery from '@/components/ImageGallery';
import LiveCameras from '@/components/LiveCameras';
import TransportLines from '@/components/TransportLines';
import { dataLabel } from '@/i18n/message-key';
import type { AreaGuideData } from '@/lib/area-guide';
import type { StationPlace } from '@/lib/types';
import imagesData from '@/data/station-images-all.json';
import placesData from '@/data/station-places.json';
import AreaLink from './AreaLink';
import styles from './area-guide.module.css';

type Photo = { url: string; alt: string; attribution?: string; photographer?: string; photographer_url?: string; source?: string; license?: string; lqip?: string };

function Disclosure({ label, children }: { label: string; children: ReactNode }) {
  return <details className={styles.disclosure}>
    <summary>{label}<span aria-hidden="true">+</span></summary>
    <div className={styles.disclosureBody}>{children}</div>
  </details>;
}

export default async function AreaGuideExtras({ area }: { area: AreaGuideData }) {
  const t = await getTranslations({ locale: area.locale });
  const station = area.city === 'tokyo' ? getStation(area.slug) : undefined;
  const district = area.city === 'bangkok' && area.kind === 'district' ? getBangkokDistrict(area.slug) : undefined;
  const stationArea = area.city === 'bangkok' && area.kind === 'station' ? getBangkokStationArea(area.slug) : undefined;
  const description = (station?.description ?? district?.description)?.[area.locale];
  const images = station ? ((imagesData as Record<string, Photo[]>)[area.slug] ?? []) : [];
  const places = station ? ((placesData as Record<string, StationPlace[]>)[area.slug] ?? []) : [];
  const institutions = getInstitutions(area.city, area.kind, area.slug);
  const quietness = area.kind === 'station' ? getQuietness(area.city, area.slug) : undefined;
  const wikipedia = district?.wikipedia ?? stationArea?.wikipedia;
  const nf = new Intl.NumberFormat(area.locale, { maximumFractionDigits: 1 });
  return <>
    <section className={styles.supplemental} aria-label={t('areaGuide.extras.notes')}>
      <Disclosure label={t('areaGuide.extras.transport')}>
        {station && <TransportLines lines={station.lines} ward={station.ward ?? null} locale={area.locale} />}
        {station?.last_train && <>
          <h3>{t('station.lastTrain')}</h3>
          <dl className={styles.weightList}>
            {station.last_train.weekday && <div><dt>{t('station.weekdayFull')}</dt><dd>{station.last_train.weekday}</dd></div>}
            {station.last_train.holiday && <div><dt>{t('station.holidayFull')}</dt><dd>{station.last_train.holiday}</dd></div>}
          </dl>
          <p>{t('station.lastTrainCaveat')}</p>
          {station.last_train.data_date && <p>{t('areaGuide.snapshot', { date: station.last_train.data_date })}</p>}
        </>}
        {area.city === 'bangkok' && <>
          <div className={styles.linesList}>{area.lines.map(line => <div key={line.name}><i style={{ backgroundColor: line.color }} aria-hidden="true" />{line.name}</div>)}</div>
          <dl className={styles.allFacts}>{area.map.stations.map(member => <div key={member.id}>
            <dt>{t(member.selected ? 'areaGuide.map.stationSelected' : 'areaGuide.map.stationNearby')}</dt><dd>{member.name}</dd>
          </div>)}</dl>
          {stationArea && <>
            <h3>{t('bangkok.station.residentLabel')}</h3><p>{t('areaGuide.commute.origin.district')}</p>
            <dl className={styles.weightList}>{Object.entries(stationArea.resident_minutes).map(([hub, minutes]) => <div key={hub}>
              <dt>{dataLabel(t, 'hubs', hub)}</dt><dd>{nf.format(minutes)} {t('areaGuide.units.min')}</dd>
            </div>)}</dl>
          </>}
        </>}
      </Disclosure>
      {(description || places.length > 0) && <Disclosure label={t('areaGuide.extras.notes')}>
        {description && <div className={styles.localNotes}>
          {([
            ['atmosphere', 'atmosphere'], ['landmarks', 'landmarks'], ['food', 'foodAndCafes'], ['nightlife', 'barsAndNightlife'],
          ] as const).map(([field, label]) => description[field] ? <div key={field}>
            <h3>{t(`station.${label}`)}</h3><p>{description[field]}</p>
          </div> : null)}
        </div>}
        {station && <NearbyPlaces places={places} lat={station.lat} lng={station.lng} stationName={area.name} />}
      </Disclosure>}
      {area.city === 'bangkok' && <Disclosure label={t('areaGuide.extras.allFacts')}>
        <dl className={styles.allFacts}>{area.facts.map(fact => <div key={fact.key}>
          <dt>{t(`areaGuide.facts.${fact.key}`)}</dt><dd>{nf.format(fact.value)} {fact.unit ? t(`areaGuide.units.${fact.unit}`) : ''}</dd>
        </div>)}
          {district?.facts.population != null && <div><dt>{t('areaGuide.facts.population')} ({district.facts.population_year})</dt><dd>{nf.format(district.facts.population)}</dd></div>}
          {district?.facts.density != null && <div><dt>{t('bangkok.district.density')}</dt><dd>{nf.format(district.facts.density)} / {t('areaGuide.units.km2')}</dd></div>}
          {district && <div><dt>{t('bangkok.district.factParks')} (%)</dt><dd>{nf.format(district.facts.park_share)}%</dd></div>}
        </dl>
        <p>{t('areaGuide.facts.attribution')}</p>
        {district?.facts.population != null && <p>{t('areaGuide.extras.populationNote')}</p>}
        {stationArea && (stationArea.hotels_800m != null || stationArea.attractions_800m != null) && <>
          <dl className={styles.allFacts}>
            {stationArea.hotels_800m != null && <div><dt>{t('areaGuide.facts.hotels')}</dt><dd>{nf.format(stationArea.hotels_800m)}</dd></div>}
            {stationArea.attractions_800m != null && <div><dt>{t('areaGuide.facts.attractions')}</dt><dd>{nf.format(stationArea.attractions_800m)}</dd></div>}
          </dl><p>{t('areaGuide.facts.nearbyScope')}</p>
        </>}
      </Disclosure>}
      {stationArea && <Disclosure label={t('areaGuide.extras.districts')}>
        <div className={styles.related}>{stationArea.districts.map(item => {
          const parent = getBangkokDistrict(item.slug);
          return parent ? <AreaLink key={item.slug} href={`/bangkok/district/${item.slug}`}>
            {stationDisplayName(parent, area.locale).primary}<span>{nf.format(item.share * 100)}%</span>
          </AreaLink> : null;
        })}</div>
        <p>{t('bangkok.station.districtsCaption')}</p>
        <AreaLink href={`/bangkok?lv=grid&s=${encodeURIComponent(area.key)}`}>{t('bangkok.station.viewGrid')}</AreaLink>
      </Disclosure>}
      {institutions && <Disclosure label={t('areaGuide.extras.institutions')}><InstitutionFacts fact={institutions} /></Disclosure>}
      {quietness && <Disclosure label={t('areaGuide.extras.noise')}><QuietnessFacts fact={quietness} /></Disclosure>}
      {(station?.environment || district?.flood) && <Disclosure label={t('areaGuide.extras.environment')}>
        {station?.environment && <NaturalEnvironment environment={station.environment} />}
        {district?.flood && <><p>{t('areaGuide.extras.flood', { count: district.flood.episodes_total })}</p><Link href={area.methodologyHref}>{t('areaGuide.methodology')} ↗</Link></>}
      </Disclosure>}
      <Disclosure label={t('areaGuide.extras.air')}><AirPanel city={area.city} /></Disclosure>
      {(images.length > 0 || station?.livecams?.length) ? <Disclosure label={t('areaGuide.extras.photos')}>
        {images.length > 0 && <ImageGallery images={images} stationName={area.name} />}
        {!!station?.livecams?.length && <LiveCameras livecams={station.livecams} locale={area.locale} />}
      </Disclosure> : null}
      {wikipedia && <Disclosure label={t('areaGuide.extras.wikipedia')}><div className={styles.sourceLinks}>
        {Object.entries(wikipedia).map(([language, href]) => href ? <a key={language} href={href} target="_blank" rel="noopener noreferrer">Wikipedia ({language.toUpperCase()}) ↗</a> : null)}
      </div></Disclosure>}
    </section>
    <div className={styles.feedback}><FeedbackWidget stationSlug={area.key} stationName={area.name} source="station_page" /></div>
  </>;
}
