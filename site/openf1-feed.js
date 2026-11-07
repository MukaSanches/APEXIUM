/** Same-origin, source-preserving OpenF1 historical race adapters.
 * If a session is not mirrored here, only then fall back to original API.
 */
const BASE=typeof location==='undefined'?'https://mukasanches.github.io/APEXIUM/':
  new URL('./',location.href).href;
let catalogPromise;
const racePromises=new Map();
const TRACKED=new Set(['laps','stints','pit','position','overtakes','weather','race_control',
  'drivers','sessions','meetings','car_data']);
async function json(path){
  const response=await fetch(new URL(path,BASE),{cache:'no-store'});
  if(!response.ok)throw Error('Snapshot '+path+' HTTP '+response.status);
  return response.json();
}
async function catalog(){
  if(!catalogPromise)catalogPromise=json('data/openf1/catalog.json')
    .then(x=>{if(x.schema!=='apexium-openf1-catalog-v1'||!Array.isArray(x.races))
      throw Error('Invalid OpenF1 catalog');return x;})
    .catch(error=>{catalogPromise=null;throw error;});
  return catalogPromise;
}
async function race(year){
  const key=String(year);
  if(!racePromises.has(key))racePromises.set(key,json('data/openf1/'+year+'/race.json')
    .then(x=>{if(x.schema!=='apexium-openf1-race-v1'||x.year!==Number(year)||
      !Array.isArray(x.drivers)||!Array.isArray(x.data?.laps))
      throw Error('Invalid OpenF1 snapshot');return x;})
    .catch(err=>{racePromises.delete(key);throw err;}));
  return racePromises.get(key);
}
function records(rows,original,metadata={}){
  return {rows,source:'openf1',url:original,
    fetchedAt:metadata.fetchedAt||new Date().toISOString(),cached:true,
    metadata:{via:'same-origin-historical-race',...metadata}};
}
function matchFilters(items,filters,exclude=[]){
  return items.filter(row=>Object.entries(filters).every(([key,val])=>{
    if(val==null||exclude.includes(key))return true;
    const [field,op]=key.split('__');
    if(op&&['gte','lte','gt','lt'].includes(op)){
      const a=Number(row[field]),b=Number(val);
      return Number.isFinite(a)&&Number.isFinite(b)&&
        (op==='gte'?a>=b:op==='lte'?a<=b:op==='gt'?a>b:a<b);
    }
    return String(row[field])===String(val);
  }));
}
export function createOpenF1Query(upstream){
  return async function query(endpoint,filters={},options={}){
    if(!TRACKED.has(endpoint))return upstream(endpoint,filters,options);
    try {
      const list=await catalog();
      const selected=list.races.find(r=>
        filters.session_key!=null?String(r.session_key)===String(filters.session_key):
        filters.meeting_key!=null?String(r.meeting_key)===String(filters.meeting_key):
        filters.year!=null?Number(r.year)===Number(filters.year):false);
      if(endpoint==='meetings'){
        const rows=list.races.map(r=>({
          year:r.year,meeting_key:r.meeting_key,meeting_name:r.meeting_name,
          country_name:r.country_name,date_start:r.date_start,
          location:r.meeting_name
        }));
        const found=matchFilters(rows,filters);
        return records(found,list.url,{fetchedAt:list.fetchedAt,coverage:'curated demo races'});
      }
      if(endpoint==='sessions'&&selected){
        const data=await race(selected.year);
        return records(matchFilters([data.session],filters,['meeting_key']),data.url,
          {fetchedAt:data.fetchedAt});
      }
      if(selected){
        const data=await race(selected.year);
        if(endpoint==='drivers')return records(
          matchFilters(data.drivers,filters,['session_key']),data.url,
          {fetchedAt:data.fetchedAt});
        if(endpoint==='car_data'){
          const sample=data.telemetry?.[String(filters.driver_number)];
          if(!sample)return records([],data.url,{coverage:'No sampled telemetry for driver'});
          let items=sample.rows;
          if(filters.date__gte||filters.date__lte){
            const start=filters.date__gte?Date.parse(filters.date__gte):-Infinity;
            const end=filters.date__lte?Date.parse(filters.date__lte):Infinity;
            items=items.filter(i=>Date.parse(i.date)>=start&&Date.parse(i.date)<=end);
          }
          return records(items,data.url,{fetchedAt:data.fetchedAt,
            sampledLap:sample.lap_number,coverage:'One real sampled lap per driver'});
        }
        if(Array.isArray(data.data[endpoint]))
          return records(matchFilters(data.data[endpoint],filters,['session_key']),
            data.url,{fetchedAt:data.fetchedAt,
              coverage:'Historical sample - '+data.meeting.meeting_name});
      }
    }catch(err){ /* Fall back to provider without fabricating sample data. */ }
    return upstream(endpoint,filters,options);
  };
}
export async function sampledTelemetry(year,meetingKey,driverNumber){
  const list=await catalog();
  const selected=list.races.find(r=>r.year===Number(year)&&
    String(r.meeting_key)===String(meetingKey));
  if(!selected)return null;
  const data=await race(selected.year);
  return data.telemetry?.[String(driverNumber)]||null;
}
export async function sampledDriverNumbers(year,meetingKey){
  const list=await catalog();
  const selected=list.races.find(r=>r.year===Number(year)&&
    String(r.meeting_key)===String(meetingKey));
  if(!selected)return null;
  const data=await race(selected.year);
  return Object.keys(data.telemetry||{}).map(Number);
}
