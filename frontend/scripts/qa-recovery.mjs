/** Local rendered acceptance, explicitly authorized Playwright browser. */
import {chromium} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';

const base=process.env.QA_BASE??'http://127.0.0.1:5179';
const output=resolve(process.env.QA_OUTPUT??'../data/experiments/browser-recovery');
mkdirSync(output,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader']});
const context=await browser.newContext({viewport:{width:1440,height:960},deviceScaleFactor:1});
const page=await context.newPage();
const errors=[];const rows=[];
page.on('pageerror',error=>errors.push(String(error)));
page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
async function capture(name){
  await page.screenshot({path:resolve(output,`${name}.png`),fullPage:false});
  const layout=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,
    canvas:[...document.querySelectorAll('canvas')].map(c=>({width:c.width,height:c.height})),
    fonts:[...new Set([...document.querySelectorAll('h1,h2,button,label')].map(e=>getComputedStyle(e).fontFamily))]}));
  if(layout.scrollWidth>layout.width+1)errors.push(`Horizontal document overflow: ${name}`);
  rows.push({name,...layout});console.log('CAPTURE',name,JSON.stringify(layout),{errors:errors.length});
}
await page.goto(base,{waitUntil:'networkidle'});
await page.getByLabel('Geological case',{exact:true}).waitFor();
await capture('desktop-gravity-final');
await page.getByRole('button',{name:'Synthetic target',exact:true}).click();
await capture('desktop-gravity-truth');
await page.getByRole('button',{name:'Final model',exact:true}).click();
await page.getByRole('button',{name:'Play',exact:true}).click();
await page.getByText(/Model replay · saved state/).first().waitFor();
await page.getByRole('button',{name:'Pause',exact:true}).click();
await capture('desktop-replay');
await page.getByRole('checkbox',{name:'Show final model',exact:true}).check();
await page.getByLabel('Geological case',{exact:true}).selectOption('JOINT_SHARED');
await page.getByLabel('Inverse method',{exact:true}).selectOption('pgi');
await page.getByRole('tab',{name:'Inversion',exact:true}).click();
await capture('desktop-pgi');
await page.getByLabel('Geological case',{exact:true}).selectOption('MT_CONDUCTIVE');
await page.getByLabel('Inverse method',{exact:true}).selectOption('mt-lm');
await capture('desktop-mt-uncertainty');
await page.getByLabel('Geological case',{exact:true}).selectOption('FWI_LAYERED');
await page.getByRole('tab',{name:'Model',exact:true}).click();
await capture('desktop-fwi-model');
await page.getByLabel('Geological case',{exact:true}).selectOption('LEARNED_AUTOENCODER');
await page.getByLabel('Inverse method',{exact:true}).selectOption('cnn');
await capture('desktop-signed-cnn');
for(const route of ['introduction','methodology','implementation','experiments','benchmark']){
  await page.goto(`${base}/${route}`,{waitUntil:'networkidle'});
  await capture(`desktop-${route}`);
}
await page.goto(`${base}/experiments`,{waitUntil:'networkidle'});
const edi=page.getByText('Original synthetic EDI fixtures',{exact:true});
if(await edi.count()){await edi.scrollIntoViewIfNeeded();await capture('desktop-edi');}
await page.getByRole('button',{name:'Switch language',exact:true}).click();
await page.getByRole('button',{name:'Cambiar claro / oscuro',exact:true}).click();
await page.setViewportSize({width:390,height:844});
await capture('mobile-es-experiments');
await page.goto(base,{waitUntil:'networkidle'});
await capture('mobile-es-workbench');
writeFileSync(resolve(output,'report.json'),JSON.stringify({base,rows,errors},null,2));
await browser.close();
if(errors.length)throw new Error(errors.join('\n'));
