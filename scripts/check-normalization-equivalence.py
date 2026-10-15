#!/usr/bin/env python3
"""Read-only CRTKY-166 replay against a git revision; no network/store access.

Optional internal HP/OSM census stays outside git. Its other remote inputs
are missing, so that replay is explicitly partial, never a refresh proof.
"""
import argparse
import ast
import gzip
import hashlib
import json
import subprocess
import types
from pathlib import Path

from normalization_replay import ROOT, fixture_inputs, load_compute, replay_bangkok, replay_compute

BASELINE = 'd2f53570bccfe9a3b1636f7f6b331cb19e237935'


def git_source(revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, text=True)


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',',':')).encode()).hexdigest()


def compare(label, old, new):
    if json.dumps(old) != json.dumps(new):
        raise AssertionError(f'{label}: output or ordering changed')
    return {'equal': True, 'sha256': digest(new)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--historical-census', type=Path)
    args = parser.parse_args()
    old = load_compute(source=git_source(args.baseline,'scripts/compute-ratings.py'))
    new = load_compute()
    report = {'baseline':args.baseline, 'synthetic_tokyo':compare('synthetic Tokyo',
        replay_compute(old,fixture_inputs()),replay_compute(new,fixture_inputs()))}
    old_bkk = types.ModuleType('old_bangkok')
    exec(git_source(args.baseline,'scripts/bangkok/ratings.py'),old_bkk.__dict__)
    new_bkk = types.ModuleType('new_bangkok')
    new_bkk.__file__ = str(ROOT / 'scripts/bangkok/ratings.py')
    exec((ROOT / 'scripts/bangkok/ratings.py').read_text(),new_bkk.__dict__)
    report['bangkok_rounded_aggregates'] = compare('Bangkok',replay_bangkok(old_bkk),replay_bangkok(new_bkk))
    report['bangkok_rounded_aggregates'].update(districts=50,station_areas=133,
        full_geometry_rebuild=False)
    # MCP only shares anchors; do not pretend it normalizes rating inputs.
    old_tree = ast.parse(git_source(args.baseline,'mcp/src/city_rating_mcp/scoring.py'))
    old_anchor = next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='percentile_anchors')
    old_ns = {}
    exec(compile(ast.Module(body=[old_anchor],type_ignores=[]),'<baseline-mcp>','exec'),old_ns)
    from city_rating_schema.normalize import percentile_anchors
    probes = [[],[7],[9,1,5,2],list(range(1493))]
    report['mcp_anchors'] = compare('MCP anchors', [old_ns['percentile_anchors'](p) for p in probes],
        [percentile_anchors(p,empty={'p5':1.0,'p50':5.5,'p95':10.0}) for p in probes])
    if args.historical_census:
        raw = gzip.decompress(args.historical_census.read_bytes())
        census = json.loads(raw)
        tables = {k: census['tables'][k]['rows'] for k in ('hotpepper','osm_pois')}
        tables.update(osm_extended=[],osm_livability=[],station_wards=[])
        stations = json.loads((ROOT / 'data/stations.json').read_text())
        if isinstance(stations,dict): stations = stations['stations']
        inputs = (stations,tables,new.load_rent_data(),new.load_station_safety()[0],new.load_passengers()[0])
        redirects = new.load_slug_redirects()
        before, after = replay_compute(old,inputs,redirects=redirects),replay_compute(new,inputs,redirects=redirects)
        report['tokyo_partial_historical'] = compare('partial historical Tokyo',before,after)
        report['tokyo_partial_historical'].update(stations=len(stations),
            input_sha256=hashlib.sha256(raw).hexdigest(),
            table_rows={k:len(census['tables'][k]['rows']) for k in ('hotpepper','osm_pois')},
            source_dates={k: sorted({r.get('scraped_at','unknown') for r in census['tables'][k]['rows']}) for k in ('hotpepper','osm_pois')},
            missing_remote_tables=['osm_extended','osm_livability','station_wards'],
            missing_remote_fields=['osm_pois.green_area_sqm'],
            full_refresh_equivalence=False, original_acquisition_completeness='unknown')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
