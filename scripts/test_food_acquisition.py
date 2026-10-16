"""Offline target acquisition contracts: no provider or credential access."""
import io
import json
import struct
import sys
import types
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest

from food_pilot import bounded
from food_pilot.bounded import Budget, ReplayBudget, AcquisitionStopped, RequestRejected
from food_pilot.hotpepper import acquire_station, page_projection, BadCoordinates, PaginationChanged, confirmation_checkpoint, acquire_sites
from food_pilot.overture import range_projection, wkb_point, selected_groups, is_food, extract
from food_pilot.run import phase_sites, primary_gate, checked_gate, validate_result_windows

STATION={'slug':'test','lat':35.7,'lng':139.7}


def limits():
    return {'attempts':6,'response_bytes':16384,'response_body_bytes':65536,'retained_bytes':1024**2,
            'wall_seconds':900,'socket_seconds':20,'concurrency':1,'minimum_request_interval_seconds':0,
            'maximum_attempts_per_page':2,'successful_pages':4,'pages_per_station':3,'row_groups':10}


class Response(io.BytesIO):
    status=200
    headers={}


def hp_page(total=1,start=1,shops=None):
    shops=[{'id':'venue','lat':'35.7','lng':'139.7','name':'synthetic','genre':{'code':'G001'}}] if shops is None else shops
    return json.dumps({'results':{'results_available':total,'results_start':start,'results_returned':str(len(shops)),'shop':shops}}).encode()


def test_hp_complete_one_km_then_800m_filter_and_offline_replay(tmp_path):
    shops=[{'id':str(i),'lat':'35.7','lng':'139.7'} for i in range(100)]
    # ~889m north: fetched in1km universe, excluded from800m.
    last={'id':'outside','lat':'35.708','lng':'139.7'}
    pages=[hp_page(101,1,shops),hp_page(101,101,[last])]
    def open_page(*args,**kwargs): return Response(pages.pop(0))
    with Budget(tmp_path,limits(),'manifest',opener=open_page) as budget:
        result=acquire_station(STATION,budget,'SYNTHETIC_KEY')
    assert result['status']=='complete_positive'
    assert result['unique_fetched']==101 and result['count_800m']==100 and result['outside_800m']==1
    replay=acquire_station(STATION,ReplayBudget(tmp_path),'OFFLINE_NOT_SENT')
    assert replay==result
    assert 'SYNTHETIC_KEY' not in (tmp_path/'ledger.json').read_text()


@pytest.mark.parametrize('bad', ['missing_page','changing_total','duplicate'])
def test_hp_partial_pagination_never_becomes_zero(tmp_path,bad):
    shops=[{'id':str(i),'lat':'35.7','lng':'139.7'} for i in range(100)]
    second=[] if bad=='missing_page' else [{'id':'0' if bad=='duplicate' else 'last','lat':'35.7','lng':'139.7'}]
    pages=[hp_page(101,1,shops),hp_page(102 if bad=='changing_total' else 101,101,second)]
    with Budget(tmp_path,limits(),'manifest',opener=lambda *a,**k:Response(pages.pop(0))) as budget:
        with pytest.raises(PaginationChanged): acquire_station(STATION,budget,'fake')


def test_bad_coordinates_keep_explicit_state_and_stop_remaining_sites(tmp_path):
    raw=hp_page(1,1,[{'id':'bad','lat':None,'lng':'139.7'}])
    with Budget(tmp_path,limits(),'manifest',opener=lambda *a,**k:Response(raw)) as budget:
        result=acquire_sites([STATION,{**STATION,'slug':'later'}],budget,'fake')
    assert result['status']=='incomplete'
    assert [r['status'] for r in result['stations']]==['bad_coordinates','missing']
    assert all(r['count_800m'] is None for r in result['stations'])


@pytest.mark.parametrize('total,shops,status',[(0,[],'complete_provider_zero'),(1,[{'id':'outside','lat':'35.708','lng':'139.7'}],'complete_800m_zero')])
def test_distinct_complete_zero_states(tmp_path,total,shops,status):
    with Budget(tmp_path,limits(),'manifest',opener=lambda *a,**k:Response(hp_page(total,1,shops))) as budget:
        assert acquire_station(STATION,budget,'fake')['status']==status


