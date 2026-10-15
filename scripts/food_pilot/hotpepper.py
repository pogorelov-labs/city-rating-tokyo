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
    pass


class HPApiError(ValueError):
    pass


class PaginationChanged(ValueError):
    pass


def integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise PaginationChanged('invalid_integer')
    try:
        result = int(value)
    except ValueError:
        raise PaginationChanged('invalid_integer') from None
    if result < 0 or str(result) != str(value):
        raise PaginationChanged('invalid_integer')
    return result


def page_projection(raw, response):
    if response.status != 200:
        raise HPApiError('http_status')
    doc = json.loads(raw)
    data = doc.get('results')
    if not isinstance(data, dict) or data.get('error'):
        raise HPApiError('provider_error')
    total = integer(data.get('results_available'))
    start = integer(data.get('results_start'))
    returned = integer(data.get('results_returned'))
    shops = data.get('shop')
    if not isinstance(shops, list) or len(shops) != returned or returned > 100 or start < 1:
        raise PaginationChanged('incomplete_page_shape')
    rows = []
    for shop in shops:
        identity = shop.get('id')
        if not isinstance(identity, str) or not identity:
            raise PaginationChanged('missing_id')
        try:
            if isinstance(shop.get('lat'), bool) or isinstance(shop.get('lng'), bool):
                raise ValueError()
            coordinates = point(float(shop['lat']), float(shop['lng']))
        except (KeyError, TypeError, ValueError):
            raise BadCoordinates('unknown_800m_membership') from None
        rows.append({'id': identity, **coordinates, 'name': shop.get('name'),
                     'address': shop.get('address'), 'genre': (shop.get('genre') or {}).get('code')})
    return {'total': total, 'start': start, 'returned': returned, 'shops': rows,
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
        if page['start'] != start or total is not None and page['total'] != total:
            raise PaginationChanged('pagination_changed')
        total = page['total']
        expected = min(100, max(0, total-start+1))
        if page['returned'] != expected:
            raise PaginationChanged('missing_page_rows')
        for shop in page['shops']:
            if shop['id'] in shops:
                raise PaginationChanged('duplicate_or_conflicting_provider_id')
            shops[shop['id']] = shop
        page_receipts.append({'query_sha256':query_hash,'start': start, 'returned': page['returned'], 'received_at': page['received_at'],
                              'projected_sha256': hashlib.sha256(json.dumps(page, sort_keys=True).encode()).hexdigest()})
        if len(shops) == total:
            inside = sorted((v for v in shops.values() if distance(station, v) <= 800), key=lambda v:v['id'])
            status = 'complete_provider_zero' if total == 0 else 'complete_800m_zero' if not inside else 'complete_positive'
            return {'slug': station['slug'], 'status': status, 'query_radius_m': 1000, 'analysis_radius_m': 800,
                    'first_received_at': page_receipts[0]['received_at'], 'finished_at': page_receipts[-1]['received_at'], 'results_available_1000m': total,
                    'unique_fetched': len(shops), 'outside_800m': len(shops)-len(inside),
                    'pages': page_receipts, 'venues_800m': inside, 'count_800m': len(inside)}
        if len(shops) > total:
            raise PaginationChanged('unexpected_extra_rows')
    raise AcquisitionStopped('station_page_cap_truncated')


def acquire_sites(sites, budget, key):
    output = []
    for index, station in enumerate(sites):
        try:
            output.append(acquire_station(station, budget, key))
        except Exception as exc:
            reason = exc.error_type if isinstance(exc, RequestRejected) else type(exc).__name__
            status = 'bad_coordinates' if reason == 'BadCoordinates' else 'truncated' if reason == 'PaginationChanged' or type(exc) is AcquisitionStopped else 'error' 
            output.append({'slug': station['slug'], 'status': status, 'count_800m': None,
                           'error_type': reason, 'venues_800m': None})
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
