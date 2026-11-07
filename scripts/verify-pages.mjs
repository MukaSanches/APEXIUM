/** Check the actual published website and same-origin Jolpica snapshots. */
const base=(process.env.APEXIUM_SITE_URL||'https://mukasanches.github.io/APEXIUM/').replace(/\/?$/,'/');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function fetchJson(path){
  const url=new URL(path,base);
  const r=await fetch(url,{headers:{'Accept':'application/json'},signal:AbortSignal.timeout(15000),
    cache:'no-store'});
  if(!r.ok)throw Error(path+' HTTP '+r.status);
  return r.json();
}
async function run(){
  const check=[
    ['data/jolpica/2026/races.json',data=>
      data.schema==='apexium-jolpica-snapshot-v1'&&
      data.year===2026&&data.resource==='races'&&data.rows.length>=15],
    ['data/jolpica/2026/driverstandings.json',data=>
      data.schema==='apexium-jolpica-snapshot-v1'&&
      data.resource==='driverstandings'&&
      Array.isArray(data.rows?.[0]?.DriverStandings)&&
      data.rows[0].DriverStandings.length>0],
    ['data/jolpica/2026/constructorstandings.json',data=>
      data.schema==='apexium-jolpica-snapshot-v1'&&
      data.resource==='constructorstandings'&&
      Array.isArray(data.rows?.[0]?.ConstructorStandings)&&
      data.rows[0].ConstructorStandings.length>0]
  ];
  const html=await fetch(new URL('./',base),{
    signal:AbortSignal.timeout(15000),cache:'no-store'});
  if(!html.ok)throw Error('Landing page unavailable: HTTP '+html.status);
  const markup=await html.text();
  if(markup.includes('404 - File not found'))throw Error('Landing page missing');
  if(!markup.includes('app.js?release=20261107c'))
    throw Error('Browser-facing HTML is stale: versioned application missing');
  const match=markup.match(/<script id="apexium-preloaded" type="application\/json">([\s\S]*?)<\/script>/);
  if(!match)throw Error('Published HTML did not include real preloaded datasets');
  const bundle=JSON.parse(match[1]);
  if(bundle?.['2026']?.races?.rows?.length<15 ||
      bundle?.['2026']?.driverstandings?.rows?.[0]?.DriverStandings?.length<10){
    throw Error('Embedded homepage data is empty or incomplete');
  }
  console.log('Published HTML includes real racing snapshots and cache-busted scripts');
  const openf1=await fetchJson('data/openf1/catalog.json');
  if(openf1.schema!=='apexium-openf1-catalog-v1'||!openf1.races?.length)throw Error('OpenF1 public catalog missing');
  for(const choice of openf1.races){const d=await fetchJson('data/openf1/'+choice.year+'/race.json');if(d.schema!=='apexium-openf1-race-v1'||!d.data?.laps?.length||!Object.keys(d.telemetry||{}).length)throw Error('Incomplete OpenF1 race data for '+choice.year);console.log('Live OpenF1 dataset:',choice.year,d.meeting.meeting_name,d.data.laps.length,'laps',Object.keys(d.telemetry).length,'telemetry drivers');}
  for(const [path,validate] of check){
    const value=await fetchJson(path);
    if(!validate(value))throw Error('Invalid or incomplete published data at '+path);
    console.log('Live Pages PASS',path,'rows:',value.rows.length,'upstream:',value.url,
      'fetchedAt:',value.fetchedAt);
  }
}
for(let attempt=1;attempt<=7;attempt++){
  try{await run();console.log('APEXIUM live production verification succeeded');process.exit(0);}
  catch(err){
    console.error('Live verification attempt',attempt,err.message);
    if(attempt===7)process.exit(1);
    await pause(attempt*2500);
  }
}
