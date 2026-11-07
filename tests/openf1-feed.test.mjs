import test from 'node:test';
import assert from 'node:assert/strict';
import {createOpenF1Query} from '../site/openf1-feed.js';

test('same-origin source preserves real OpenF1 rows and filters', async()=>{
  let upstreamCalls=0;
  const originalFetch=globalThis.fetch;
  const catalog={schema:'apexium-openf1-catalog-v1',
    fetchedAt:'2026-11-07T03:00:00Z',url:'https://api.openf1.org/v1/meetings',
    races:[{year:2026,meeting_key:100,session_key:101,meeting_name:'Brazil',
      country_name:'Brazil',date_start:'2026-11-01T00:00:00Z',telemetryDrivers:[1]}]};
  const race={schema:'apexium-openf1-race-v1',year:2026,url:'https://api.openf1.org/v1/',
    fetchedAt:'2026-11-07T03:00:00Z',meeting:{meeting_key:100,meeting_name:'Brazil'},
    session:{session_key:101,meeting_key:100,session_name:'Race'},
    drivers:[{driver_number:1,full_name:'Driver One'}],
    data:{laps:[{session_key:101,driver_number:1,lap_number:1,lap_duration:90}],
      pit:[],stints:[],position:[],overtakes:[],race_control:[],weather:[]},
    telemetry:{"1":{lap_number:1,rows:[{driver_number:1,date:'2026-11-01T01:00:01Z',
      speed:250,throttle:100,rpm:9000,brake:0}]}}};
  globalThis.fetch=async(url)=>{
    const path=String(url);
    if(path.endsWith('/catalog.json'))return {ok:true,json:async()=>catalog};
    if(path.endsWith('/2026/race.json'))return {ok:true,json:async()=>race};
    throw Error('Unexpected source path: '+path);
  };
  try{
    const proxy=createOpenF1Query(async()=>{upstreamCalls++;throw Error('unexpected upstream')});
    const meets=await proxy('meetings',{year:2026});
    assert.equal(meets.rows.length,1);
    assert.equal(meets.rows[0].meeting_key,100);
    assert.equal((await proxy('sessions',{meeting_key:100})).rows[0].session_key,101);
    assert.equal((await proxy('drivers',{session_key:101})).rows[0].driver_number,1);
    assert.equal((await proxy('laps',{session_key:101,driver_number:1})).rows[0].lap_duration,90);
    const tele=await proxy('car_data',{session_key:101,driver_number:1,
      date__gte:'2026-11-01T01:00:00Z',date__lte:'2026-11-01T01:00:20Z'});
    assert.equal(tele.rows.length,1);
    assert.equal(tele.metadata.sampledLap,1);
    assert.equal(upstreamCalls,0);
  }finally{globalThis.fetch=originalFetch;}
});
