import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import * as a from '../site/analytics.js';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const laps=[
  {driver_number:44,lap_number:1,session_key:1,lap_duration:93,duration_sector_1:31,duration_sector_2:30,duration_sector_3:32},
  {driver_number:44,lap_number:2,session_key:1,lap_duration:91,duration_sector_1:29,duration_sector_2:32,duration_sector_3:30},
  {driver_number:44,lap_number:3,session_key:1,lap_duration:92,duration_sector_1:30,duration_sector_2:31,duration_sector_3:31},
  {driver_number:44,lap_number:4,session_key:1,lap_duration:90,duration_sector_1:30,duration_sector_2:30,duration_sector_3:30},
  {driver_number:1,lap_number:1,session_key:1,lap_duration:92,duration_sector_1:30,duration_sector_2:30,duration_sector_3:32},
  {driver_number:1,lap_number:2,session_key:1,lap_duration:90,duration_sector_1:29,duration_sector_2:30,duration_sector_3:31},
  {driver_number:1,lap_number:3,session_key:1,lap_duration:91,duration_sector_1:30,duration_sector_2:30,duration_sector_3:31},
  {driver_number:1,lap_number:4,session_key:1,lap_duration:89,duration_sector_1:29,duration_sector_2:29,duration_sector_3:31},
];
const pits=[{driver_number:44,lap_number:2,lane_duration:22,stop_duration:2.4},{driver_number:1,lap_number:2,lane_duration:24,stop_duration:2.7}];
const positions=[{driver_number:44,date:'2025-03-01T00:00:00Z',position:8},{driver_number:44,date:'2025-03-01T00:01:00Z',position:4},{driver_number:44,date:'2025-03-01T00:02:00Z',position:4}];
const stints=[{driver_number:44,stint_number:1,lap_start:1,lap_end:2,compound:'SOFT'},{driver_number:44,stint_number:2,lap_start:3,lap_end:4,compound:'HARD'}];
const car=[{driver_number:44,speed:100,throttle:100,brake:0,rpm:7000,drs:12},{driver_number:44,speed:150,throttle:50,brake:100,rpm:10000,drs:8}];
const overtakes=[{overtaking_driver_number:44},{overtaking_driver_number:44}];
const weather=[{air_temperature:20,track_temperature:30,rainfall:0},{air_temperature:22,track_temperature:32,rainfall:1}];
const rc=[{category:'Flag',flag:'YELLOW'},{category:'Flag',flag:'GREEN'}];
const datasets={laps,pit:pits,position:positions,stints,overtakes,car_data:car,weather,race_control:rc};
const num=(obj,key)=>obj[key];

