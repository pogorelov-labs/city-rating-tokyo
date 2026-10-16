"""Complete HP pagination, then 800m filtering; internal read-only shadow data."""
from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .bounded import AcquisitionStopped, RequestRejected
from .stage0 import distance, point


class BadCoordinates(ValueError):
    def __init__(self, reason='unknown_800m_membership', safe_diagnostic=None):
        super().__init__(reason)
        self.reason = reason
        self.safe_diagnostic = {**(safe_diagnostic or {}), 'parser_reason': reason}


class HPApiError(ValueError):
    def __init__(self, reason, safe_diagnostic=None):
        super().__init__(reason)
        self.reason = reason
        self.safe_diagnostic = {**(safe_diagnostic or {}), 'parser_reason': reason}


class PaginationChanged(ValueError):
    def __init__(self, reason, safe_diagnostic=None):
        super().__init__(reason)
        self.reason = reason
        self.safe_diagnostic = {**(safe_diagnostic or {}), 'parser_reason': reason}


PAGINATION_FIELDS = ('results_available', 'results_start', 'results_returned')
PROVIDER_ERROR_CODES = frozenset({'1000', '2000', '3000'})


def _value_type(value):
    if value is None: return 'null'
    if isinstance(value, bool): return 'boolean'
    if isinstance(value, int): return 'integer'
    if isinstance(value, float): return 'number'
    if isinstance(value, str): return 'string'
    if isinstance(value, list): return 'array'
    if isinstance(value, dict): return 'object'
    return 'other'


def _safe_count(value):
    if isinstance(value, bool): return None
    if isinstance(value, int):
        return value if 0 <= value <= 1_000_000 else None
    if isinstance(value, str) and len(value) <= 7 and value.isascii() and value.isdecimal():
        number = int(value)
        return number if str(number) == value and number <= 1_000_000 else None
    return None


def _provider_error_codes(error):
    entries = error[:8] if isinstance(error, list) else [error]
    codes = set()
    for entry in entries:
        raw = entry.get('code') if isinstance(entry, dict) else None
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            code = str(raw)
        elif isinstance(raw, str) and len(raw) == 4 and raw.isascii() and raw.isdecimal():
            code = raw
        else:
            continue
        if code in PROVIDER_ERROR_CODES:
            codes.add(code)
    return sorted(codes)


def _page_diagnostic(status, data=None, *, body_bytes=None, payload_type=None):
    diagnostic = {}
    if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599:
        diagnostic['http_status'] = status
    if payload_type is not None:
        diagnostic['payload_type'] = payload_type
    if isinstance(body_bytes, int) and 0 <= body_bytes <= 1_048_576:
        diagnostic['body_bytes'] = body_bytes
    if isinstance(data, dict):
        diagnostic['pagination_types'] = {field: _value_type(data.get(field)) for field in PAGINATION_FIELDS}
        counts = {field: count for field in PAGINATION_FIELDS
                  if (count := _safe_count(data.get(field))) is not None}
        if counts:
            diagnostic['pagination_counts'] = counts
        shops = data.get('shop')
        diagnostic['shop_type'] = _value_type(shops)
        if isinstance(shops, list) and len(shops) <= 1000:
            diagnostic['shop_count'] = len(shops)
        error = data.get('error')
        if error:
            diagnostic['provider_error_present'] = True
            codes = _provider_error_codes(error)
            if codes:
                diagnostic['provider_error_codes'] = codes
    return diagnostic


def integer(value, field, diagnostic):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise PaginationChanged(f'invalid_{field}', diagnostic)
    try:
        result = int(value)
    except ValueError:
        raise PaginationChanged(f'invalid_{field}', diagnostic) from None
    if result < 0 or str(result) != str(value):
        raise PaginationChanged(f'invalid_{field}', diagnostic)
    return result


def page_projection(raw, response):
    if response.status != 200:
        raise HPApiError('http_status', _page_diagnostic(response.status, body_bytes=len(raw)))
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HPApiError('invalid_json', _page_diagnostic(response.status, body_bytes=len(raw),
                                                          payload_type='invalid_json')) from None
    if not isinstance(doc, dict):
        raise HPApiError('top_level_not_object', _page_diagnostic(response.status, body_bytes=len(raw),
                                                                 payload_type=_value_type(doc)))
    data = doc.get('results')
    if not isinstance(data, dict):
        raise HPApiError('results_not_object', _page_diagnostic(response.status, body_bytes=len(raw),
                                                                payload_type=_value_type(data)))
    diagnostic = _page_diagnostic(response.status, data, body_bytes=len(raw), payload_type='object')
    if data.get('error'):
        raise HPApiError('provider_error', diagnostic)
    total = integer(data.get('results_available'), 'results_available', diagnostic)
    start = integer(data.get('results_start'), 'results_start', diagnostic)
    returned = integer(data.get('results_returned'), 'results_returned', diagnostic)
    shops = data.get('shop')
    if not isinstance(shops, list):
        raise PaginationChanged('shop_not_array', diagnostic)
    if len(shops) != returned:
        raise PaginationChanged('shop_count_mismatch', diagnostic)
    if returned > 100:
        raise PaginationChanged('page_size_over_limit', diagnostic)
    if start < 1:
        raise PaginationChanged('start_below_one', diagnostic)
    rows = []
    for shop in shops:
        identity = shop.get('id')
        if not isinstance(identity, str) or not identity:
            raise PaginationChanged('missing_id', diagnostic)
        try:
            if isinstance(shop.get('lat'), bool) or isinstance(shop.get('lng'), bool):
                raise ValueError()
            coordinates = point(float(shop['lat']), float(shop['lng']))
        except (KeyError, TypeError, ValueError):
            raise BadCoordinates('unknown_800m_membership', diagnostic) from None
        rows.append({'id': identity, **coordinates, 'name': shop.get('name'),
                     'address': shop.get('address'), 'genre': (shop.get('genre') or {}).get('code')})
    return {'total': total, 'start': start, 'returned': returned, 'shops': rows,
            'diagnostic': diagnostic,
            'received_at': datetime.now(timezone.utc).isoformat()}