def test_budget_pending_interrupt_charged_on_resume_and_replay(tmp_path,monkeypatch):
    waits=[]
    monkeypatch.setattr(bounded.time,'sleep',lambda seconds:waits.append(seconds))
    def interrupted(*args,**kwargs):
        on_disk=json.loads((tmp_path/'ledger.json').read_text())
        assert on_disk['attempts'][0]['status']=='pending' and on_disk['charged_bytes']==16384
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        with Budget(tmp_path,limits(),'manifest',opener=interrupted) as budget:
            budget.fetch('page1',object(),lambda raw,r:{},kind='page')
    with Budget(tmp_path,limits(),'manifest',resume=True,opener=lambda *a,**k:Response(b'{}')) as budget:
        assert budget.fetch('page1',object(),lambda raw,r:json.loads(raw),kind='page')=={}
        assert budget.ledger['charged_bytes']==16386
        assert len(budget.ledger['attempts'])==2
    assert waits==[2]
    assert ReplayBudget(tmp_path).fetch('page1',object(),None)=={}
    with pytest.raises(AcquisitionStopped,match='no_reset'): Budget(tmp_path,limits(),'manifest')


@pytest.mark.parametrize('code', [401, 403, 429])
def test_terminal_http_failure_cannot_be_retried_after_resume(tmp_path, code):
    calls=[]
    def reject(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError('https://redacted.invalid', code, 'rejected', {}, None)
    with pytest.raises(RequestRejected):
        with Budget(tmp_path, limits(), 'manifest', opener=reject) as budget:
            budget.fetch('page-terminal', object(), lambda raw, response: {}, kind='page')
    ledger=json.loads((tmp_path/'ledger.json').read_text())
    assert ledger['attempts'][0]['retry_disposition']=='terminal'
    with pytest.raises(RequestRejected):
        with Budget(tmp_path, limits(), 'manifest', resume=True,
                    opener=lambda *a, **k: calls.append(2)) as budget:
            budget.fetch('page-terminal', object(), lambda raw, response: {}, kind='page')
    assert calls==[1]


@pytest.mark.parametrize('failure', ['projection', 'object_identity'])
def test_terminal_projection_or_identity_failure_cannot_be_retried_after_resume(tmp_path, failure):
    calls=[]
    def project(raw, response):
        raise ValueError(failure)
    def open_once(*args, **kwargs):
        calls.append(1)
        return Response(b'bad')
    with pytest.raises(RequestRejected):
        with Budget(tmp_path, limits(), 'manifest', opener=open_once) as budget:
            budget.fetch('range-terminal', object(), project)
    assert json.loads((tmp_path/'ledger.json').read_text())['attempts'][0]['retry_disposition']=='terminal'
    with pytest.raises(RequestRejected):
        with Budget(tmp_path, limits(), 'manifest', resume=True,
                    opener=lambda *a, **k: calls.append(2)) as budget:
            budget.fetch('range-terminal', object(), project)
    assert calls==[1]


def test_transient_failure_and_interrupted_attempt_remain_resumable(tmp_path, monkeypatch):
    sleeps=[]
    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps)==1:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bounded.time, 'sleep', sleep)
    calls=[]
    def transient(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError('https://redacted.invalid', 503, 'busy', {}, None)
    with pytest.raises(KeyboardInterrupt):
        with Budget(tmp_path, limits(), 'manifest', opener=transient) as budget:
            budget.fetch('page-transient', object(), lambda raw, response: {}, kind='page')
    attempt=json.loads((tmp_path/'ledger.json').read_text())['attempts'][0]
    assert attempt['retry_disposition']=='transient'
    monkeypatch.setattr(bounded.time, 'sleep', lambda seconds: sleeps.append(seconds))
    with Budget(tmp_path, limits(), 'manifest', resume=True,
                opener=lambda *a, **k: (calls.append(2) or Response(b'{}'))) as budget:
        assert budget.fetch('page-transient', object(), lambda raw, response: json.loads(raw), kind='page')=={}
    assert calls==[1, 2]
    assert len(json.loads((tmp_path/'ledger.json').read_text())['attempts'])==2


def test_budget_expiry_during_persistence_blocks_socket(tmp_path,monkeypatch):
    clock=[100.0]
    monkeypatch.setattr(bounded.time,'monotonic',lambda:clock[0])
    calls=[]
    with pytest.raises(AcquisitionStopped):
        with Budget(tmp_path,limits(),'manifest',opener=lambda *a,**k:calls.append(1)) as budget:
            original=budget.persist
            def slow():
                original()
                clock[0]=1001.0
            budget.persist=slow
            budget.fetch('p',object(),lambda raw,r:{},kind='page')
    assert calls==[]


def test_absolute_source_deadline_checked_during_request_and_completion(tmp_path, monkeypatch):
    now=[datetime(2026, 10, 21, 23, 59, 59, tzinfo=timezone.utc)]
    real_datetime=bounded.datetime
    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0].replace(tzinfo=None)
    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    calls=[]
    def crosses_cutoff(*args, **kwargs):
        calls.append(1)
        now[0]=datetime(2026,10,22,tzinfo=timezone.utc)
        return Response(b'{}')
    with pytest.raises(AcquisitionStopped):
        with Budget(tmp_path, limits(), 'manifest', opener=crosses_cutoff,
                    absolute_deadline='2026-10-22T00:00:00Z') as budget:
            budget.fetch('page-cutoff', object(), lambda raw, response: json.loads(raw), kind='page')
    assert calls==[1]
    assert json.loads((tmp_path/'ledger.json').read_text())['attempts'][0]['status']=='failed'


