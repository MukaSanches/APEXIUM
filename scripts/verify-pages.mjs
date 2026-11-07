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
  const html=await fetch(new URL('./',base),{signal:AbortSignal.timeout(15000)});
  if(!html.ok||(await html.text()).includes('404 - File not found'))throw Error('Landing page unavailable');
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