test('Exactly 20 distinct analytic tools, all executable on offline fixtures',()=>{
  assert.equal(a.ANALYSES.length,20);
  assert.equal(new Set(a.ANALYSES.map(x=>x.id)).size,20);
  for(const tool of a.ANALYSES){
    assert.equal(typeof tool.fn,'function',tool.id);
    assert.ok(tool.name&&tool.limit&&tool.desc,tool.id);
    const data=tool.sources.map(src=>datasets[src]);
    assert.ok(data.every(Boolean),tool.id);
    const result=tool.id==='lapDeltas'?tool.fn(data[0],44,1):tool.id==='positionTrajectory'?tool.fn(data[0],44):tool.fn(...data);
    assert.ok(result !== undefined,tool.id);
  }
});
test('Pace is descriptive and ordered by actual sample median',()=>{
  assert.equal(a.racePace(laps)[0].driver_number,1);
  assert.equal(a.racePace(laps)[0].best_seconds,89);
  assert.throws(()=>a.racePace(laps,0));
});
test('Pit summary separates stationary from lane time',()=>{
  const row=a.pitSummary(pits).find(x=>x.driver_number===44);
  assert.equal(row.stationary_seconds_total,2.4);
  assert.equal(row.lane_seconds_total,22);
});
test('Positions use first/last observed samples, no interpolation',()=>{
  assert.equal(a.positionChanges(positions)[0].net_gain,4);
  assert.equal(a.positionTrajectory(positions,44).length,2);
});
test('Stint summary and ordered compound strategy',()=>{
  assert.deepEqual(a.stintSummary(stints).map(x=>x.laps),[2,2]);
  assert.deepEqual(a.stintStrategies(stints)[0].compounds,['SOFT','HARD']);
});
test('Overtake counts reflect reported swaps, including non-track swaps',()=>{
  assert.equal(a.overtakingCounts(overtakes)[0].recorded_position_swaps,2);
});
test('Lap quality detects duplicate keys and invalid laps',()=>{
  const report=a.lapQuality([laps[0],{...laps[0],lap_duration:-1}]);
  assert.equal(report.duplicate_driver_lap_session,1);
  assert.equal(report.invalid_lap_duration,1);
});
test('Fastest and theoretical best sector sum are distinct',()=>{
  assert.equal(a.fastestLaps(laps).find(x=>x.driver_number===44).lap_seconds,90);
  const ideal=a.idealLaps(laps).find(x=>x.driver_number===44);
  assert.equal(ideal.ideal_seconds,89);
  assert.equal(ideal.best_recorded_seconds,90);
});
test('Sector median is measured without normalization',()=>{
  assert.equal(a.sectorPace(laps).find(x=>x.driver_number===44).sector_1_median_seconds,30);
});
test('Linear trend computes known slope',()=>{
  const input=[1,2,3,4,5].map(i=>({driver_number:1,lap_number:i,lap_duration:100+i}));
  assert.equal(a.lapTrends(input)[0].slope_seconds_per_lap,1);
  assert.throws(()=>a.lapTrends([],1));
});
test('Compound pace maps lap numbers exclusively to one stint',()=>{
  assert.equal(a.compoundPace(laps,stints).length,2);
});
test('Histogram counts pit-stop lap peaks',()=>{
  assert.equal(a.pitWindowHistogram([...pits,{...pits[0]}])[0].pit_entries,3);
});
test('Speed max and sample mean',()=>{
  assert.equal(a.speedSummary(car)[0].maximum_kmh,150);
  assert.equal(a.speedSummary(car)[0].mean_kmh,125);
});
test('Brake and throttle sample fractions',()=>{
  const r=a.throttleBrakeSummary(car)[0];
  assert.equal(r.full_throttle_sample_pct,50);
  assert.equal(r.brake_engaged_sample_pct,50);
});
test('DRS counts code frequencies without inferring physical flap state',()=>{
  assert.equal(a.drsCodeSummary(car)[0].code_10_12_14_pct,50);
});
test('Weather values use arithmetic sample means',()=>{
  assert.equal(a.weatherSummary(weather).mean_track_temperature,31);
  assert.equal(a.weatherSummary(weather).rainfall_reported_samples,1);
});
test('Race-control summaries count messages, not incidents',()=>{
  assert.equal(a.raceControlSummary(rc).by_category.Flag,2);
});
test('Lap delta is positive when A slower than B',()=>{
  const d=a.lapDeltas(laps,44,1);
  assert.equal(d[0].delta_a_minus_b_seconds,1);
  assert.equal(d.length,4);
});
test('No invented rows with null or missing lap times',()=>{
  assert.deepEqual(a.fastestLaps([{driver_number:44,lap_duration:null}]),[]);
  assert.deepEqual(a.racePace([{driver_number:44,lap_duration:-1}]),[]);
});
test('Responsive app has required screens, real source links and PWA manifest',async()=>{
  const html=await readFile(resolve(root,'site/index.html'),'utf8');
  const css=await readFile(resolve(root,'site/styles.css'),'utf8');
  const manifest=JSON.parse(await readFile(resolve(root,'site/manifest.webmanifest'),'utf8'));
  for(const id of ['view-overview','view-calendar','view-championship','view-lab','view-telemetry','view-explorer','view-about','run-analysis','run-telemetry','run-explorer'])assert.ok(html.includes(`id="${id}"`),id);
  assert.ok(html.includes('https://openf1.org/docs/')&&html.includes('https://api.jolpi.ca/docs/'));
  assert.ok(css.includes('@media(max-width:740px)'));
  assert.equal(manifest.display,'standalone');
  assert.ok(manifest.icons.some(x=>x.sizes==='512x512'));
});
