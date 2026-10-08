import { expect, test, type Locator, type Page } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
const path=process.env.GEOPHYSICS_JOINT_INPUT_BROWSER_FIXTURE;
if(!path)throw new Error('Explicit external actual allocated API fixture required; no skipped browser gate');
const fixture=JSON.parse(readFileSync(path,'utf8'));
async function pointer(page: Page,target: Locator) {
 await target.evaluate(n=>n.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'}));const b=await target.boundingBox();if(!b)throw new Error('No real pointer target');
 await page.mouse.move(b.x+b.width/2,b.y+b.height/2,{steps:5});await page.mouse.down();await page.mouse.up();
}
async function selectOriginals(tool: Locator,language: string) {
 await tool.getByLabel(language==='en'?'Original input section':'Sección de datos originales',{exact:true}).selectOption('originals');
 await tool.getByLabel(language==='en'?'Original development directory':'Directorio original de desarrollo',{exact:true}).setInputFiles(join(fixture.originals,'development'));
 await tool.getByLabel(language==='en'?'Original sealed directory':'Directorio original reservado',{exact:true}).setInputFiles(join(fixture.originals,'sealed'));
}
async function sourceFields(page: Page,tool: Locator,language: string) {
 const es=language==='es';
 await pointer(page,tool.getByRole('button',{name:es?'Verificar bytes originales opacos':'Verify opaque original bytes',exact:true}));
 await expect(tool.getByLabel(es?'Proveedor original':'Original provider',{exact:true})).toBeVisible();
 await tool.getByLabel(es?'Proveedor original':'Original provider',{exact:true}).fill('Original actual private browser custody');
 await tool.getByLabel(es?'Atribución':'Attribution',{exact:true}).fill('Original external survey fixture owner');
 await tool.getByLabel(es?'Cita (opcional)':'Citation (optional)',{exact:true}).fill('Actual source pair; scientific acceptance not inferred');
 await tool.getByLabel(es?'DOI (opcional)':'DOI (optional)',{exact:true}).fill('10.1190/1.2122412');
 await pointer(page,tool.getByRole('button',{name:es?'Revisar derechos de almacenamiento privado':'Review private-storage rights',exact:true}));
 const rights=tool.getByLabel(es?'Decisión de derechos':'Rights decision',{exact:true});await rights.focus();await rights.press('Home');await rights.press('ArrowDown');
 await tool.getByLabel(es?'Declaración original de derechos':'Original rights statement',{exact:true}).fill('I attest permission to store each original privately, without public redistribution.');
 const upload=tool.getByRole('button',{name:es?'Cargar originales e indexar, no ejecutar ciencia':'Upload originals and index, not a scientific run',exact:true});
 await expect(upload).toBeDisabled();await pointer(page,tool.getByRole('checkbox'));await expect(upload).toBeEnabled();return upload;
}
let index=0;
for(const language of ['en','es'])for(const theme of ['light','dark'])for(const phone of [false,true]){
 const caseIndex=index++;
 test(`actual authenticated native input ${language} ${theme} ${phone?'phone':'desktop'}`,async({browser})=>{
  test.setTimeout(120000);mkdirSync(fixture.evidence,{recursive:true});const c=fixture.cases[caseIndex];
  const context=await browser.newContext({baseURL:fixture.origin,viewport:phone?{width:390,height:844}:{width:1600,height:900},reducedMotion:'reduce'});
  await context.addCookies(c.cookies.map((cookie: {name: string;value: string})=>({...cookie,url:fixture.origin,httpOnly:true,sameSite:'Strict'})));
  const page=await context.newPage(),errors: string[]=[],external: string[]=[],posts: string[]=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).origin!==fixture.origin)external.push(r.url());if(r.method()!=='GET')posts.push(new URL(r.url()).pathname)});
  await page.goto(`${fixture.origin}/qa-joint-input?case=${caseIndex}&lang=${language}&theme=${theme}`);
  const tool=page.getByTestId('joint-native-input-panel');await expect(tool).toBeVisible();
  await expect(tool.getByRole('button',{name:language==='en'?'Verify opaque original bytes':'Verificar bytes originales opacos',exact:true})).toBeDisabled();
  await selectOriginals(tool,language);const upload=await sourceFields(page,tool,language);
  await page.screenshot({path:join(fixture.evidence,`input-${language}-${theme}-${phone?'phone':'desktop'}-permission.png`)});
  await pointer(page,upload);await expect(tool.getByTestId('joint-native-indexed')).toBeVisible({timeout:60000});
  const indexed=JSON.parse(await page.getByTestId('qa-parent-dataset').innerText());expect(indexed.scientific_accepted).toBe(false);
  const receipt=await context.request.get(indexed.receipt_url);expect(receipt.status()).toBe(200);const payload=await receipt.json();
  expect(payload.owner_id).toBe(c.owner_id);expect(payload.project_id).toBe(c.project_id);expect(payload.scientific_values_decoded).toBe(false);
  let count=0;for(const [role,members] of Object.entries(payload.members))for(const [name,binding] of Object.entries(members as Record<string,{asset_id: string;raw_sha256: string;source_version: number}>)) {
   const asset=await context.request.get(`/api/projects/${c.project_id}/assets/${binding.asset_id}`);expect(asset.status()).toBe(200);const view=await asset.json();
   expect(view.source.private_storage_permission).toBe('attested');expect(view.source.version).toBe(binding.source_version);expect(view.source.rights_decision).toBe('derivative-only');
   const download=await context.request.get(view.download_url);expect(download.status()).toBe(200);const bytes=await download.body();
   expect(createHash('sha256').update(bytes).digest('hex')).toBe(binding.raw_sha256);expect(bytes.equals(readFileSync(join(fixture.originals,role,name)))).toBe(true);count++;
  }expect(count).toBe(36);expect(posts.filter(p=>p.endsWith('/joint-members'))).toHaveLength(36);expect(posts.filter(p=>p.endsWith('/joint-datasets'))).toHaveLength(1);
  await pointer(page,tool.getByText(language==='en'?'Original versions, hashes and custody':'Versiones, hashes y custodia originales',{exact:true}));
  const member=tool.getByLabel(language==='en'?'Original member receipt':'Recibo de miembro original',{exact:true});
  await expect(member.locator('option')).toHaveCount(36);
  for(const [role,members] of Object.entries(payload.members))for(const [name,binding] of Object.entries(members as Record<string,{raw_sha256: string}>)) {
    await member.selectOption(`${role}/${name}`);await expect(tool.getByTestId('joint-native-member-receipt').locator('code')).toHaveText(binding.raw_sha256);
  }
  for(const codes of [tool.getByTestId('joint-native-indexed').locator('code'),tool.getByTestId('joint-native-member-receipt').locator('code')]) {
    for(const code of await codes.all())expect(await code.evaluate(node=>{const range=document.createRange();range.selectNodeContents(node);
      return [...range.getClientRects()].every(rect=>rect.left>=0&&rect.right<=innerWidth)})).toBe(true);
  }
  await page.screenshot({path:join(fixture.evidence,`input-${language}-${theme}-${phone?'phone':'desktop'}-indexed.png`)});
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await pointer(page,page.getByTestId('qa-change-project'));await expect(tool.getByTestId('joint-native-indexed')).toHaveCount(0);await expect(page.getByTestId('qa-parent-dataset')).toHaveCount(0);
  await tool.getByLabel(language==='en'?'Original input section':'Sección de datos originales',{exact:true}).selectOption('attribution');
  await expect(tool.getByLabel(language==='en'?'Original provider':'Proveedor original',{exact:true})).toHaveValue('');
  await tool.getByLabel(language==='en'?'Original input section':'Sección de datos originales',{exact:true}).selectOption('rights');await expect(tool.getByRole('checkbox')).not.toBeChecked();
  expect(errors).toEqual([]);expect(external).toEqual([]);await context.close();
 });
}
test('real partial transfer cancel, explicit resume and expired-session privacy',async({browser})=>{
 test.setTimeout(120000);const c=fixture.cases[8],context=await browser.newContext({baseURL:fixture.origin,viewport:{width:1600,height:900}});
 await context.addCookies(c.cookies.map((cookie: {name: string;value: string})=>({...cookie,url:fixture.origin,httpOnly:true,sameSite:'Strict'})));
 const page=await context.newPage();await page.goto(`${fixture.origin}/qa-joint-input?case=8`);const tool=page.getByTestId('joint-native-input-panel');
 await selectOriginals(tool,'en');await pointer(page,await sourceFields(page,tool,'en'));
 await expect.poll(()=>tool.locator('output').innerText()).toMatch(/^[1-9]\d* \/ 36/);
 await pointer(page,tool.getByRole('button',{name:'Cancel transfer / inspection',exact:true}));
 await expect(tool.getByRole('alert')).toContainText('not deleted');
 await pointer(page,tool.getByRole('button',{name:'Explicitly continue remaining uploads / index',exact:true}));
 await expect(tool.getByTestId('joint-native-indexed')).toBeVisible({timeout:60000});
 await pointer(page,tool.getByRole('button',{name:'Forget this local selection, preserve server originals',exact:true}));
 await expect(tool.getByTestId('joint-native-indexed')).toHaveCount(0);
 await expect(page.getByTestId('qa-parent-dataset')).toHaveCount(0);
 await tool.getByLabel('Original input section',{exact:true}).selectOption('attribution');await expect(tool.getByLabel('Original provider',{exact:true})).toHaveValue('');
 const csrf=await (await context.request.get('/api/auth/csrf')).json();
 const logout=await context.request.post('/api/auth/cookie/logout',{headers:{Origin:fixture.origin,'X-CSRF-Token':csrf.csrf_token}});expect(logout.status()).toBe(204);
 await selectOriginals(tool,'en');await pointer(page,await sourceFields(page,tool,'en'));
 await expect(tool.getByRole('alert')).toContainText('Session expired; private receipts cleared');
 await tool.getByLabel('Original input section',{exact:true}).selectOption('attribution');await expect(tool.getByLabel('Original provider',{exact:true})).toHaveValue('');
 await context.close();
});
