import test from 'node:test';
import assert from 'node:assert/strict';
import { getSeasonData } from '../site/feed.js';
const src='https://api.jolpi.ca/ergast/f1/2026/races.json?limit=100&offset=0';
const mock=(rows,resource='races')=>({schema:'apexium-jolpica-snapshot-v1',
 year:2026,resource,url:src,fetchedAt:'2026-11-07T02:00:00Z',rows,
 metadata:{total:String(rows.length)}});
const failRemote={jolpica:{query:async()=>{throw Error('browser blocked cross-origin API')}}};
test('calendar uses same-origin source-attributed snapshot without an API call',async()=>{
 let called='';
 const data=await getSeasonData(failRemote,'races',2026,{
  baseUrl:'https://mukasanches.github.io/APEXIUM/#overview',
  fetcher:async url=>{called=url;return {ok:true,json:async()=>mock([{raceName:'Brazilian Grand Prix',round:'21'}])};}
 });
 assert.equal(called,'https://mukasanches.github.io/APEXIUM/data/jolpica/2026/races.json');
 assert.equal(data.source,'jolpica');assert.equal(data.rows[0].round,'21');
 assert.equal(data.metadata.via,'apexium-pages-snapshot');
 assert.equal(data.cached,true);
});
test('driver standings load real-shaped nested results from snapshot',async()=>{
 const data=await getSeasonData(failRemote,'driverstandings',2026,{baseUrl:'https://mukasanches.github.io/APEXIUM/',
 fetcher:async()=>({ok:true,json:async()=>mock([{DriverStandings:[{Driver:{givenName:'Sample',familyName:'Driver'},points:'100'}]}],'driverstandings')})});
 assert.equal(data.rows[0].DriverStandings[0].points,'100');
});
test('snapshot failure falls back to upstream with no fabricated results',async()=>{
 const api={jolpica:{query:async(resource,o)=>({rows:[{season:String(o.season)}],source:'jolpica',url:src})}};
 const data=await getSeasonData(api,'races',1950,{baseUrl:'https://mukasanches.github.io/APEXIUM/',
 fetcher:async()=>({ok:false,status:404})});
 assert.deepEqual(data.rows,[{season:'1950'}]);
});
test('if neither source is accessible the error is explicit, not fake data',async()=>{
 await assert.rejects(getSeasonData(failRemote,'races',2026,{baseUrl:'https://mukasanches.github.io/APEXIUM/',
 fetcher:async()=>{throw Error('network offline')}}),/não estão disponíveis|indisponíveis/);
});
test('snapshot schema and resource are strictly validated',async()=>{
 await assert.rejects(getSeasonData(failRemote,'races',2026,{baseUrl:'https://mukasanches.github.io/APEXIUM/',
 fetcher:async()=>({ok:true,json:async()=>mock([{position:1}],'constructorstandings')})}),/Formato do snapshot/);
});
