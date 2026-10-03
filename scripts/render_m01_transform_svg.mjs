// Static scientific figure QA in a separate headless profile; never user browser state.
import {spawn} from 'node:child_process';
import {mkdir, mkdtemp, readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath, pathToFileURL} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'data/raw/gravity-m01-transforms');
await mkdir(output, {recursive: true});
const profile = await mkdtemp(path.join(output, 'render-profile-'));
const executable = process.env.M01_FIGURE_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const browser = spawn(executable, ['--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
try {
  let port;
  for (let i=0; i<100; i++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break; }
    catch { await delay(100); }
  }
  if (!port) throw new Error('Headless figure browser did not start within 10 seconds');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.addEventListener('open', resolve, {once:true}); socket.addEventListener('error', reject, {once:true});});
  let nextId=0;
  const pending = new Map();
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    const item = pending.get(message.id);
    if (item) {pending.delete(message.id); clearTimeout(item.timer); message.error ? item.reject(new Error(JSON.stringify(message.error))) : item.resolve(message.result);}
  });
  const command = (method, params={}) => new Promise((resolve, reject) => {
    const id=++nextId;
    const timer=setTimeout(() => {pending.delete(id); reject(new Error(`Figure CDP timeout: ${method}`));}, 10000);
    pending.set(id, {resolve,reject,timer}); socket.send(JSON.stringify({id,method,params}));
  });
  await command('Page.enable');
  await command('Emulation.setDeviceMetricsOverride', {width:1200,height:820,deviceScaleFactor:1,mobile:false});
  const source = path.join(root, 'docs/methods/gravity-processing/assets/equivalent-source-transforms.svg');
  await command('Page.navigate', {url:pathToFileURL(source).href});
  for (let i=0; i<100; i++) {
    const ready=await command('Runtime.evaluate', {expression:"document.documentElement.tagName === 'svg'",returnByValue:true});
    if (ready.result.value) break;
    if (i===99) throw new Error('SVG did not load');
    await delay(50);
  }
  await command('Runtime.evaluate', {expression:'document.fonts.ready.then(() => true)',awaitPromise:true,returnByValue:true});
  const receipt=[];
  for (const theme of ['light','dark']) {
    await command('Emulation.setEmulatedMedia', {features:[{name:'prefers-color-scheme',value:theme}]});
    await command('Runtime.evaluate', {expression:'new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))',awaitPromise:true});
    const details=await command('Runtime.evaluate', {expression:`JSON.stringify({dark:matchMedia('(prefers-color-scheme: dark)').matches,background:getComputedStyle(document.querySelector('rect')).fill,outside:[...document.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.x<0||b.y<0||b.x+b.width>1200||b.y+b.height>820}).map(t=>t.textContent)})`,returnByValue:true});
    const values=JSON.parse(details.result.value);
    if (values.dark !== (theme==='dark') || values.outside.length) throw new Error(`Theme/bounds failed: ${JSON.stringify(values)}`);
    const screenshot=await command('Page.captureScreenshot',{format:'png'});
    const bytes=Buffer.from(screenshot.data,'base64');
    const filename=`theory-${theme}-cdp.png`;
    await writeFile(path.join(output,filename),bytes,{flag:'wx'});
    receipt.push({theme,...values,filename,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});
  }
  const value={schema_version:'m01-static-svg-render-1',browser:await command('Browser.getVersion'),source_sha256:createHash('sha256').update(await readFile(source)).digest('hex'),receipt,web_acceptance:false};
  await writeFile(path.join(output,'svg-render.json'),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(value));
} finally {
  socket?.close();
  browser.kill();
}
