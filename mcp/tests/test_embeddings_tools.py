"""Offline MCP tool tests using tiny synthetic vectors and station records."""
from __future__ import annotations

import json

import numpy as np
import pytest

from city_rating_mcp.data import Datamart
from city_rating_mcp.embeddings import EmbeddingStore
from city_rating_mcp.tools.search import search_stations
from city_rating_mcp.tools.semantic import find_similar, recommend, semantic_search
from city_rating_mcp.tools.station import compare_stations, get_station


@pytest.fixture
def embeddings():
    slugs = np.array(['a', 'b', 'c'] * 4)
    locales = np.array(['en'] * 6 + ['ja'] * 6)
    fields = np.array(['all'] * 3 + ['food'] * 3 + ['all'] * 3 + ['food'] * 3)
    vectors = np.array([[1, 0], [.8, .6], [0, 1]] * 4, dtype=np.float32)
    return EmbeddingStore(vectors, slugs, locales, fields, 'synthetic')


def test_embedding_slices_masks_and_aggregate(embeddings):
    query = np.array([1, 0], dtype=np.float32)
    assert [hit[0] for hit in embeddings.search(query, limit=2)] == ['a', 'b']
    assert [hit[:2] for hit in embeddings.search(query, locale='ja', field='food', slug_filter={'c'})] == [('c', 'food')]
    assert embeddings.search(query, locale='ru') == []
    assert embeddings.search(query, slug_filter=set()) == []
    np.testing.assert_array_equal(embeddings.aggregate_vector('a', 'en'), [1, 0])
    assert embeddings.aggregate_vector('missing', 'en') is None


def test_embed_query_prefix_and_normalization(embeddings, monkeypatch):
    class Model:
        def embed(self, texts):
            assert texts == ['query: quiet streets']
            return iter([[3, 4]])

    monkeypatch.setattr(embeddings, '_embedder', lambda: Model())
    np.testing.assert_allclose(embeddings.embed_query('quiet streets'), [.6, .8])


def station(slug, food, rent=100_000):
    return {'slug': slug, 'name_en': slug, 'ratings': {'food': food},
            'rent': {'1k_1ldk': rent}, 'transit_minutes': {'hub': 20}}


@pytest.fixture
def dm():
    stations = {'a': station('a', 2), 'b': station('b', 9), 'c': station('c', 5)}
    return Datamart(stations, list(stations), {})


class FakeEmbeddingStore:
    def __init__(self, hits):
        self.hits = hits
        self.limits = []

    def embed_query(self, query):
        return query

    def aggregate_vector(self, slug, locale):
        return [1, 0]

    def search(self, vector, *, locale, field, limit):
        self.limits.append(limit)
        return self.hits[:limit]


def test_search_filters_sorts_and_clamps(dm):
    result = search_stations(dm, category_mins={'food': 5}, limit=999)
    assert result['total_matches'] == result['returned'] == 2
    assert [row['slug'] for row in result['results']] == ['b', 'c']
    many = Datamart({str(i): station(str(i), 5) for i in range(205)}, [], {})
    result = search_stations(many, limit=999)
    assert (result['total_matches'], result['returned']) == (205, 200)


def test_station_hints_compare_bounds_and_missing(dm):
    dm._stations['shinagawa'] = station('shinagawa', 5)
    with pytest.raises(ValueError, match='Did you mean.*shinagawa'):
        get_station(dm, 'shina')
    for slugs in (['a'], ['a'] * 6):
        with pytest.raises(ValueError):
            compare_stations(dm, slugs)
    result = compare_stations(dm, ['a', 'missing'])
    assert [row['slug'] for row in result['profiles']] == ['a']
    assert result['missing'] == ['missing']


def test_recommend_alpha_filters_and_clamps_cosine(dm):
    es = FakeEmbeddingStore([('a', 'all', 1.4), ('b', 'all', -.2), ('c', 'all', .8)])
    structured = recommend(dm, es, query='quiet', hybrid_alpha=0)
    semantic = recommend(dm, es, query='quiet', hybrid_alpha=1)
    assert structured['results'][0]['slug'] == 'b'
    assert semantic['results'][0]['slug'] == 'a'
    assert [r['semantic_score'] for r in semantic['results']] == [1.0, .8, 0.0]
    filtered = recommend(dm, es, query='quiet', category_mins={'food': 5})
    assert filtered['total_after_filters'] == 2
    assert {r['slug'] for r in filtered['results']} == {'b', 'c'}
    with pytest.raises(ValueError, match='query is empty'):
        recommend(dm, es, query='  ')
    with pytest.raises(ValueError, match='hybrid_alpha'):
        recommend(dm, es, query='quiet', hybrid_alpha=1.1)


def test_semantic_tools_apply_documented_limit_bounds():
    stations = {str(i): station(str(i), 5) for i in range(65)}
    dm = Datamart(stations, [], {})
    es = FakeEmbeddingStore([(str(i), 'all', .5) for i in range(65)])
    assert len(semantic_search(dm, es, query='q', limit=100)['results']) == 50
    assert es.limits[-1] == 50
    assert len(find_similar(dm, es, slug='0', limit=100)['results']) == 50
    assert es.limits[-1] == 51  # includes the seed
    assert len(recommend(dm, es, query='q', limit=0)['results']) == 1
    assert len(recommend(dm, es, query='q', limit=100)['results']) == 50


def test_datamart_load_optional_files_and_description_merge(tmp_path):
    source = tmp_path / 'datamart.json'
    descriptions = tmp_path / 'descriptions.json'
    cameras = tmp_path / 'cameras.json'
    source.write_text(json.dumps({'stations': {'a': station('a', 5), 'b': station('b', 6),
                                               'c': station('c', 7)},
                                  'generation_order': ['a', 'b', 'c'], 'metadata': {'source': 'fixture'}}))
    descriptions.write_text(json.dumps({'a': {'en': {'food': 'yes'}}, 'b': {'ja': {}}, 'c': 'invalid',
                                        '_metadata': {'en': {'food': 'not a station'}}}))
    cameras.write_text(json.dumps({'_metadata': [{'id': 'ignored'}], 'a': [{'id': 'camera'}]}))
    loaded = Datamart.load(source, descriptions, cameras)
    assert loaded.get('a')['description'] == {'en': {'food': 'yes'}}
    assert 'description' not in loaded.get('b')
    assert 'description' not in loaded.get('c')
    assert loaded.get('a')['livecams'] == [{'id': 'camera'}]
    assert '_metadata' not in loaded
    assert loaded.metadata == {'source': 'fixture'}
    without_optional = Datamart.load(source, tmp_path / 'absent-desc', tmp_path / 'absent-cams')
    assert len(without_optional) == 3 and 'description' not in without_optional.get('a')
