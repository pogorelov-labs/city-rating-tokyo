'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { LineInfo, LineType, WardInfo } from '@/lib/types';

const COLLAPSE_THRESHOLD = 6;
const INITIAL_SHOW = 5;

/** Sort priority: subway → JR → private railway; alphabetical within group */
function lineSortKey(line: LineInfo, locale: string): string {
  let groupOrder: string;
  if (line.type === 'subway') {
    groupOrder = '0';
  } else if (line.operator_en.startsWith('JR')) {
    groupOrder = '1';
  } else {
    groupOrder = '2';
  }
  const name = locale === 'ja' ? line.name_ja : line.name_en;
  return `${groupOrder}-${line.operator_en}-${name}`;
}

function formatWard(ward: WardInfo): string {
  const parts: string[] = [];
  if (ward.city_name) parts.push(ward.city_name);
  if (ward.ward_name) parts.push(ward.ward_name);
  return parts.join(' ');
}

interface Props {
  lines: LineInfo[];
  lineCount: number;
  ward: WardInfo | null;
  locale: string;
}

export default function TransportLines({ lines, lineCount, ward, locale }: Props) {
  const t = useTranslations('transport');
  const [expanded, setExpanded] = useState(false);

  if (lines.length === 0 && !ward) return null;

  const sorted = [...lines].sort((a, b) =>
    lineSortKey(a, locale).localeCompare(lineSortKey(b, locale)),
  );

  const needsCollapse = sorted.length >= COLLAPSE_THRESHOLD;
  const visible = needsCollapse && !expanded ? sorted.slice(0, INITIAL_SHOW) : sorted;
  const hiddenCount = sorted.length - INITIAL_SHOW;

  const distinctTypes = [...new Set(sorted.map((l) => l.type))];

  const typeLabel = (type: LineType) => {
    const key = `type${type.charAt(0).toUpperCase()}${type.slice(1)}` as
      | 'typeGeneral'
      | 'typeSubway'
      | 'typeMonorail'
      | 'typeTram'
      | 'typeOther';
    return t(key);
  };

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">{t('title')}</h2>

      {/* Ward / city */}
      {ward && ward.city_name && (
        <div className="flex items-center gap-2 mb-3 text-sm text-gray-600">
          <span className="shrink-0" aria-hidden>
            📍
          </span>
          <span>
            {formatWard(ward)}
            {ward.prefecture_name && ward.prefecture_name !== '東京都' && (
              <span className="text-gray-400 ml-1">{ward.prefecture_name}</span>
            )}
          </span>
        </div>
      )}

      {/* Line list */}
      {sorted.length > 0 && (
        <div className="space-y-1.5">
          {visible.map((line) => (
            <div key={line.id} className="flex items-center gap-2 text-sm">
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: line.color }}
                aria-hidden
              />
              <span className="font-medium">
                {locale === 'ja' ? line.name_ja : line.name_en}
              </span>
              {locale !== 'ja' && (
                <span className="text-gray-400 text-xs">{line.name_ja}</span>
              )}
              <span className="text-gray-400 text-xs ml-auto shrink-0">
                {locale === 'ja' ? line.operator_ja : line.operator_en}
              </span>
            </div>
          ))}

          {/* Expand / collapse */}
          {needsCollapse && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-600 hover:text-blue-800 mt-1 cursor-pointer"
            >
              {expanded
                ? t('showFewer')
                : t('moreLines', { count: hiddenCount })}
            </button>
          )}
        </div>
      )}

      {/* Type legend — only when 2+ distinct types */}
      {distinctTypes.length >= 2 && (
        <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-3 text-xs text-gray-400">
          {distinctTypes.map((type) => {
            const sample = sorted.find((l) => l.type === type);
            return (
              <span key={type} className="flex items-center gap-1">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: sample?.color ?? '#999' }}
                  aria-hidden
                />
                {typeLabel(type)}
              </span>
            );
          })}
        </div>
      )}
    </section>
  );
}