def acquire_station(station, budget, key):
    shops, page_receipts, total = {}, [], None
    started = datetime.now(timezone.utc).isoformat()
    for page_index in range(budget.limits['pages_per_station']):
        start = 1 + page_index*100
        params = {'lat': station['lat'], 'lng': station['lng'], 'range': 3,
                  'count': 100, 'start': start, 'format': 'json', 'order': 1}
        query_hash = hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
        params['key'] = key
        request = urllib.request.Request('https://webservice.recruit.co.jp/hotpepper/gourmet/v1/?'+urllib.parse.urlencode(params),
                                        headers={'User-Agent':'city-rating-food-shadow/2.0', 'Accept-Encoding':'identity'})
        page = budget.fetch(f"hp:{station['slug']}:{start}:{query_hash}", request, page_projection, kind='page')
        if page['start'] != start:
            raise PaginationChanged('start_mismatch', page.get('diagnostic'))
        if total is not None and page['total'] != total:
            raise PaginationChanged('total_changed_during_pagination', page.get('diagnostic'))
        total = page['total']
        expected = min(100, max(0, total-start+1))
        if page['returned'] != expected:
            raise PaginationChanged('returned_count_mismatch', page.get('diagnostic'))
        for shop in page['shops']:
            if shop['id'] in shops:
                raise PaginationChanged('duplicate_or_conflicting_provider_id', page.get('diagnostic'))
            shops[shop['id']] = shop
        page_receipts.append({'query_sha256':query_hash,'start': start, 'returned': page['returned'], 'received_at': page['received_at'],
                              'diagnostic': page['diagnostic'],
                              'projected_sha256': hashlib.sha256(json.dumps(page, sort_keys=True).encode()).hexdigest()})
        if len(shops) == total:
            inside = sorted((v for v in shops.values() if distance(station, v) <= 800), key=lambda v:v['id'])
            status = 'complete_provider_zero' if total == 0 else 'complete_800m_zero' if not inside else 'complete_positive'
            return {'slug': station['slug'], 'status': status, 'query_radius_m': 1000, 'analysis_radius_m': 800,
                    'first_received_at': page_receipts[0]['received_at'], 'finished_at': page_receipts[-1]['received_at'], 'results_available_1000m': total,
                    'unique_fetched': len(shops), 'outside_800m': len(shops)-len(inside),
                    'pages': page_receipts, 'venues_800m': inside, 'count_800m': len(inside)}
        if len(shops) > total:
            raise PaginationChanged('unexpected_extra_rows', page.get('diagnostic'))
    raise AcquisitionStopped('station_page_cap_truncated')


def acquire_sites(sites, budget, key):
    output = []
    for index, station in enumerate(sites):
        try:
            output.append(acquire_station(station, budget, key))
        except Exception as exc:
            reason = exc.error_type if isinstance(exc, RequestRejected) else type(exc).__name__
            status = 'bad_coordinates' if reason == 'BadCoordinates' else 'truncated' if reason == 'PaginationChanged' or type(exc) is AcquisitionStopped else 'error' 
            row = {'slug': station['slug'], 'status': status, 'count_800m': None,
                   'error_type': reason, 'venues_800m': None}
            diagnostic = exc.diagnostic if isinstance(exc, RequestRejected) else getattr(exc, 'safe_diagnostic', None)
            if isinstance(diagnostic, dict):
                row['error_diagnostic'] = diagnostic
            output.append(row)
            output.extend({'slug': s['slug'], 'status':'missing', 'count_800m':None, 'venues_800m':None} for s in sites[index+1:])
            return {'status':'incomplete', 'stations': output}
    return {'status':'complete', 'stations':output}


def confirmation_checkpoint(prescreen):
    zeros = [r for r in prescreen['stations'] if r['status'] in ('complete_provider_zero','complete_800m_zero')]
    rows = []
    for row in zeros:
        first = datetime.fromisoformat(row['finished_at'])
        if first.tzinfo is None:
            raise ValueError('Undated zero cannot be confirmed')
        rows.append({'slug':row['slug'], 'first_status':row['status'], 'first_complete_at':first.isoformat(),
                     'eligible_from':(first+timedelta(hours=24)).isoformat(),
                     'eligible_until':(first+timedelta(hours=72)).isoformat()})
    return {'status':'pending_real_time' if rows else 'insufficient_no_initial_zeros', 'candidates':rows,
            'batch_eligible_from':max((r['eligible_from'] for r in rows),default=None),
            'batch_eligible_until':min((r['eligible_until'] for r in rows),default=None)}
