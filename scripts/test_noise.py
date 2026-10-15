"""Noise facts: semantics, independent-location evaluation and offline reproducibility."""
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/schema/python'))
spec = importlib.util.spec_from_file_location('noise_build', ROOT/'scripts/noise/build.py')
noise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(noise)


@pytest.fixture(scope='module')
def rebuilt():
    return noise.build()


def test_geometry_uses_segment_not_endpoints():
    assert noise.segment_distance(5, 2, 0, 0, 10, 0) == 2
    assert noise.segment_distance(-2, 0, 0, 0, 10, 0) == 2
    assert noise.segment_distance(3, 4, 0, 0, 0, 0) == 5


def test_exact_address_normalization_does_not_guess():
    assert noise.address_key(' 千代田区外神田２丁目５ ') == noise.address_key('千代田区外神田2-5')
    assert noise.address_key('千代田区外神田2-5-1') != noise.address_key('千代田区外神田2-5')
    assert noise.address_key('千代田区外神田2-6') != noise.address_key('千代田区外神田2-5')


def test_quietness_scale_and_direction():
    assert noise.quietness(45) == 10
    assert noise.quietness(80) == 1
    assert noise.quietness(20) == 10
    assert noise.quietness(120) == 1
    assert noise.quietness(55) > noise.quietness(65)


def test_more_venues_and_closer_roads_cannot_mean_quieter(rebuilt):
    _, report, _ = rebuilt
    remote = {'arterial_distance_m': 2000, 'expressway_distance_m': 2000, 'nightlife_800m': 0}
    for beta in report['model'].values():
        base = noise.predict(remote, beta)
        assert noise.predict(remote | {'nightlife_800m': 100}, beta) > base
        assert noise.predict(remote | {'arterial_distance_m': 0}, beta) > base
        assert noise.predict(remote | {'expressway_distance_m': 0}, beta) > base
    # Periods share one scale; the nightlife assumption is stronger at night.
    assert report['nightlife_assumption_db_per_log_count'] == {'day': .5, 'night': 1.5}


def test_no_fabricated_silence_from_missing_extent():
    index = noise.ProxyIndex.__new__(noise.ProxyIndex)
    index.latitude = 35.6
    index.bboxes = [[35, 139, 36, 140]]
    assert index.features(35, 139) is None
    assert index.features(0, 0) is None


def test_calibration_split_is_by_location_and_mae_is_real(rebuilt):
    _, report, matched = rebuilt
    train = [r for r in matched if r['id'] in report['training_ids']]
    test = [r for r in matched if r['id'] in report['test_ids']]
    assert len(train) == report['training_rows'] == 99
    assert len({r['address_key'] for r in train}) == report['training_locations'] == 68
    assert len(test) == report['test_locations'] == 76
    assert {r['address_key'] for r in train}.isdisjoint(r['address_key'] for r in test)
    # Catch changed spellings at the same physical location as well.
    for row in test:
        assert row['year'] == 2023
        assert min(math.hypot((row['lat']-t['lat'])*111195, (row['lng']-t['lng'])*90600) for t in train) > 100
    for period in ['day', 'night']:
        error = sum(abs(noise.predict(r['features'], report['model'][period])-r[f'{period}_db']) for r in test)/len(test)
        assert round(error, 3) == report['evaluation'][period]['mae_db']
    assert report['evaluation']['night']['mae_db'] > report['evaluation']['night']['training_mean_baseline_mae_db']
    assert report['matched_readings_by_year']['2023'] == 83
    assert report['unmatched_addresses_by_year']['2023'] == 184
    assert report['test_excluded_repeated_locations'] == 7


def test_both_cities_have_estimates_but_bangkok_has_no_measured_values(rebuilt):
    output, report, _ = rebuilt
    assert len(output['tokyo']) == 1493
    assert len(output['bangkok']) == 133
    assert report['bangkok']['mae_db'] is None
    for city in ['tokyo', 'bangkok']:
        for row in output[city].values():
            assert row['confidence'] == 'estimate'
            assert row['status'] == 'available'
            assert 1 <= row['day'] <= 10 and 1 <= row['night'] <= 10
            assert 'day_db' not in row and 'night_db' not in row
            if city == 'bangkok':
                assert row['calibration'] == 'uncalibrated_transfer'
                assert row['anchors'] == []
    assert output['tokyo']['shibuya']['night'] < output['tokyo']['chitose-funabashi']['night']


def test_anchors_remain_recent_roadside_measurements_with_archival_location(rebuilt):
    output, _, matched = rebuilt
    readings = {r['id']: r for r in matched}
    for row in output['tokyo'].values():
        for anchor in row['anchors']:
            assert anchor['year'] == 2023 and anchor['coordinate_year'] == 2013
            assert 0 <= anchor['distance_m'] <= 800
            assert anchor['day_db'] == readings[anchor['id']]['day_db']
            assert anchor['night_db'] == readings[anchor['id']]['night_db']
    assert output['tokyo']['akihabara']['anchors'][0]['day_db'] == 65


def test_complaints_are_municipal_context(rebuilt):
    output, _, _ = rebuilt
    assert output['tokyo']['shibuya']['complaints'] == {
        'municipality': '渋谷区', 'series': [
            {'year': 2022, 'count': 41}, {'year': 2023, 'count': 126}, {'year': 2024, 'count': 216}]}
    assert 'complaints' not in output['tokyo']['yokohama']


def test_complaints_require_tokyo_municipality_identity(rebuilt):
    output, _, _ = rebuilt
    wards = noise.read_json(ROOT/'app/src/data/ward-data.json')
    # These names collide with Tokyo municipalities in the same yearbook.
    for slug in ['chiba', 'saitama-shintoshin', 'sagamihara', 'doro']:
        assert wards[slug]['ward_name'] in ('中央区', '北区')
        assert 'complaints' not in output['tokyo'][slug]
    for station in noise.read_json(ROOT/'data/stations.json'):
        if station['prefecture'] != '13':
            assert 'complaints' not in output['tokyo'][station['slug']]
    # Keep Tokyo's true municipality, even when ward_name is a smaller district.
    assert output['tokyo']['oji']['complaints']['municipality'] == '北区'
    assert output['tokyo']['ningyocho']['complaints'] == {
        'municipality': '中央区', 'series': [
            {'year': 2022, 'count': 192}, {'year': 2023, 'count': 122}, {'year': 2024, 'count': 128}]}


def test_outputs_reproduce_offline_and_inputs_are_hashed(rebuilt):
    output, report, matched = rebuilt
    for path, doc in [
        ('app/src/data/noise/quietness.json', output),
        ('data/noise/calibration.json', report),
        ('data/noise/tmg-matched.json', matched),
    ]:
        assert (ROOT/path).read_text() == json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    for source in report['inputs']:
        assert noise.sha(ROOT/source['path']) == source['sha256']


def test_generated_schema_accepts_facts(rebuilt):
    from city_rating_schema.models import QuietnessFact
    output, _, _ = rebuilt
    for city in ['tokyo', 'bangkok']:
        for row in output[city].values():
            QuietnessFact.model_validate(row)
    with pytest.raises(ValueError):
        QuietnessFact.model_validate(output['tokyo']['shibuya'] | {'confidence': 'strong'})
