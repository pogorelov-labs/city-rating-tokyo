'use client';

import { EnvironmentData, SeismicRiskTier, ElevationTier } from '@/lib/types';
import Tooltip from './Tooltip';

const SEISMIC_TIER_CONFIG: Record<SeismicRiskTier, { label: string; color: string; description: string }> = {
  low: { label: 'Low', color: '#6A8059', description: 'Below 3% probability' },
  moderate: { label: 'Moderate', color: '#C9A227', description: '3\u201315% probability' },
  high: { label: 'High', color: '#B3574E', description: '15\u201330% probability' },
  very_high: { label: 'Very High', color: '#8C2926', description: 'Above 30% probability' },
  unknown: { label: 'Unknown', color: '#828A8C', description: 'No data available' },
};

const ELEVATION_LABELS: Record<ElevationTier, string> = {
  very_low: 'Very low \u2014 check flood hazard maps',
  low: 'Low-lying area',
  moderate: 'Low to moderate elevation',
  elevated: 'Moderate elevation',
  high: 'Elevated area',
  mountain: 'Hill / mountain area',
  unknown: 'Elevation unknown',
};

interface Props {
  environment: EnvironmentData;
}

export function NaturalEnvironment({ environment }: Props) {
  const { elevation_m, elevation_tier, seismic_prob_i60, seismic_risk_tier } = environment;

  if (elevation_m == null && seismic_prob_i60 == null) return null;

  const tier = seismic_risk_tier ?? 'unknown';
  const seismicConfig = SEISMIC_TIER_CONFIG[tier];
  const elevLabel = ELEVATION_LABELS[elevation_tier ?? 'unknown'];
  const isFloodRisk = elevation_m != null && elevation_m < 5;

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">Natural Environment</h2>
      <div className="space-y-3">
        {/* Elevation */}
        {elevation_m != null && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>
              {isFloodRisk ? '\u26a0\ufe0f' : elevation_m > 100 ? '\u26f0\ufe0f' : '\u{1f4cd}'}
            </span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">Station elevation: {elevation_m}m above sea level</span>
                    <span className="block mt-1">
                      {elevation_m < 0
                        ? 'Below sea level \u2014 this area is in a known flood-prone zone. The Koto/Edogawa lowlands and Arakawa floodplain are at highest risk during typhoons and storm surges.'
                        : elevation_m < 5
                          ? 'Very low elevation \u2014 near or below sea level. These areas are susceptible to flooding during heavy rainfall, typhoons, and storm surges. Check Tokyo/prefecture flood hazard maps.'
                          : elevation_m < 20
                            ? 'Low-lying area. Some flood risk during extreme weather events. Generally manageable with proper preparation.'
                            : 'Moderate to high elevation. Lower flood risk from river/coastal flooding.'}
                    </span>
                    <span className="block mt-1 text-gray-400 text-xs">Source: Open-Elevation API (SRTM data)</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    Elevation: {elevation_m}m
                  </span>
                  <span className="text-xs text-gray-500 ml-1.5">{elevLabel}</span>
                  {isFloodRisk && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                      Flood risk
                    </span>
                  )}
                </div>
              </Tooltip>
            </div>
          </div>
        )}

        {/* Seismic */}
        {seismic_prob_i60 != null && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>
              {tier === 'very_high' ? '\u{1f534}' : tier === 'high' ? '\u{1f7e0}' : '\u{1f30d}'}
            </span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">
                      Seismic risk: {(seismic_prob_i60 * 100).toFixed(1)}% probability of JMA intensity {'\u2265'}6.0 in 30 years
                    </span>
                    <span className="block mt-1">
                      JMA intensity 6.0 means strong shaking where unsecured furniture topples and some buildings are damaged.
                      {tier === 'very_high'
                        ? ' This area has significantly higher risk, often due to soft alluvial soil or reclaimed land that amplifies seismic waves.'
                        : tier === 'high'
                          ? ' This is a relatively high-risk area. Building earthquake resistance and emergency preparedness are important considerations.'
                          : tier === 'moderate'
                            ? ' Moderate risk. Standard earthquake preparedness measures are recommended.'
                            : ' Lower risk area, typically on firmer bedrock. Standard precautions still apply.'}
                    </span>
                    <span className="block mt-1 text-gray-400 text-xs">Source: J-SHIS 2024 (National Research Institute for Earth Science and Disaster Resilience)</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    Seismic Risk:
                  </span>
                  <span className="ml-1.5 inline-flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: seismicConfig.color }}
                      aria-hidden
                    />
                    <span className="text-sm" style={{ color: seismicConfig.color }}>
                      {seismicConfig.label}
                    </span>
                    <span className="text-xs text-gray-500">
                      ({(seismic_prob_i60 * 100).toFixed(1)}%)
                    </span>
                  </span>
                </div>
              </Tooltip>
              <p className="text-[11px] text-gray-500 mt-0.5 ml-0">
                Probability of JMA intensity {'\u2265'}6.0 in 30 years
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-2">
        {(['low', 'moderate', 'high', 'very_high'] as const).map((t) => {
          const cfg = SEISMIC_TIER_CONFIG[t];
          return (
            <span
              key={t}
              className="inline-flex items-center gap-1 text-[10px] text-gray-500"
            >
              <span
                className="h-1.5 w-1.5 rounded-full shrink-0"
                style={{ backgroundColor: cfg.color, opacity: 0.85 }}
                aria-hidden
              />
              {cfg.label} ({cfg.description})
            </span>
          );
        })}
      </div>
    </section>
  );
}