def test_expired_absolute_cutoff_blocks_request_after_phase_start(tmp_path, monkeypatch):
    now=[datetime(2026,10,22,tzinfo=timezone.utc)]
    real_datetime=bounded.datetime
    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0].replace(tzinfo=None)
    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    calls=[]
    with pytest.raises(AcquisitionStopped):
        with Budget(tmp_path, limits(), 'manifest', opener=lambda *a, **k: calls.append(1),
                    absolute_deadline='2026-10-22T00:00:00Z') as budget:
            budget.fetch('page-after-cutoff', object(), lambda raw, response: {}, kind='page')
    assert calls==[]


def test_confirmation_window_checked_for_each_request_and_completion(tmp_path, monkeypatch):
    now=[datetime(2026,10,16,12,tzinfo=timezone.utc)]
    real_datetime=bounded.datetime
    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0].replace(tzinfo=None)
    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    calls=[]
    def crosses_window(*args, **kwargs):
        calls.append(1)
        now[0]=datetime(2026,10,19,12,tzinfo=timezone.utc)
        return Response(b'{}')
    with pytest.raises(AcquisitionStopped):
        with Budget(tmp_path, limits(), 'manifest', opener=crosses_window,
                    identity_windows={'hp:test:':('2026-10-16T12:00:00Z','2026-10-19T12:00:00Z')},
                    completion_window=('2026-10-16T12:00:00Z','2026-10-19T12:00:00Z')) as budget:
            budget.fetch('hp:test:1:hash', object(), lambda raw, response: json.loads(raw), kind='page')
    assert calls==[1]
    with Budget(tmp_path/'completion', limits(), 'manifest',
                completion_window=('2026-10-16T12:00:00Z','2026-10-19T12:00:00Z')) as budget:
        now[0]=datetime(2026,10,19,12,tzinfo=timezone.utc)
        with pytest.raises(AcquisitionStopped, match='confirmation_completion'):
            budget.check_completion()


def test_confirmation_result_timestamp_cannot_escape_candidate_window():
    windows={'hp:test:':(datetime(2026,10,16,12,tzinfo=timezone.utc),datetime(2026,10,19,12,tzinfo=timezone.utc))}
    result={'stations':[{'slug':'test','status':'complete_800m_zero','finished_at':'2026-10-19T12:00:00+00:00',
                         'pages':[{'received_at':'2026-10-18T12:00:00+00:00'}]}]}
    with pytest.raises(AcquisitionStopped, match='confirmation_result_outside'):
        validate_result_windows(result,windows)


def test_confirmation_requires_real_window_and_never_promotes_first_zero():
    stamp=datetime(2026,10,16,tzinfo=timezone.utc)
    prior={'stations':[{'slug':'test','status':'complete_provider_zero','finished_at':stamp.isoformat()}]}
    checkpoint=confirmation_checkpoint(prior)
    assert checkpoint['status']=='pending_real_time'
    manifest={'core':{'stations':[]},'challenge':{'order':[STATION]}}
    for hours in (0,23,73):
        with pytest.raises(AcquisitionStopped,match='real_24_72'):
            phase_sites(manifest,'hp_confirmation',prior,stamp+timedelta(hours=hours))
    assert phase_sites(manifest,'hp_confirmation',prior,stamp+timedelta(hours=25))==[STATION]


