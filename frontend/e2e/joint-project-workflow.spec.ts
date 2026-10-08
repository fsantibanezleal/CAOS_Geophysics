import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { unzipSync } from 'fflate';

const input=process.env.GEOPHYSICS_JOINT_PROJECT_BROWSER_FIXTURE;
if(!input)throw new Error('Explicit external actual selected-project API fixture required; no skipped acceptance');
const fixture=JSON.parse(readFileSync(input,'utf8'));
async function pointer(page:Page,target:Locator){
 await target.evaluate(n=>n.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'}));
 const box=await target.boundingBox();if(!box)throw new Error('Actual pointer target absent');
 const reachable=await target.evaluate((node,point)=>{const hit=document.elementFromPoint(point.x,point.y);return hit===node||!!hit&&node.contains(hit)}, {x:box.x+box.width/2,y:box.y+box.height/2});
 if(!reachable)throw new Error('Actual pointer target occluded, do not count a synthetic click');
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2,{steps:5});await page.mouse.down();await page.mouse.up();
}
async function selected(page:Page,es:boolean,phone=false){
 const tool=page.getByTestId('joint-project-workbench');await expect(tool.locator('h1')).toHaveText(fixture.project_name);
 if(phone)await pointer(page,tool.getByRole('button',{name:es?'Controles de procesamiento':'Processing controls',exact:true}));
 const section=tool.getByLabel(es?'Sección de controles conjuntos':'Joint control section',{exact:true});
 await section.selectOption('run');await expect(tool.locator('.processing-scope')).toContainText(es?'no envía trabajos científicos':'No scientific job is submitted');
 await section.selectOption('history');
 await pointer(page,tool.getByRole('button',{name:es?'Actualizar historial literal de trabajos nativos':'Refresh literal native job history',exact:true}));
 const history=await page.request.get(`/api/projects/${fixture.project_id}/joint-results`);expect(history.status()).toBe(200);expect(history.headers()['cache-control']).toBe('no-store');expect(history.headers()['vary']).toBe('Cookie');
 const job=tool.getByLabel(es?'Trabajo nativo':'Native job',{exact:true});await expect(job.locator('option')).toHaveCount(1);
 await expect(job.locator('option')).toHaveText('failed · '+fixture.job_id);
 await expect(tool.locator('.processing-provenance').filter({hasText:'custody_fixture_no_execution'})).toContainText(fixture.request_sha256);
 return tool;
}
async function inspect(page:Page,tool:Locator,es:boolean,phone=false){
 const index=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/joint-results/'+fixture.job_id));
 await pointer(page,tool.getByRole('button',{name:es?'Verificar e inspeccionar originales nativos almacenados exactos':'Verify and inspect exact stored native originals',exact:true}));
 const response=await index;expect(response.status()).toBe(200);expect(response.headers()['cache-control']).toBe('no-store');expect(response.headers()['vary']).toBe('Cookie');
 const result=tool.getByTestId('joint-result-workbench');await expect(result.getByTestId('joint-response-readout')).toBeVisible({timeout:60000});
 await expect(tool.locator('.processing-status').filter({hasText:es?'Estado de trabajo del servidor':'Server job state'})).toContainText('failed');
 await expect(result.getByTestId('joint-workflow-boundary')).toContainText(es?'criterios científicos permanecen separados':'scientific gates remain separate');
 if(phone)await pointer(page,tool.getByRole('button',{name:es?'Controles de procesamiento':'Processing controls',exact:true}));
 return result;
}
for(const lang of ['en','es'])for(const theme of ['light','dark'])for(const phone of [false,true]){
 test(`actual selected native project ${lang} ${theme} ${phone?'phone':'desktop'}`,async({browser})=>{
  test.setTimeout(150000);mkdirSync(fixture.evidence,{recursive:true});const es=lang==='es',stem=`${lang}-${theme}-${phone?'phone':'desktop'}`;
  const context=await browser.newContext({baseURL:fixture.origin,viewport:phone?{width:390,height:844}:{width:1600,height:900},acceptDownloads:true,reducedMotion:'reduce'});
  await context.addCookies(fixture.cookies.map((c:{name:string;value:string})=>({...c,url:fixture.origin,httpOnly:true,sameSite:'Strict'})));
  const page=await context.newPage(),errors:string[]=[],external:string[]=[],writes:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).origin!==fixture.origin)external.push(r.url());if(r.method()!=='GET')writes.push(new URL(r.url()).pathname)});
  await page.goto(`${fixture.origin}/qa-joint-project?lang=${lang}&theme=${theme}`);
  const tool=await selected(page,es,phone),result=await inspect(page,tool,es,phone);
  await page.screenshot({path:join(fixture.evidence,`${stem}-literal-history.png`)});
  const view=result.getByLabel(es?'Vista científica conjunta':'Joint scientific view',{exact:true});await view.selectOption('native');
  const native=result.getByTestId('joint-native-state-instrument'),frames=native.getByLabel(es?'Marco de modelo nativo':'Native model frame',{exact:true});
  await expect(frames.locator('option')).toHaveCount(28);
  for(const key of [...Array.from({length:26},(_,i)=>`c${String(i).padStart(2,'0')}`),'baseline','selected']){
   await frames.selectOption(key);await expect(native.getByTestId('joint-native-frame-identity')).toContainText(key);
   const states=native.getByLabel(es?'Estado aceptado nativo':'Native accepted state',{exact:true});await states.selectOption(String((await states.locator('option').count())-1));
   await expect(native.getByTestId('joint-native-response-readout')).toBeVisible();
  }
  for(const key of ['c00','c08','c25','baseline','selected']){
   await frames.selectOption(key);
   if(key==='c00'||key==='c08')await expect(native.getByTestId('joint-native-coupling-readout')).toHaveCount(0);
   else{await expect(native.getByTestId('joint-native-coupling-readout')).toBeVisible();await native.getByLabel(es?'Ponderación de acoplamiento exacto':'Exact coupling weighting',{exact:true}).selectOption('weighted');}
   for(const part of ['training','validation','sealed']){await native.getByLabel(es?'Partición posterior a congelación':'Post-freeze partition',{exact:true}).selectOption(part);await expect(native.getByTestId('joint-native-response-readout')).toBeVisible();}
   for(const plane of ['xy','xz','yz']){await native.getByLabel(es?'Plano de sección nativa':'Native section plane',{exact:true}).selectOption(plane);await pointer(page,native.locator('rect[data-cell]').first());}
   await page.screenshot({path:join(fixture.evidence,`${stem}-${key}.png`)});
  }
  await frames.selectOption('c25');const states=native.getByLabel(es?'Estado aceptado nativo':'Native accepted state',{exact:true});
  await states.selectOption('1');await states.focus();await page.keyboard.press('ArrowUp');await expect(states).toHaveValue('0');await page.keyboard.press('ArrowDown');await expect(states).toHaveValue('1');
  await native.getByLabel(es?'Respuesta de estado nativo':'Native state response',{exact:true}).selectOption('magnetic');
  await native.getByLabel(es?'Fila receptora nativa':'Native receiver row',{exact:true}).selectOption('1');
  await native.getByLabel(es?'Corte fijo nativo':'Native fixed slice',{exact:true}).selectOption('1');
  await native.getByLabel(es?'Celda activa nativa':'Native active cell',{exact:true}).selectOption('1');
  const frameDownload=page.waitForEvent('download');await pointer(page,native.getByRole('button',{name:es?'Exportar este marco nativo exacto JSON':'Export this exact native frame JSON',exact:true}));
  const framePath=join(fixture.evidence,`${stem}-frame.json`);await(await frameDownload).saveAs(framePath);const frame=JSON.parse(readFileSync(framePath,'utf8'));
  expect(frame.key).toBe('c25');expect(frame.state).toBe(1);expect(frame.scientific_acceptance_verified).toBe(false);expect(frame.historical_sealed_use).toBe('post_freeze_diagnostic_only');
  expect(frame.responses.magnetic.sealed.residual[0]).toBe(frame.responses.magnetic.sealed.predicted[0]-frame.responses.magnetic.sealed.observed[0]);
  await pointer(page,native.getByText(es?'¿Qué magnitud exacta se muestra?':'Which exact quantity is shown?',{exact:true}));
  await pointer(page,native.getByText(es?'Manifiesto exacto de fuente y marco nativo':'Exact native source and frame manifest',{exact:true}));
  await expect(native.locator('pre')).toContainText('exporter_source_inventory');
  const download=page.waitForEvent('download');await pointer(page,result.getByRole('button',{name:es?'Exportar archivo privado original (incluye observaciones)':'Export original private archive (includes observations)',exact:true}));
  const zipPath=join(fixture.evidence,`${stem}-native-originals.zip`);await(await download).saveAs(zipPath);const archive=unzipSync(new Uint8Array(readFileSync(zipPath)));
  expect(Object.keys(archive).sort()).toEqual(Object.keys(fixture.index.members).sort());
  for(const[name,member]of Object.entries(fixture.index.members)as[string,{byte_count:number;sha256:string}][]){expect(archive[name].length).toBe(member.byte_count);expect(createHash('sha256').update(archive[name]).digest('hex')).toBe(member.sha256);}
  for(const[name,digest]of Object.entries(frame.original_file_sha256))expect(digest).toBe(fixture.index.members[name].sha256);
  await expect.poll(()=>page.evaluate(()=>({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,w:innerWidth,h:innerHeight}))).toEqual(phone?{width:390,height:844,w:390,h:844}:{width:1600,height:900,w:1600,h:900});
  if(phone)await pointer(page,tool.getByRole('button',{name:es?'Controles de procesamiento':'Processing controls',exact:true}));
  await pointer(page,tool.getByRole('button',{name:es?'Borrar vistas privadas, no bytes del servidor':'Clear private views, not server bytes',exact:true}));
  await expect(result.getByTestId('joint-native-state-instrument')).toHaveCount(0);await expect(tool.getByLabel(es?'Trabajo nativo':'Native job',{exact:true}).locator('option')).toHaveCount(0);
  expect(errors).toEqual([]);expect(external).toEqual([]);expect(writes).toEqual([]);await context.close();
 });
}
test('actual selected project read cancellation, cookie expiry and other-owner denial',async({browser})=>{
 test.setTimeout(150000);const context=await browser.newContext({baseURL:fixture.origin,viewport:{width:1600,height:900}});
 await context.addCookies(fixture.cookies.map((c:{name:string;value:string})=>({...c,url:fixture.origin,httpOnly:true,sameSite:'Strict'})));
 const page=await context.newPage();await page.goto(`${fixture.origin}/qa-joint-project`);let tool=page.getByTestId('joint-project-workbench');
 await expect(tool.locator('h1')).toHaveText(fixture.project_name);
 const inputPanel=tool.getByTestId('joint-native-input-panel');await inputPanel.getByLabel('Original input section',{exact:true}).selectOption('attribution');
 await inputPanel.getByLabel('Original provider',{exact:true}).fill('Private original provider to forget');
 await inputPanel.getByLabel('Attribution',{exact:true}).fill('Private selected source attribution');
 await inputPanel.getByLabel('Original input section',{exact:true}).selectOption('rights');
 await inputPanel.getByLabel('Original rights statement',{exact:true}).fill('Private attestation, not a public redistribution grant');await pointer(page,inputPanel.getByRole('checkbox'));
 await pointer(page,tool.getByRole('button',{name:'Clear private views, not server bytes',exact:true}));
 await inputPanel.getByLabel('Original input section',{exact:true}).selectOption('attribution');
 await expect(inputPanel.getByLabel('Original provider',{exact:true})).toHaveValue('');await expect(inputPanel.getByLabel('Attribution',{exact:true})).toHaveValue('');
 await inputPanel.getByLabel('Original input section',{exact:true}).selectOption('rights');await expect(inputPanel.getByRole('checkbox')).not.toBeChecked();
 await expect(inputPanel.getByLabel('Original rights statement',{exact:true})).toHaveValue('');
 tool=await selected(page,false);
 const read=page.waitForRequest(r=>new URL(r.url()).pathname.endsWith('/joint-results/'+fixture.job_id));
 await pointer(page,tool.getByRole('button',{name:'Verify and inspect exact stored native originals',exact:true}));await read;
 await pointer(page,page.getByTestId('qa-select-other'));await expect(tool.locator('h1')).toHaveText(fixture.other_project_name);
 await expect(tool.getByTestId('joint-native-state-instrument')).toHaveCount(0);await expect(tool.getByLabel('Native job',{exact:true}).locator('option')).toHaveCount(0);
 await pointer(page,tool.getByRole('button',{name:'Refresh literal native job history',exact:true}));await expect(tool.getByLabel('Native job',{exact:true}).locator('option')).toHaveCount(0);
 await pointer(page,page.getByTestId('qa-select-original'));tool=await selected(page,false);await inspect(page,tool,false);
 const csrf=await(await context.request.get('/api/auth/csrf')).json();expect((await context.request.post('/api/auth/cookie/logout',{headers:{Origin:fixture.origin,'X-CSRF-Token':csrf.csrf_token}})).status()).toBe(204);
 await pointer(page,tool.getByRole('button',{name:'Refresh literal native job history',exact:true}));await expect(tool.getByRole('alert')).toContainText('Unauthorized');
 await expect(tool.getByTestId('joint-response-readout')).toHaveCount(0);await expect(tool.getByLabel('Native job',{exact:true})).toHaveCount(0);
 await page.screenshot({path:join(fixture.evidence,'expired-private-views.png')});
 const other=await browser.newContext({baseURL:fixture.origin});await other.addCookies(fixture.other_cookies.map((c:{name:string;value:string})=>({...c,url:fixture.origin,httpOnly:true,sameSite:'Strict'})));
 const root=`/api/projects/${fixture.project_id}/joint-results/${fixture.job_id}`;
 for(const path of [`/api/projects/${fixture.project_id}/joint-results`,root,root+'/members?name=workflow.json',root+'/export'])expect((await other.request.get(path)).status()).toBe(404);
 await other.close();await context.close();
});
