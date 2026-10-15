"""Offline target acquisition contracts: no provider or credential access."""
import io
import json
import struct
from datetime import datetime, timedelta, timezone

import pytest

from food_pilot import bounded
from food_pilot.bounded import Budget, ReplayBudget, AcquisitionStopped, RequestRejected
from food_pilot.hotpepper import acquire_station, page_projection, BadCoordinates, PaginationChanged, confirmation_checkpoint, acquire_sites
from food_pilot.overture import range_projection, wkb_point, selected_groups, is_food
from food_pilot.run import phase_sites, primary_gate, checked_gate

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


def test_frozen_food_taxonomy_does_not_substitute_nightlife():
    contract={'hierarchy_prefix':'food_and_drink','second_level':['restaurant','casual_eatery','non_alcoholic_beverage_venue'],
              'any_hierarchy_level':['bakery','dessert_shop','food_court','food_truck_stand']}
    assert is_food(['food_and_drink','restaurant'],contract)
    assert is_food(['other','bakery'],contract)
    assert not is_food(['food_and_drink','alcoholic_beverage_venue'],contract)
