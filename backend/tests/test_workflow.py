from app.services.ai_service import analyze
from app.services.priority_service import label_for_score

def sample(**changes):
    data={"title":"Waterlogging near school","description":"Urgent waterlogging creates an unsafe hazard outside the school after heavy rain.","location_name":"Central Avenue","latitude":12.9716,"longitude":77.5946}; data.update(changes); return data
def test_health_create_track_and_admin_flow(client):
    assert client.get('/api/health').json()=={'status':'ok'}
    created=client.post('/api/reports',json=sample()); assert created.status_code==201
    r=created.json(); cid=r['public_id']; assert r['category']=='Waterlogging' and 0<=r['priority_score']<=100 and r['priority_explanation']
    assert client.get(f'/api/reports/{cid}').json()['status']=='SUBMITTED'
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'IN_PROGRESS'}).status_code==400
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'UNDER_REVIEW'}).status_code==200
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'ASSIGNED'}).status_code==400
    assert client.patch(f'/api/admin/reports/{cid}/assignment',json={'team':'Drainage team'}).json()['assigned_team']=='Drainage team'
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'ASSIGNED'}).status_code==200
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'IN_PROGRESS'}).status_code==200
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'RESOLVED'}).status_code==400
    assert client.patch(f'/api/admin/reports/{cid}/status',json={'status':'RESOLVED','note':'Drain cleared'}).status_code==200
    assert len(client.get(f'/api/reports/{cid}/history').json())==5
def test_validation_filter_analytics_and_duplicates(client):
    assert client.post('/api/reports',json=sample(latitude=200)).status_code==422
    distant=client.post('/api/reports',json=sample(latitude=1,longitude=1,location_name='Far Away')).json()
    assert distant['public_id']
    assert client.get(f"/api/reports/{distant['public_id']}/duplicates").json()==[]
    a=client.post('/api/reports',json=sample()).json(); b=client.post('/api/reports',json=sample(title='Waterlogging near school gate')).json()
    assert client.get(f"/api/reports/{b['public_id']}/duplicates").json()
    assert client.get('/api/reports?category=unknown').status_code==400
    assert client.get('/api/reports?priority=urgent').status_code==400
    assert client.get('/api/reports?skip=0&limit=1').json()['total']==3
    assert client.get('/api/analytics/summary').json()['total']==3
    assert client.get('/api/analytics/hotspots').json()
    brief=client.post('/api/admin/action-brief').json()
    assert brief['supporting_report_count']==2 and brief['location']=='Central Avenue'
def test_unknown_and_empty_brief(client):
    assert client.get('/api/reports/CIV-UNKNOWN').status_code==404
    assert client.post('/api/admin/action-brief?category=Roads').status_code==404
    empty=client.get('/api/analytics/summary').json()
    assert empty['total']==0 and empty['resolution_rate']==0 and empty['hotspots']==[]

def test_rules_based_category_summary_and_priority_bounds():
    category,summary,score,level,explanation,factors,suggested=analyze('Streetlight is broken','The streetlight is dark and unsafe near the hospital. '+'More detail '*40)
    assert category=='Streetlights'
    assert len(summary)<=320 and summary.endswith('...')
    assert 0<=score<=100 and level in {'LOW','MEDIUM','HIGH','CRITICAL'}
    assert sum(x['score'] for x in factors.values())==score
    assert factors['Safety Risk']['score']<=30 and factors['Severity']['score']<=25
    assert 'safety risk' in explanation.lower() and suggested=='Streetlights'
    assert factors['Time Sensitivity']['score']<=10 and factors['Public Impact']['score']<=20
    assert [label_for_score(n) for n in (0,24,25,49,50,74,75,100)]==['LOW','LOW','MEDIUM','MEDIUM','HIGH','HIGH','CRITICAL','CRITICAL']

def test_transport_analytics_priority_chat_and_filters(client):
    payload=sample(title='Pothole near bus stop',description='A deep pothole on the road forces two-wheelers to swerve into traffic.',transportation_mode='Two-Wheeler / Motorcycle')
    created=client.post('/api/reports',json=payload); assert created.status_code==201
    report=created.json(); assert report['transportation_mode']=='Two-Wheeler / Motorcycle'
    assert report['priority_factors']['Safety Risk']['score']>0
    assert sum(f['score'] for f in report['priority_factors'].values())==report['priority_score']
    assert 'inferred' in report['priority_factors']['Safety Risk']['reason']
    analytics=client.get('/api/analytics/summary?transportation_mode=Two-Wheeler%20%2F%20Motorcycle').json()
    assert analytics['total']==1 and analytics['by_transportation_mode']['Two-Wheeler / Motorcycle']==1
    assert client.get('/api/reports?transportation_mode=Not%20specified').status_code==200
    assert client.get('/api/reports?date_from=2100-01-01').json()['total']==0
    assert client.get('/api/analytics/summary?date_from=2100-02-01&date_to=2000-01-01').status_code==400
    tracked=client.post('/api/chat',json={'message':f"Why was {report['public_id']} given this priority?"}).json()
    assert report['public_id'] in tracked['complaint_ids'] and str(report['priority_score']) in tracked['answer']
    modes=client.post('/api/chat',json={'message':'Which transportation modes are most affected by open complaints?'}).json()
    assert 'Two-Wheeler / Motorcycle: 1' in modes['answer']
    assert client.post('/api/reports',json=sample(transportation_mode='Jetpack')).status_code==422
    assert client.post('/api/reports',json=sample(image_ref='/uploads/not-a-real-file.jpg')).status_code==422
    explicit=client.post('/api/reports',json=sample(category='Roads and Infrastructure',title='Pothole by road',description='A pothole is damaging the road surface.')).json()
    assert explicit['category']=='Roads and Infrastructure' and explicit['category_source']=='citizen' and explicit['suggested_category']=='Roads'

