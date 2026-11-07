/** Prepare non-commercial Jolpica CC BY-NC-SA 4.0 data on an Actions server. */
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const out=join(root,'dist','site','data','jolpica');
const current=Number(process.env.APEXIUM_CURRENT_YEAR||new Date().getUTCFullYear());
const seasons=[...new Set([current,current-1,current-2,current-3])]
  .filter(year=>year>=1950&&year<=2100);
const resources=['races','driverstandings','constructorstandings'];
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const stamp=new Date().toISOString();
const failures=[];
let successes=0;

async function snapshot(year,resource){
  const url='https://api.jolpi.ca/ergast/f1/'+year+'/'+resource+'.json?limit=100&offset=0';
  let last;
  for(let attempt=0;attempt<3;attempt++){
    try{
      const response=await fetch(url,{signal:AbortSignal.timeout(16000),headers:{
        'User-Agent':'APEXIUM-Studio/1.2 (+https://github.com/MukaSanches/APEXIUM)',
        'Accept':'application/json'
      }});
      if(!response.ok){
        last=new Error('Upstream HTTP '+response.status+' for '+url);
        if(![429,500,502,503,504].includes(response.status))break;
      }else{
        const json=await response.json();
        const body=json&&json.MRData;
        const tableName=resource==='races'?'RaceTable':'StandingsTable';
        const key=resource==='races'?'Races':'StandingsLists';
        const rows=body&&body[tableName]&&body[tableName][key];
        if(!Array.isArray(rows)||rows.length===0)throw new Error('Empty or invalid source for '+url);
        const folder=join(out,String(year));
        await mkdir(folder,{recursive:true});
        const data={schema:'apexium-jolpica-snapshot-v1',year,resource,url,
          fetchedAt:new Date().toISOString(),license:'CC BY-NC-SA 4.0',
          attribution:'Jolpica-F1 API: https://api.jolpi.ca/docs/',
          metadata:{total:body.total,series:body.series,limit:body.limit},rows};
        await writeFile(join(folder,resource+'.json'),JSON.stringify(data),'utf8');
        console.log('Snapshot OK:',year,resource,'records:',rows.length);
        successes++;
        return;
      }
    }catch(error){last=error;}
    if(attempt<2)await wait(1500*(attempt+1));
  }
  throw last||new Error('Unknown fetch failure');
}

for(const year of seasons){
  for(const resource of resources){
    try{await snapshot(year,resource);}
    catch(error){
      const problem=year+'/'+resource+': '+String(error);
      console.error('Snapshot error:',problem);
      failures.push(problem);
    }
    await wait(350);
  }
}
await mkdir(out,{recursive:true});
await writeFile(join(out,'ATTRIBUTION.txt'),
  'Source: Jolpica-F1 API https://api.jolpi.ca/docs/\n'+
  'Data license: CC BY-NC-SA 4.0 https://creativecommons.org/licenses/by-nc-sa/4.0/\n'+
  'Refresh attempt: '+stamp+'\n'+
  'Non-commercial use; not affiliated with Formula 1 or FIA.\n');
console.log('Snapshots:',successes,'successful;',failures.length,'failed');
// Embed synchronized real records in the HTML to guarantee initial UI data.
const bundled={};
for(const year of seasons){
  const collected={};
  for(const resource of resources){
    try{
      const data=JSON.parse(await readFile(join(out,String(year),resource+'.json'),'utf8'));
      if(data?.schema==='apexium-jolpica-snapshot-v1'&&Array.isArray(data.rows)){
        collected[resource]=data;
      }
    }catch(error){ /* missing optional dataset */ }
  }
  if(Object.keys(collected).length)bundled[String(year)]=collected;
}
const htmlPath=join(root,'dist','site','index.html');
let html=await readFile(htmlPath,'utf8');
const marker=html.match(/<script type="module" src="\.\/app\.js(?:\?[^"]*)?"><\/script>/)?.[0];
if(!marker)throw new Error('Missing app module script in HTML');
const serialized=JSON.stringify(bundled).replace(/</g,'\\u003c');
html=html.replace(marker,
  '<script id="apexium-preloaded" type="application/json">'+serialized+'</script>\n'+marker);
await writeFile(htmlPath,html,'utf8');
console.log('Embedded historical data for:',Object.keys(bundled).join(','));

for(const required of ['races','driverstandings']){
  if(failures.some(f=>f.startsWith(current+'/'+required+':'))){
    throw new Error('Missing critical '+current+' '+required+
      ' snapshot. Preventing deployment of an empty homepage.');
  }
}
