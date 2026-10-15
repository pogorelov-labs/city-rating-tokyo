"""Pinned Overture parquet ranges; only permitted phase circles leave extraction."""
from __future__ import annotations

import base64
import io
import json
import math
import re
import struct
import urllib.request
import xml.etree.ElementTree as ET

from .bounded import AcquisitionStopped
from .stage0 import distance, point

BASE = 'https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/'
COLUMNS = ['id', 'geometry', 'names', 'addresses', 'websites', 'phones', 'basic_category',
           'taxonomy', 'confidence', 'sources', 'bbox', 'operating_status']


def range_projection(start, end, *, etag=None, size=None, suffix=False):
    def project(raw, response):
        if response.status != 206:
            raise ValueError('range_not_honored')
        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
        if not match:
            raise ValueError('missing_range_contract')
        actual_start, actual_end, actual_size = map(int, match.groups())
        expected_start = actual_size-start if suffix else start
        expected_end = actual_size-1 if suffix else end
        if (actual_start, actual_end) != (expected_start, expected_end) or len(raw) != actual_end-actual_start+1:
            raise ValueError('incomplete_or_wrong_range')
        tag = response.headers.get('ETag')
        if not tag or etag is not None and tag != etag or size is not None and size != actual_size:
            raise ValueError('object_identity_changed')
        return {'body_b64': base64.b64encode(raw).decode(), 'etag': tag, 'size': actual_size}
    return project


def fetch_range(budget, url, start, end=None, *, etag=None, size=None, suffix=False):
    if not url.startswith(BASE) or '?' in url or '#' in url:
        raise ValueError('unapproved_object_destination')
    header = f'bytes=-{start}' if suffix else f'bytes={start}-{end}'
    request = urllib.request.Request(url, headers={'Range': header, 'Accept-Encoding':'identity',
                                    **({'If-Match':etag} if etag else {})})
    identity = 'ov:'+url.removeprefix(BASE)+':'+header
    return budget.fetch(identity, request, range_projection(start, end, etag=etag, size=size, suffix=suffix),
                        response_bytes=start if suffix else end-start+1)


