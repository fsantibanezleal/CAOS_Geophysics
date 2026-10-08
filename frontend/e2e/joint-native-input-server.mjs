// Explicit loopback component fixture only; never a product deploy/mount.
import { createServer } from 'vite';
import { readFileSync } from 'node:fs';
import { isAbsolute, resolve } from 'node:path';
import { createServer as reservePort } from 'node:net';
const [apiUrl, publicCases, cacheRoot] = process.argv.slice(2);
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(apiUrl) || !isAbsolute(publicCases) || !isAbsolute(cacheRoot)) throw new Error('Explicit external local fixture arguments required');
const root=resolve(import.meta.dirname,'..');
if (cacheRoot.startsWith(root) || publicCases.startsWith(root)) throw new Error('Fixture data/cache must stay external');
const html=`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div><script type="module">
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import '@fasl-work/caos-app-shell/styles.css';import '/src/styles.css';
import {CitationsProvider,useLangStore,useThemeStore} from '@fasl-work/caos-app-shell';
import {CITATIONS} from '/src/data/citations.ts';import {ApiClient} from '/src/api/client.ts';
import {JointNativeInputPanel} from '/src/components/JointNativeInputPanel.tsx';
const p=new URLSearchParams(location.search),lang=p.get('lang')||'en',theme=p.get('theme')||'light';
useLangStore.setState({lang});useThemeStore.setState({theme});document.documentElement.dataset.theme=theme;
const c=await fetch('/qa-case?index='+p.get('case'),{cache:'no-store'}).then(r=>r.json());
const api=new ApiClient(location.origin);
function Fixture(){const [project,setProject]=useState(c.project_id),[indexed,setIndexed]=useState(null);
return React.createElement(React.Fragment,null,React.createElement('button',{onClick:()=>{setIndexed(null);setProject(project===c.project_id?c.other_project_id:c.project_id)},'data-testid':'qa-change-project'},'Change owned project (fixture)'),
React.createElement(JointNativeInputPanel,{projectId:project,ownerId:c.owner_id,api,onIndexed:setIndexed,onCleared:()=>setIndexed(null)}),
indexed&&React.createElement('output',{'data-testid':'qa-parent-dataset'},JSON.stringify(indexed)))}
createRoot(document.getElementById('root')).render(React.createElement(CitationsProvider,{items:CITATIONS},React.createElement(Fixture)));
</script></body></html>`;
// Vite treats configured0 as its5173 default. Reserve a real ephemeral choice;
// strictPort still refuses a race instead of touching another owner's server.
const reservation=reservePort();await new Promise(resolve=>reservation.listen(0,'127.0.0.1',resolve));
const port=reservation.address().port;await new Promise(resolve=>reservation.close(resolve));
const server=await createServer({root,configFile:false,publicDir:false,cacheDir:cacheRoot,esbuild:{jsx:'automatic'},
 optimizeDeps:{entries:[],noDiscovery:true,include:['react','react/jsx-runtime','react/jsx-dev-runtime','react-dom/client','@fasl-work/caos-app-shell','fflate']},
 server:{host:'127.0.0.1',port,strictPort:true,proxy:{'/api':{target:apiUrl,changeOrigin:false}}},
 plugins:[{name:'actual-private-joint-input-fixture',configureServer(s){s.middlewares.use(async(req,res,next)=>{
  try { const url=new URL(req.url,'http://127.0.0.1');
   if(url.pathname==='/qa-case') { const cases=JSON.parse(readFileSync(publicCases,'utf8')),index=Number(url.searchParams.get('index'));
    if(!Number.isInteger(index)||!cases[index])throw new Error('Invalid fixture case');
    res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.end(JSON.stringify(cases[index]));return; }
   if(url.pathname==='/qa-joint-input') { res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/qa-joint-input',html));return; }
   next();
  } catch(error){next(error)}
 })}}]});
await server.listen();process.stdout.write(JSON.stringify({origin:server.resolvedUrls.local[0].replace(/\/$/,'')})+'\n');
