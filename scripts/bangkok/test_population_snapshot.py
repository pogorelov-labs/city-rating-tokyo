"""Regression guard for the committed CRTKY-197 adoption outputs."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('population_replay', HERE / 'rebuild-population.py')
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


@pytest.mark.parametrize('baseline_name', ['adoption', 'refresh-2026-10-24'])
def test_committed_population_snapshot_and_scope(baseline_name):
    import hashlib
    root = Path(__file__).resolve().parents[2]
    data = root / 'data/bangkok'
    app = root / 'app/src/data/bangkok'
    baseline = json.loads((data / rebuild.BASELINES[baseline_name]).read_text())
    fixture = root / 'scripts/fixtures/bangkok-population/adoption'
    def snapshot(name, directory):
        return json.loads(((fixture if baseline_name == 'adoption' else directory) / name).read_text())
    comparison = snapshot('population-comparison.json', data)
    districts = snapshot('districts.json', app)
    signals = snapshot('signals.json', data)
    meta = snapshot('meta.json', app)
    rows = comparison['districts']
    assert len(rows) == 50
    assert set(rows) == {d['slug'] for d in districts['districts']} == set(baseline['districts'])
    assert comparison['source'] == json.loads((data / 'population-source.json').read_text())
    assert comparison['summary']['population'] == pytest.approx(sum(r['population'] for r in rows.values()), abs=1e-6)
    reproduced = rebuild.compare(baseline['districts'], rows)
    assert rows == reproduced
    for d in districts['districts']:
        row = rows[d['slug']]
        assert d['ratings']['crowd'] == row['worldpop_rating']
        assert d['sources']['crowd'] == ['worldpop_2020', 'overture']
        assert d['confidence']['crowd'] == 'moderate'
        s = signals['districts'][d['slug']]
        assert s['ratings']['crowd'] == row['worldpop_rating']
        assert s['raw']['crowd'] == round(row['worldpop_raw'], 4)
    weights = json.loads((root / 'packages/schema/constants.json').read_text())['default_weights']
    assert meta['default_anchors'] == rebuild.R.anchors([rebuild.R.composite(d['ratings'], weights) for d in districts['districts']])
    assert meta['medians']['crowd'] == rebuild.R.median_int([d['ratings']['crowd'] for d in districts['districts']])
    # Explicit scope gate: every other rating, fact, confidence, grid/station
    # signal and date must remain as it was at the frozen adoption baseline.
    districts.pop('_meta'); signals.pop('_meta')
    for d in districts['districts']:
        d['ratings'].pop('crowd'); d['sources'].pop('crowd')
    for d in signals['districts'].values():
        d['ratings'].pop('crowd'); d['raw'].pop('crowd')
    meta['medians'].pop('crowd'); meta.pop('default_anchors')
    for name, doc in [('districts', districts), ('signals', signals), ('meta', meta)]:
        digest = hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        assert digest == baseline['_meta']['unchanged_signatures'][name]
    for lang in ('en', 'ja', 'ru'):
        messages = json.loads((root / f'app/src/messages/{lang}/common.json').read_text())
        assert messages['sources']['worldpop_2020']
        assert set(messages['populationMethodology']) >= {'method', 'limits', 'attribution', 'tableSource'}



def test_committed_manifest_contract():
    from types import SimpleNamespace
    import rasterio
    from affine import Affine
    from population import validate_raster
    source = json.loads((HERE.parents[1] / 'data/bangkok/population-source.json').read_text())
    assert source['record_id'] == 49890 and source['epoch'] == 2020
    assert source['license'] == 'CC-BY-4.0'
    assert source['bytes'] == 28878233
    assert source['sha256'] == '400dc5435e15e78ce6b5e510327ec863c62d209011ce1b03cad4445773753d42'
    assert source['filename'] == 'tha_ppp_2020_constrained.tif'
    assert source['url'].endswith('/Global_2000_2020_Constrained/2020/BSGM/THA/' + source['filename'])
    spec = source['raster']
    # Exercise the actual manifest against the independent accepted raster contract.
    validate_raster(SimpleNamespace(crs=rasterio.crs.CRS.from_epsg(4326), count=1,
                    shape=(17816, 9952), dtypes=('float32',), nodata=-99999,
                    transform=Affine(0.0008333333299839229, 0, 97.345416292,
                                     0, -0.0008333333299842838, 20.462916786)), source)
    assert spec['crs'] == 'EPSG:4326' and spec['dtype'] == 'float32' and spec['nodata'] == -99999


@pytest.fixture(params=['adoption', 'refresh-2026-10-24'])
def replay_workspace(tmp_path, monkeypatch, request):
    import copy
    import shutil
    root = HERE.parents[1]
    baseline_name = request.param
    paths = ['data/bangkok/' + rebuild.BASELINES[baseline_name], 'data/bangkok/population-source.json',
             'data/bangkok/signals.json', 'app/src/data/bangkok/districts.json',
             'app/src/data/bangkok/geometry.json', 'app/src/data/bangkok/meta.json',
             'packages/schema/constants.json']
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = root / name
        if baseline_name == 'adoption' and Path(name).name in ('signals.json', 'districts.json', 'geometry.json', 'meta.json'):
            source = root / 'scripts/fixtures/bangkok-population/adoption' / Path(name).name
        shutil.copyfile(source, target)
    comparison_path = (root / 'scripts/fixtures/bangkok-population/adoption/population-comparison.json'
                       if baseline_name == 'adoption' else root / 'data/bangkok/population-comparison.json')
    actual = json.loads(comparison_path.read_text())
    populations = {s: {k: r[k] for k in ('population', 'polygon_area_km2', 'pixels', 'settled_pixels')}
                   for s, r in actual['districts'].items()}
    monkeypatch.setattr(rebuild, 'ROOT', tmp_path)
    monkeypatch.setattr(rebuild, 'APP', tmp_path / 'app/src/data/bangkok')
    monkeypatch.setattr(rebuild, 'DATA', tmp_path / 'data/bangkok')
    # Main-path tests are offline: aggregation itself is tested against GeoTIFF
    # fixtures; here its validated result is fixed so preflight/writes are real.
    monkeypatch.setattr(rebuild, 'load_population', lambda *args: (copy.deepcopy(populations), copy.deepcopy(actual['summary'])))
    return tmp_path, baseline_name


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def original_snapshot(root, baseline_name):
    baseline = json.loads((root / 'data/bangkok' / rebuild.BASELINES[baseline_name]).read_text())['districts']
    district_path = root / 'app/src/data/bangkok/districts.json'
    signal_path = root / 'data/bangkok/signals.json'
    meta_path = root / 'app/src/data/bangkok/meta.json'
    d = json.loads(district_path.read_text()); s = json.loads(signal_path.read_text())
    m = json.loads(meta_path.read_text())
    d['_meta'].pop('population'); s['_meta'].pop('population')
    for row in d['districts']:
        b = baseline[row['slug']]
        row['ratings']['crowd'] = b['crowd_rating']
        row['sources']['crowd'] = ['dopa_population', 'overture']
        s['districts'][row['slug']]['ratings']['crowd'] = b['crowd_rating']
        s['districts'][row['slug']]['raw']['crowd'] = b['crowd_raw']
    weights = json.loads((root / 'packages/schema/constants.json').read_text())['default_weights']
    m['medians']['crowd'] = rebuild.R.median_int([r['ratings']['crowd'] for r in d['districts']])
    m['default_anchors'] = rebuild.R.anchors([rebuild.R.composite(r['ratings'], weights) for r in d['districts']])
    district_path.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '\n')
    signal_path.write_text(json.dumps(s, ensure_ascii=False, indent=1) + '\n')
    meta_path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')


def test_main_original_adoption_and_idempotent_replay(replay_workspace):
    root, baseline_name = replay_workspace
    original_snapshot(root, baseline_name)
    rebuild.main(['--baseline', baseline_name])
    first = files(root)
    rebuild.main(['--baseline', baseline_name])
    assert files(root) == first
    comparison = json.loads((root / 'data/bangkok/population-comparison.json').read_text())
    assert comparison['summary']['changed_ratings'] == 20
    assert comparison['summary']['population'] == pytest.approx(10887568.273106098, abs=1e-6)


@pytest.mark.parametrize('change', ['poi', 'crowd', 'rating', 'provenance', 'anchors', 'original_checksum'])
def test_main_rejects_incompatible_snapshots_without_writes(replay_workspace, change):
    root, baseline_name = replay_workspace
    path = root / 'data/bangkok/signals.json'
    if change == 'original_checksum':
        original_snapshot(root, baseline_name)
    doc = json.loads(path.read_text())
    if change == 'poi': doc['districts']['watthana']['raw']['food'] += 0.1
    elif change == 'crowd': doc['districts']['watthana']['raw']['crowd'] += 0.1
    elif change == 'rating': doc['districts']['watthana']['ratings']['crowd'] += 1
    elif change == 'provenance': doc['_meta']['population']['sha256'] = '0' * 64
    elif change == 'original_checksum': doc['_meta']['generated'] = '2099-01-01'
    elif change == 'anchors':
        meta_path = root / 'app/src/data/bangkok/meta.json'
        meta = json.loads(meta_path.read_text()); meta['default_anchors']['p50'] += 0.1
        meta_path.write_text(json.dumps(meta))
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    before = files(root)
    with pytest.raises(ValueError, match='Incompatible'):
        rebuild.main(['--baseline', baseline_name])
    assert files(root) == before


def test_replay_requires_explicit_baseline_selection():
    with pytest.raises(SystemExit):
        rebuild.main([])


def test_current_replay_preserves_published_snapshot_bytes(replay_workspace):
    root, baseline_name = replay_workspace
    paths = ['app/src/data/bangkok/districts.json', 'data/bangkok/signals.json', 'app/src/data/bangkok/meta.json']
    before = {path: (root / path).read_bytes() for path in paths}
    rebuild.main(['--baseline', baseline_name])
    assert {path: (root / path).read_bytes() for path in paths} == before


def test_selected_geometry_must_match_without_writes(replay_workspace):
    root, baseline_name = replay_workspace
    path = root / 'app/src/data/bangkok/geometry.json'
    path.write_text(path.read_text() + ' ')
    before = files(root)
    with pytest.raises(ValueError, match='Incompatible geometry'):
        rebuild.main(['--baseline', baseline_name])
    assert files(root) == before