def test_holdout_and_execution_receipts_are_bound_to_manifest(tmp_path):
    receipt=tmp_path/'receipt.json'
    receipt.write_text(json.dumps({'manifest_sha256':'wrong','allowed_phases':['hp_holdout']}))
    with pytest.raises(AcquisitionStopped):checked_gate(receipt,'correct','hp_holdout')
    receipt.write_text(json.dumps({'manifest_sha256':'correct','code_sha256':{},'development_complete':False}))
    with pytest.raises(AcquisitionStopped):primary_gate(receipt,'correct',{'code_sha256':{},'primary_comparison':'raw'})


def test_range_contract_rejects_wrong_bytes_identity_and_whole_objects():
    response=Response(b'')
    response.status=206;response.headers={'Content-Range':'bytes 10-13/100','ETag':'"fixed"'}
    project=range_projection(10,13,etag='"fixed"',size=100)
    assert project(b'abcd',response)['size']==100
    with pytest.raises(ValueError):project(b'abc',response)
    response.headers['ETag']='"changed"'
    with pytest.raises(ValueError):project(b'abcd',response)
    response.status=200
    with pytest.raises(ValueError):project(b'abcd',response)


def test_geometry_and_rowgroup_selection_fail_closed():
    raw=struct.pack('<BIdd',1,1,139.7,35.7)
    assert wkb_point(raw)=={'lat':35.7,'lng':139.7}
    for bad in (b'',struct.pack('<BIdd',1,2,139.7,35.7),struct.pack('<BIdd',1,1,float('nan'),35.7)):
        with pytest.raises(ValueError):wkb_point(bad)
    item={'groups':[{'index':0,'bounds':[None]*4},{'index':1,'bounds':[139.699,35.699,139.701,35.701]},
                    {'index':2,'bounds':[140,36,141,37]}]}
    assert selected_groups(item,[STATION])==[0,1]


def test_extract_rejects_duplicate_provider_id_at_different_normalized_points(monkeypatch):
    def wkb(lat, lng):
        return struct.pack('<BIdd', 1, 1, lng, lat)
    rows=[{'id':'same','geometry':wkb(35.7,139.7),'bbox':None,'confidence':0.9,
           'operating_status':'open','taxonomy':{'hierarchy':['food_and_drink','restaurant']},
           'names':None,'addresses':None,'websites':None,'phones':None,'basic_category':None,'sources':None},
          {'id':'same','geometry':wkb(35.72,139.7),'bbox':None,'confidence':0.9,
           'operating_status':'open','taxonomy':{'hierarchy':['food_and_drink','restaurant']},
           'names':None,'addresses':None,'websites':None,'phones':None,'basic_category':None,'sources':None}]
    class Table:
        num_rows=2
        def to_pylist(self): return rows
    class ParquetFile:
        def __init__(self, *args, **kwargs): pass
        def read_row_group(self, *args, **kwargs): return Table()
    pyarrow=types.ModuleType('pyarrow'); pyarrow.__path__=[]
    parquet=types.ModuleType('pyarrow.parquet'); parquet.ParquetFile=ParquetFile
    monkeypatch.setitem(sys.modules, 'pyarrow', pyarrow)
    monkeypatch.setitem(sys.modules, 'pyarrow.parquet', parquet)
    stations=[{'slug':'a','lat':35.7,'lng':139.7},{'slug':'b','lat':35.72,'lng':139.7}]
    metadata={
        'complete':True,
        'release':'r',
        'objects':[{
            'url':'https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/r/p.parquet',
            'groups':[{'index':0,'rows':2,'bounds':[None]*4}],
            'footer_b64':'',
        }],
    }
    manifest={'overture':{'release':'r','objects':[metadata['objects'][0]['url']],
                'confidence_min':0.6,'operating_status_included':['open'],'food':{'hierarchy_prefix':'food_and_drink',
                'second_level':['restaurant'],'any_hierarchy_level':[]}}}
    class FakeBudget:
        def group(self, identity): pass
        def remaining(self): pass
    with pytest.raises(ValueError, match='conflicting_provider_identity'):
        extract(manifest,stations,metadata,FakeBudget())


def test_frozen_food_taxonomy_does_not_substitute_nightlife():
    contract={'hierarchy_prefix':'food_and_drink','second_level':['restaurant','casual_eatery','non_alcoholic_beverage_venue'],
              'any_hierarchy_level':['bakery','dessert_shop','food_court','food_truck_stand']}
    assert is_food(['food_and_drink','restaurant'],contract)
    assert is_food(['other','bakery'],contract)
    assert not is_food(['food_and_drink','alcoholic_beverage_venue'],contract)
