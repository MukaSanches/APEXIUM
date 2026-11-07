/** Build a single-file APEXIUM Studio edition usable by double-clicking HTML.
 * No npm packages required, no external assets; real API calls need internet/CORS.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const read=path=>readFile(join(root,path),'utf8');
let html=await read('site/index.html');
const css=await read('site/styles.css');
const sdk=await read('sdk/javascript/index.js');
const analytics=await read('site/analytics.js');
const feed=await read('site/feed.js');
let app=await read('site/app.js');
const withoutExports=s=>s.replace(/^export\s+/gm,'');
app=app.replace(/^import\s+[^;]+;\s*$/gm,'');
const script=`(()=>{\nconst { Apexium }=(()=>{\n${withoutExports(sdk)}\nreturn {Apexium};})();\nconst { ANALYSES }=(()=>{\n${withoutExports(analytics)}\nreturn {ANALYSES};})();\nconst { getSeasonData }=(()=>{\n${withoutExports(feed)}\nreturn {getSeasonData};})();\n${app}\n})();`;
if(script.includes('</script>'))throw Error('Script contains an unsafe closing tag');
html=html.replace(/<link rel="stylesheet" href="\.\/styles\.css(?:\?[^"]*)?"\s*\/>/,`<style>\n${css}\n</style>`)
 .replace(/<link rel="manifest" href="\.\/manifest\.webmanifest"\s*\/>/,'')
 .replace(/<link rel="icon" href="\.\/icons\/apexium\.svg" type="image\/svg\+xml"\s*\/>/,'')
 .replace(/<link rel="apple-touch-icon" href="\.\/icons\/apexium-192\.png"\s*\/>/,'')
 .replace(/<script type="module" src="\.\/app\.js(?:\?[^"]*)?"><\/script>/,`<script>\n${script}\n</script>`);
if(/src="\.\/app\.js(?:\?[^\"]*)?"/.test(html)||/href="\.\/styles\.css(?:\?[^\"]*)?"/.test(html))throw Error('Bundling failed: external app assets remain');
const dist=join(root,'dist');await mkdir(dist,{recursive:true});
const target=join(dist,'APEXIUM_Standalone.html');
await writeFile(target,html,'utf8');
console.log(`APEXIUM Standalone created: ${target} (${Buffer.byteLength(html)} bytes)`);
