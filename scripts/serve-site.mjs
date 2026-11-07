/** Developer preview without build tools (node scripts/serve-site.mjs). */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(fileURLToPath(new URL('../dist/site',import.meta.url)));
const port=Number(process.env.PORT||4173);
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.webmanifest':'application/manifest+json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon'};
const server=createServer(async(req,res)=>{
  try{
    const url=new URL(req.url,'http://localhost');
    const pathname=decodeURIComponent(url.pathname);
    const candidate=resolve(root,`.${pathname.endsWith('/')?pathname+'index.html':pathname}`);
    if(candidate!==root&&!candidate.startsWith(root+sep))throw Error('Blocked path traversal');
    const meta=await stat(candidate);
    if(!meta.isFile())throw Error('Not a file');
    const content=await readFile(candidate);
    res.writeHead(200,{'Content-Type':types[extname(candidate)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    res.end(content);
  }catch(_){res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});res.end('Arquivo não encontrado');}
});
server.listen(port,'127.0.0.1',()=>console.log(`APEXIUM preview: http://127.0.0.1:${port}`));
