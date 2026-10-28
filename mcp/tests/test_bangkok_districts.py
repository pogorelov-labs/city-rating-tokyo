"""Offline checks for Bangkok district scope and provenance."""
from pathlib import Path

import pytest

from city_rating_mcp.data import Datamart
from city_rating_mcp.scoring import passes_dealbreakers
from city_rating_mcp.tools.methodology import get_methodology
from city_rating_mcp.tools.search import search_stations
from city_rating_mcp.tools.station import compare_stations, get_station

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bangkok():
    return Datamart.load_bangkok(ROOT / 'app/src/data/bangkok/districts.json')


def test_committed_snapshot_has_50_unique_districts(bangkok):
    assert len(bangkok) == 50
    assert bangkok.get('bang-bon')['_city'] == 'bangkok'


def test_profile_and_comparison_preserve_estimate_provenance(bangkok):
    row = get_station(bangkok, 'bang-bon', locale='ja')
    assert row['unit'] == 'district' and row['city'] == 'bangkok'
    assert row['rent']['provenance'] == 'district_editorial'
    assert row['rent']['metric'] == 'typical_asking'
    assert row['confidence']['safety'] == 'editorial'
    assert '/ja/bangkok/district/bang-bon' in row['url']
    assert 'relative within Bangkok' in row['caveat']
    result = compare_stations(bangkok, ['bang-bon', 'bang-kapi'])
    assert len(result['profiles']) == 2
    assert all(p['rent']['provenance'] == 'district_editorial' for p in result['profiles'])


def test_search_uses_baht_and_district_view(bangkok):
    entry = bangkok.get('bang-bon')
    assert passes_dealbreakers(entry, max_rent=8499)[0] is False
    assert passes_dealbreakers(entry, max_rent=8500)[0] is True
    result = search_stations(bangkok, max_rent=8500)
    row = next(r for r in result['results'] if r['slug'] == 'bang-bon')
    assert row['unit'] == 'district' and row['rent']['one_bed'] == 8500
    assert 'rent_1k_1ldk' not in row


def test_city_filter_boundary_and_methodology():
    from city_rating_mcp.server import _check_city_filters
    with pytest.raises(ValueError, match='Tokyo-specific'):
        _check_city_filters('bangkok', False, True, False)
    _check_city_filters('tokyo', True, True, True)
    assert 'not directly comparable' in get_methodology()['bangkok']['scores']


def test_server_routes_city_without_cross_city_leakage(bangkok, monkeypatch):
    from city_rating_mcp import server
    from city_rating_mcp.data import Datamart
    tokyo = Datamart({'bang-bon': {'slug': 'bang-bon', 'name_en': 'Tokyo fixture',
                                   'ratings': {'food': 3}}}, [], {})
    monkeypatch.setattr(server, '_DM', tokyo)
    monkeypatch.setattr(server, '_BANGKOK_DM', bangkok)
    assert server.get_station('bang-bon')['name'] == 'Tokyo fixture'
    assert server.get_station('bang-bon', city='bangkok')['unit'] == 'district'
    assert server.list_pois('bang-bon', city='bangkok')['categories']['food']['food'] == 711
    with pytest.raises(ValueError, match='city must'):
        server.get_station('bang-bon', city='other')
    with pytest.raises(ValueError, match='Tokyo-specific'):
        server.search_stations(city='bangkok', has_live_camera=True)


def test_bangkok_description_input_for_embeddings(bangkok):
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_embeddings', ROOT / 'scripts/build-embeddings.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    descriptions = {row['slug']: row['description'] for row in bangkok.all()}
    texts, index = module.collect_texts(descriptions)
    assert len(texts) == len(index) == 50 * 3 * 4
    assert all(text.startswith('passage: ') for text in texts)
    assert len(set(index)) == len(index)


def test_semantic_uses_city_specific_vectors(bangkok, monkeypatch):
    from city_rating_mcp import server

    class Vectors:
        def embed_query(self, query):
            return query
        def search(self, vector, *, locale, field, limit):
            return [('bang-bon', 'all', 0.9)]
        def aggregate_vector(self, slug, locale):
            return [1]

    monkeypatch.setattr(server, '_BANGKOK_DM', bangkok)
    monkeypatch.setattr(server, '_BANGKOK_ES', Vectors())
    result = server.semantic_search('quiet', city='bangkok')
    assert result['city'] == 'bangkok' and result['results'][0]['unit'] == 'district'
    assert result['results'][0]['rent']['provenance'] == 'district_editorial'
    assert 'relative within Bangkok' in result['caveat']


def test_embedding_artifact_requires_city_snapshot_and_model(tmp_path):
    import numpy as np
    from city_rating_mcp.embeddings import EmbeddingStore
    path = tmp_path / 'vectors.npz'
    def write(city='bangkok', digest='expected', model='intfloat/multilingual-e5-large'):
        np.savez(path, vectors=np.array([[1., 0.]], dtype=np.float32), slugs=np.array(['x']),
                 locales=np.array(['en']), fields=np.array(['all']), model=np.array(model),
                 city=np.array(city), source_sha256=np.array(digest))
    write()
    assert EmbeddingStore.load(path, expected_city='bangkok', source_sha256='expected').slugs[0] == 'x'
    for city, digest, model in [('tokyo', 'expected', 'intfloat/multilingual-e5-large'),
                                ('bangkok', 'stale', 'intfloat/multilingual-e5-large'),
                                ('bangkok', 'expected', 'other')]:
        write(city, digest, model)
        with pytest.raises(ValueError):
            EmbeddingStore.load(path, expected_city='bangkok', source_sha256='expected')
