// Actual-route selected-project component fixture, not a deployment or MAIN mount.
import { createServer } from 'vite';
import { readFileSync } from 'node:fs';
import { isAbsolute, resolve } from 'node:path';
import { createServer as reservePort } from 'node:net';
const [apiUrl, publicCase, cacheRoot] = process.argv.slice(2);
const phase=name=>process.stdout.write(JSON.stringify({phase:name,process_milliseconds:performance.now()})+'\n');
phase('modules_loaded');
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(apiUrl) || !isAbsolute(publicCase) || !isAbsolute(cacheRoot)) throw new Error('Explicit external local fixture required');
const root = resolve(import.meta.dirname, '..');
if (cacheRoot.startsWith(root) || publicCase.startsWith(root)) throw new Error('External fixture/cache only');
const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div><script type="module">
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {BrowserRouter} from 'react-router';
import '@fasl-work/caos-app-shell/styles.css';import '/src/styles.css';
import {AppShell,CitationsProvider,useLangStore,useThemeStore} from '@fasl-work/caos-app-shell';
import {CITATIONS} from '/src/data/citations.ts';import {architecture} from '/src/architecture.ts';
import {JointProjectWorkbench} from '/src/components/JointProjectWorkbench.tsx';
const p=new URLSearchParams(location.search),lang=p.get('lang')||'en',theme=p.get('theme')||'light';
useLangStore.setState({lang});useThemeStore.setState({theme});document.documentElement.dataset.theme=theme;
const c=await fetch('/qa-selected-project',{cache:'no-store'}).then(r=>r.json());
const config={product:{name:'Inverse Earth Studio'},routes:[{path:'/qa-joint-project',en:'Allocated project fixture',es:'Fixture de proyecto asignado'}],links:{github:'https://github.com/fsantibanezleal/CAOS_Geophysics'},version:'0.04.001',architecture,fixedRoutes:['/qa-joint-project'],
footer:{attribution:{en:'Developed by Felipe Santibanez-Leal',es:'Desarrollado por Felipe Santibanez-Leal'},provenance:{en:'Actual private custody fixture; no scientific execution.',es:'Fixture de custodia privada real; sin ejecucion cientifica.'},license:{en:'Apache-2.0 code and CC-BY-4.0 content',es:'Codigo Apache-2.0 y contenido CC-BY-4.0'},disclaimer:{en:'Not canonical MAIN assembly or host admission.',es:'No es ensamblaje canonico MAIN ni admision de host.'}}};
function Fixture(){const [project,setProject]=useState(c.project_id);
const navigation=React.createElement('nav',{className:'processing-actions','aria-label':'Allocated fixture project navigation'},
React.createElement('button',{className:'btn','data-testid':'qa-select-other',onClick:()=>setProject(c.other_project_id)},'Select other owned project (fixture)'),
React.createElement('button',{className:'btn','data-testid':'qa-select-original',onClick:()=>setProject(c.project_id)},'Select original owned project (fixture)'));
return React.createElement(JointProjectWorkbench,{projectId:project,es:lang==='es',onManage:()=>setProject(c.other_project_id),onCurated:()=>setProject(c.project_id),methodNavigation:navigation});}
createRoot(document.getElementById('root')).render(React.createElement(BrowserRouter,null,React.createElement(CitationsProvider,{items:CITATIONS},React.createElement(AppShell,{config},React.createElement(Fixture)))));
</script></body></html>`;
const reservation=reservePort();await new Promise(resolve=>reservation.listen(0,'127.0.0.1',resolve));
const port=reservation.address().port;await new Promise(resolve=>reservation.close(resolve));
phase('ephemeral_port_reserved');
const server=await createServer({root,configFile:false,publicDir:false,cacheDir:cacheRoot,esbuild:{jsx:'automatic'},
 optimizeDeps:{entries:[],noDiscovery:true,include:['react','react/jsx-runtime','react/jsx-dev-runtime','react-dom/client','react-router','@fasl-work/caos-app-shell','fflate']},
 server:{host:'127.0.0.1',port,strictPort:true,proxy:{'/api':{target:apiUrl,changeOrigin:false}}},
 plugins:[{name:'actual-native-selected-project-fixture',configureServer(s){s.middlewares.use(async(req,res,next)=>{
  try {const url=new URL(req.url,'http://127.0.0.1');
   if(url.pathname==='/qa-selected-project'){res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.end(readFileSync(publicCase));return;}
   if(url.pathname==='/qa-joint-project'){res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/qa-joint-project',html));return;}
   next();
  }catch(error){next(error)}
 })}}]});
phase('vite_created');
await server.listen();process.stdout.write(JSON.stringify({origin:server.resolvedUrls.local[0].replace(/\/$/,'')})+'\n');