def test_legacy_category_aliases_can_be_duplicate_candidates(client):
    old=client.post('/api/reports',json=sample(title='Pothole beside school entrance',description='A deep pothole by the school entrance is forcing motorcycles to swerve.',category='Roads')).json()
    new=client.post('/api/reports',json=sample(title='Pothole at school entrance',description='A deep pothole by the school entrance is forcing motorcycles to swerve.',category='Roads and Infrastructure')).json()
    matches=client.get(f"/api/reports/{new['public_id']}/duplicates").json()
    assert any(x['public_id']==old['public_id'] and x['similarity']>0 and x['explanation'] for x in matches)
    assert client.get('/api/reports?category=Roads').json()['total']==2
    assert client.get('/api/analytics/summary?category=Roads').json()['by_category']=={'Roads and Infrastructure':2}
    assert client.post('/api/admin/action-brief?category=Roads').json()['supporting_report_count']==2

def test_image_upload_validates_format_and_persists_reference(client):
    from app.services.upload_service import UPLOAD_DIR
    valid_png=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082')
    rejected=client.post('/api/uploads',files={'file':('bad.png',b'not an image','image/png')})
    assert rejected.status_code==415
    oversized=client.post('/api/uploads',files={'file':('large.png',b'\x89PNG\r\n\x1a\n'+b'x'*(5*1024*1024),'image/png')})
    assert oversized.status_code==413
    uploaded=client.post('/api/uploads',files={'file':('tiny.png',valid_png,'image/png')})
    assert uploaded.status_code==200
    ref=uploaded.json()['image_ref']
    try:
        body=sample(image_ref=ref)
        created=client.post('/api/reports',json=body)
        assert created.status_code==201 and created.json()['image_ref']==ref
        assert client.get('http://testserver'+ref).status_code==200
    finally:
        (UPLOAD_DIR/ref.rsplit('/',1)[-1]).unlink(missing_ok=True)

def test_resource_plan_and_work_orders_persist_and_validate(client):
    report=client.post('/api/reports',json=sample(category='Roads and Infrastructure')).json()
    plan=client.get(f"/api/reports/{report['public_id']}/resource-plan")
    assert plan.status_code==200
    assert plan.json()['estimated_workers']>0 and 'heuristic' in plan.json()['confidence'].lower()
    assert 'not a dispatch' in plan.json()['assumptions'].lower()
    created=client.post('/api/admin/work-orders',json={
        'report_id':report['public_id'],'title':'Inspect damaged roadway','assigned_team':'Roads team',
        'estimated_workers':2,'estimated_hours':4,'materials':['Inspection kit'],
        'assumptions':'Initial inspection only; confirm scope on site.'
    })
    assert created.status_code==201
    order=created.json(); assert order['status']=='PLANNED' and order['materials']==['Inspection kit']
    assert client.get('/api/admin/work-orders').json()[0]['id']==order['id']
    updated=client.patch(f"/api/admin/work-orders/{order['id']}",json={'status':'IN_PROGRESS','notes':'Crew scheduled'})
    assert updated.status_code==200 and updated.json()['status']=='IN_PROGRESS'
    assert client.get('/api/admin/work-orders?status=IN_PROGRESS').json()[0]['notes']=='Crew scheduled'
    assert client.patch(f"/api/admin/work-orders/{order['id']}",json={'status':'UNKNOWN'}).status_code==400
    completed=client.patch(f"/api/admin/work-orders/{order['id']}",json={'status':'COMPLETED'})
    assert completed.status_code==200
    assert client.patch(f"/api/admin/work-orders/{order['id']}",json={'status':'PLANNED'}).status_code==400
    invalid={
        'report_id':'CIV-DOESNOTEXIST','title':'Inspect unknown issue',
        'estimated_workers':2,'estimated_hours':3,
        'assumptions':'Initial inspection only; confirm scope on site.'
    }
    assert client.post('/api/admin/work-orders',json=invalid).status_code==404

def test_duplicate_review_is_explicit_persistent_and_updatable(client):
    original=client.post('/api/reports',json=sample(title='Pothole at school entrance',description='A deep pothole by the school entrance forces motorcycles to swerve.')).json()
    candidate=client.post('/api/reports',json=sample(title='Pothole beside school entrance',description='A deep pothole by the school entrance forces motorcycles to swerve.')).json()
    matches=client.get(f"/api/reports/{candidate['public_id']}/duplicates").json()
    assert any(x['public_id']==original['public_id'] for x in matches)
    path=f"/api/reports/{candidate['public_id']}/duplicate-review"
    saved=client.post(path,json={'candidate_id':original['public_id'],'decision':'CONFIRMED','note':'Same location and reported condition'})
    assert saved.status_code==200 and saved.json()['decision']=='CONFIRMED'
    assert client.get(f"/api/reports/{candidate['public_id']}/duplicate-reviews").json()[0]['candidate_id']==original['public_id']
    assert client.post(path,json={'candidate_id':original['public_id'],'decision':'DISMISSED'}).json()['decision']=='DISMISSED'
    assert client.get(f"/api/reports/{candidate['public_id']}/duplicate-reviews").json()[0]['decision']=='DISMISSED'
    assert client.post(path,json={'candidate_id':candidate['public_id'],'decision':'CONFIRMED'}).status_code==400
    assert client.post(path,json={'candidate_id':original['public_id'],'decision':'MERGE'}).status_code==422