def metadata(manifest, budget):
    import pyarrow.parquet as pq
    release = manifest['overture']['release']
    prefix = f'release/{release}/theme=places/type=place/'
    expected = manifest['overture']['objects']

    def listing(raw, response):
        if response.status != 200:
            raise ValueError('listing_http_status')
        tree = ET.fromstring(raw)
        ns = {'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
        truncated = tree.find('s:IsTruncated', ns)
        if truncated is None or truncated.text != 'false':
            raise ValueError('incomplete_listing')
        urls = [BASE+n.text for n in tree.findall('s:Contents/s:Key', ns) if n.text and n.text.endswith('.parquet')]
        if sorted(urls) != sorted(expected):
            raise ValueError('pinned_listing_changed')
        return {'objects':urls}

    budget.fetch('ov:listing:'+release, urllib.request.Request(BASE+'?list-type=2&prefix='+prefix+'&max-keys=1000',
                 headers={'Accept-Encoding':'identity'}), listing)
    objects = []
    for url in expected:
        tail = fetch_range(budget, url, 8, suffix=True)
        raw_tail = base64.b64decode(tail['body_b64'])
        if raw_tail[4:] != b'PAR1':
            raise ValueError('unsupported_parquet_footer')
        footer_size = struct.unpack('<I', raw_tail[:4])[0]+8
        if footer_size > budget.limits['response_bytes'] or footer_size >= tail['size']:
            raise ValueError('footer_budget_or_shape')
        footer = fetch_range(budget, url, tail['size']-footer_size, tail['size']-1,
                             etag=tail['etag'], size=tail['size'])
        raw_footer = base64.b64decode(footer['body_b64'])
        md = pq.ParquetFile(io.BytesIO(b'PAR1'+raw_footer)).metadata
        groups = []
        for index in range(md.num_row_groups):
            group = md.row_group(index)
            columns = {group.column(j).path_in_schema:group.column(j) for j in range(group.num_columns)}
            extents = []
            for name, fn in [('bbox.xmin', 'min'), ('bbox.ymin','min'), ('bbox.xmax','max'), ('bbox.ymax','max')]:
                stats = columns[name].statistics if name in columns else None
                value = getattr(stats, fn, None) if stats is not None and stats.has_min_max and stats.null_count == 0 else None
                extents.append(value if isinstance(value, (int,float)) and math.isfinite(value) else None)
            groups.append({'index':index, 'rows':group.num_rows, 'bounds':extents})
        objects.append({'url':url, 'etag':tail['etag'], 'size':tail['size'],
                        'footer_b64':footer['body_b64'], 'groups':groups})
    return {'release':release, 'objects':objects, 'complete':True}


def selected_groups(item, stations):
    # Spherical 800m longitude half-width is <.01 degrees over this fixed frame;
    # latitude half-width is <.008. Missing stats always retain the group.
    selected = []
    for group in item['groups']:
        bounds = group['bounds']
        if any(v is None for v in bounds) or any(
            bounds[2] >= s['lng']-.01 and bounds[0] <= s['lng']+.01 and
            bounds[3] >= s['lat']-.008 and bounds[1] <= s['lat']+.008 for s in stations):
            selected.append(group['index'])
    return selected


class Ranges(io.RawIOBase):
    def __init__(self, item, budget):
        self.item, self.budget = item, budget
        self.footer = base64.b64decode(item['footer_b64'])
        self.position = 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position+offset if whence == 1 else self.item['size']+offset
        if not 0 <= self.position <= self.item['size']:
            raise ValueError('invalid_parquet_seek')
        return self.position

    def read(self, length=-1):
        self.budget.remaining()
        length = self.item['size']-self.position if length < 0 else min(length, self.item['size']-self.position)
        if length <= 0: return b''
        if self.position >= self.item['size']-len(self.footer):
            begin = self.position-(self.item['size']-len(self.footer))
            data = self.footer[begin:begin+length]
        else:
            result = fetch_range(self.budget, self.item['url'], self.position, self.position+length-1,
                                 etag=self.item['etag'], size=self.item['size'])
            data = base64.b64decode(result['body_b64'])
        self.position += len(data)
        return data


def wkb_point(raw):
    if not isinstance(raw, bytes) or len(raw) != 21 or raw[0] not in (0,1):
        raise ValueError('unsupported_place_geometry')
    endian = '<' if raw[0] else '>'
    if struct.unpack(endian+'I', raw[1:5])[0] != 1:
        raise ValueError('place_geometry_not_point')
    lng, lat = struct.unpack(endian+'dd', raw[5:])
    return point(lat, lng)


def is_food(hierarchy, contract):
    h = hierarchy or []
    if not isinstance(h, list) or any(not isinstance(v,str) for v in h):
        raise ValueError('invalid_food_taxonomy')
    return (len(h)>1 and h[0] == contract['hierarchy_prefix'] and h[1] in contract['second_level']) or bool(set(h)&set(contract['any_hierarchy_level']))


def extract(manifest, stations, pinned_metadata, budget):
    import pyarrow.parquet as pq
    if not pinned_metadata.get('complete') or pinned_metadata['release'] != manifest['overture']['release']:
        raise ValueError('incomplete_metadata')
    if sorted(x['url'] for x in pinned_metadata['objects']) != sorted(manifest['overture']['objects']):
        raise ValueError('missing_object_metadata')
    kept, seen, groups = {}, {}, []
    filters = {key:0 for key in ('read', 'outside_phase', 'low_or_missing_confidence', 'operation_excluded', 'nonfood', 'duplicate_id')}
    contract = manifest['overture']
    for item in pinned_metadata['objects']:
        for index in selected_groups(item, stations):
            identity = item['url']+':group:'+str(index)
            budget.group(identity)
            reader = Ranges(item, budget)
            table = pq.ParquetFile(reader, pre_buffer=False).read_row_group(index, columns=COLUMNS, use_threads=False)
            expected = next(g['rows'] for g in item['groups'] if g['index']==index)
            if table.num_rows != expected:
                raise ValueError('incomplete_row_group')
            groups.append({'object':item['url'], 'row_group':index, 'rows':expected})
            for row in table.to_pylist():
                budget.remaining()
                filters['read'] += 1
                coords = wkb_point(row['geometry'])
                memberships = [s['slug'] for s in stations if distance(s, coords)<=800]
                if not memberships:
                    filters['outside_phase'] += 1
                    continue
                identity = row.get('id')
                if not isinstance(identity,str) or not identity:
                    raise ValueError('missing_provider_identity')
                row = {k:v for k,v in row.items() if k != 'geometry'}
                if identity in seen:
                    if seen[identity] != row:
                        raise ValueError('conflicting_provider_identity')
                    filters['duplicate_id'] += 1
                    continue
                seen[identity] = row
                confidence = row.get('confidence')
                if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or confidence < contract['confidence_min']:
                    filters['low_or_missing_confidence'] += 1
                    continue
                if row.get('operating_status') not in contract['operating_status_included']:
                    filters['operation_excluded'] += 1
                    continue
                hierarchy = (row.get('taxonomy') or {}).get('hierarchy')
                if not is_food(hierarchy, contract['food']):
                    filters['nonfood'] += 1
                    continue
                kept[identity] = {**row, **coords, 'memberships':sorted(memberships)}
    return {'status':'complete', 'release':contract['release'], 'groups':groups, 'filters':filters,
            'rows':sorted(kept.values(),key=lambda r:r['id']),
            'stations':[{'slug':s['slug'], 'count_800m':sum(s['slug'] in r['memberships'] for r in kept.values())} for s in stations]}
