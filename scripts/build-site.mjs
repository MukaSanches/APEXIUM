/** Build no-dependency distributable website from repository source. */
import { cp, mkdir, rm, writeFile, readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const target = join(root, 'dist', 'site');
await rm(target,{recursive:true,force:true});
await mkdir(target,{recursive:true});
await cp(join(root,'site'),target,{recursive:true});
await mkdir(join(target,'sdk','javascript'),{recursive:true});
await cp(join(root,'sdk','javascript','index.js'),join(target,'sdk','javascript','index.js'));
await cp(join(root,'sdk','javascript','index.d.ts'),join(target,'sdk','javascript','index.d.ts'));
await writeFile(join(target,'.nojekyll'),'');
for (const name of ['index.html','app.js','analytics.js','styles.css','sw.js','manifest.webmanifest','sdk/javascript/index.js']){
  const content=await readFile(join(target,name));
  if(!content.length)throw new Error(`Empty expected asset: ${name}`);
}
console.log(`APEXIUM app ready: ${target}`);
