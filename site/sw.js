/** Offline app shell only. Third-party API responses remain under source control. */
const CACHE = 'apexium-app-shell-v1.3';
const APP_SHELL = ['./','./index.html','./styles.css','./app.js','./analytics.js',
  './feed.js','./sdk/javascript/index.js','./manifest.webmanifest','./icons/apexium.svg',
  './icons/apexium-192.png','./icons/apexium-512.png'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(APP_SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(names=>Promise.all(names.filter(n=>n.startsWith('apexium-app-shell-')&&n!==CACHE).map(n=>caches.delete(n)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin)return; // Never intercept upstream API calls.
  if(!url.pathname.startsWith(new URL('./',self.registration.scope).pathname))return;
  if(req.mode==='navigate'){
    event.respondWith(fetch(req).catch(()=>caches.match('./index.html')));
    return;
  }
  event.respondWith(fetch(req).then(response=>{if(response.ok){const fresh=response.clone();event.waitUntil(caches.open(CACHE).then(c=>c.put(req,fresh)));}return response;}).catch(()=>caches.match(req)));
});
