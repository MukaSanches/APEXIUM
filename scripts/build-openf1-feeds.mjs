/** Generate real, bounded race samples for no-code tools on static GitHub Pages.
 * Strictly non-commercial; respect OpenF1 limits and source conditions.
 */
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const out=join(root,'dist/site/data/openf1');
const now=Date.now();
const years=[Number(process.env.APEXIUM_CURRENT_YEAR||new Date().getUTCFullYear()),2025];
const resources=['laps','stints','pit','position','overtakes','weather','race_control'];
const pause=(n)=>new Promise(r=>setTimeout(r,n));
let nextRequestAt=0;
let calls=0;
const recent=[];
async function awaitQuota(){const now=Date.now();while(recent.length&&recent[0]<now-60000)recent.shift();if(recent.length>=26){await pause(Math.max(1000,60050-(now-recent[0])));return awaitQuota();}recent.push(Date.now());}
async function api(resource,filters){
  const params=new URLSearchParams();
  for(const [k,v] of Object.entries(filters)){if(v!=null)params.append(k,String(v));}
  const url='https://api.openf1.org/v1/'+resource+'?'+params;
  let error;
  for(let i=0;i<3;i++){
    const remaining=nextRequestAt-Date.now();
    if(remaining>0)await pause(remaining);
    nextRequestAt=Date.now()+700; // <= 1.5 requests/s
    await awaitQuota();
    calls++;
    try{
      const response=await fetch(url,{headers:{
        'Accept':'application/json',
        'User-Agent':'APEXIUM-Studio/1.4 (+https://github.com/MukaSanches/APEXIUM)'
      },signal:AbortSignal.timeout(20000)});
      if(!response.ok){
        error=new Error(resource+' HTTP '+response.status+' at '+url+' '+(await response.text()).slice(0,180));
        if(![429,500,502,503,504].includes(response.status))break;
        await pause(response.status===429?25000:2500*(i+1));
        continue;
      }
      const json=await response.json();
      if(!Array.isArray(json))throw Error('Bad OpenF1 JSON structure for '+resource);
      return {rows:json,url,fetchedAt:new Date().toISOString(),source:'openf1'};
    }catch(exc){error=exc;await pause(2000*(i+1));}
  }
  throw error||new Error('OpenF1 unavailable: '+resource);
}
async function write(name,data){
  const file=join(out,name);
  await mkdir(join(file,'..'),{recursive:true});
  await writeFile(file,JSON.stringify(data),'utf8');
}
const chosen=[];
for(const year of [...new Set(years)]){
  if(year<2023)continue;
  const [meetings,sessions]=await Promise.all([
    api('meetings',{year}),api('sessions',{year})
  ]);
  const options=sessions.rows.filter(s=>s.session_name==='Race'&&
    Date.parse(s.date_end||s.date_start)<now-60*60*1000&&
    s.meeting_key&&s.session_key&&
    meetings.rows.some(m=>m.meeting_key===s.meeting_key));
  options.sort((a,b)=>Date.parse(b.date_start)-Date.parse(a.date_start));
  if(!options.length){console.warn('No completed races for',year);continue;}
  const selected=options[0];
  const meeting=meetings.rows.find(m=>m.meeting_key===selected.meeting_key);
  console.log('Selected completed OpenF1 race',year,meeting.meeting_name,
    'session',selected.session_key);
  const drivers=await api('drivers',{session_key:selected.session_key});
  const data={};
  const missing=[];
  for(const resource of resources){
    try{const result=await api(resource,{session_key:selected.session_key});data[resource]=result.rows;
      console.log('  OpenF1',resource,result.rows.length);}
    catch(err){console.error('  Missing',resource,String(err));data[resource]=[];missing.push(resource);}
  }
  if(data.laps.length<50||drivers.rows.length<10){
    throw Error('No critical real lap/driver data for '+year);
  }
  // One measured lap for each of four explicitly available drivers. This is a
  // demo of telemetry, not whole-session telemetry or a live broadcaster.
  const available=drivers.rows
    .map(d=>d.driver_number).filter(Number.isInteger).sort((a,b)=>a-b);
  const preferred=[1,4,16,44,55,81,63,11];
  const sampled=[...new Set([...preferred.filter(x=>available.includes(x)),...available])].slice(0,4);
  const telemetry={};
  for(const driver of sampled){
    const lap=data.laps.find(l=>l.driver_number===driver&&l.date_start&&
      Number(l.lap_duration)>30&&Number(l.lap_duration)<600&&!l.is_pit_out_lap);
    if(!lap)continue;
    const start=new Date(lap.date_start);
    if(!Number.isFinite(start.getTime()))continue;
    const end=new Date(start.getTime()+Number(lap.lap_duration)*1000);
    try{
      let measured;
      let coverage='Complete time-window sample';
      try{
        measured=await api('car_data',{
          session_key:selected.session_key,driver_number:driver,
          'date>':new Date(start.getTime()-1000).toISOString(),'date<':new Date(end.getTime()+1000).toISOString()
        });
      }catch(dateError){
        console.warn('  Range query returned:',String(dateError).slice(0,190));
        const speedSample=await api('car_data',{
          session_key:selected.session_key,driver_number:driver,'speed>':275
        });
        const rows=speedSample.rows.filter(r=>Date.parse(r.date)>=start.getTime()&&
          Date.parse(r.date)<=end.getTime());
        measured={...speedSample,rows};
        coverage='Speed-filtered telemetry (speed >=275 km/h); not a complete lap';
        console.log('  Filtered car_data rows in selected lap:',rows.length);
      }
      if(measured.rows.length>=12){
        telemetry[String(driver)]={lap_number:lap.lap_number,
          rows:measured.rows,lap_duration:lap.lap_duration,coverage};
        console.log('  Telemetry',driver,measured.rows.length);
      }
    }catch(err){console.error('  Telemetry unavailable',driver,String(err));}
  }
  if(!Object.keys(telemetry).length)console.warn('No real telemetry sampled for',year,'(do not fabricate)');
  const result={
    schema:'apexium-openf1-race-v1',
    source:'openf1',url:'https://api.openf1.org/v1/',
    fetchedAt:new Date().toISOString(),
    year,meeting,session:selected,drivers:drivers.rows,data,telemetry,
    coverage:{kind:'sampled-historical-grand-prix',supportedResources:resources,
      sampledDriverNumbers:Object.keys(telemetry).map(Number),missing},
    attribution:'OpenF1: https://openf1.org/docs/'
  };
  await write(year+'/race.json',result);
  chosen.push({year,meeting_key:meeting.meeting_key,session_key:selected.session_key,
    meeting_name:meeting.meeting_name,country_name:meeting.country_name,
    date_start:meeting.date_start,telemetryDrivers:Object.keys(telemetry).map(Number)});
}
if(chosen.length<1)throw Error('No valid real race feed produced');
await write('catalog.json',{schema:'apexium-openf1-catalog-v1',
  fetchedAt:new Date().toISOString(),source:'openf1',
  url:'https://api.openf1.org/v1/meetings',races:chosen});
console.log('OpenF1 feed complete:',chosen.length,'historical races,',calls,'requests');
