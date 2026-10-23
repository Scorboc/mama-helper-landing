// Run after a Vite build with --base /mama-helper-landing/.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.resolve(process.argv[2] || 'dist');
const base='/mama-helper-landing/';
const root=fileURLToPath(new URL('..',import.meta.url));
let html=fs.readFileSync(path.join(dir,'index.html'),'utf8');
for(const name of ['demo-content.js','demo-model.js','phone-preview-adapter.js']) fs.copyFileSync(path.join(root,'deploy/pages',name),path.join(dir,name));
html=html.replace('<head>','<head>\n'+['demo-content.js','demo-model.js','phone-preview-adapter.js'].map(n=>`<script src="${base}${n}"></script>`).join('\n'));
// Static files and PWA links must stay inside the Pages subdirectory.
html=html.replace(/(href|src)="\/(?!\/|mama-helper-landing\/)/g,`$1="${base}`);
fs.writeFileSync(path.join(dir,'index.html'),html);
fs.writeFileSync(path.join(dir,'app-config.json'),JSON.stringify({apiUrl:base+'__preview-api',publicDemo:true}));
fs.writeFileSync(path.join(dir,'.nojekyll'),'');
fs.writeFileSync(path.join(dir,'404.html'),'<!doctype html><meta charset="utf-8"><title>MAMA helper</title><script>location.replace('+JSON.stringify(base+'?__route=')+'+encodeURIComponent(location.pathname.slice('+JSON.stringify(base.slice(0,-1))+'.length)+location.search+location.hash));</script>');
const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.webmanifest'),'utf8'));
function prefix(x){return typeof x==='string'&&x.startsWith('/')&&!x.startsWith(base)?base+x.slice(1):x;}
manifest.id=base;manifest.scope=base;manifest.start_url=base+'cabinet';
for(const icon of manifest.icons||[])icon.src=prefix(icon.src);
for(const shortcut of manifest.shortcuts||[]){shortcut.url=prefix(shortcut.url);for(const icon of shortcut.icons||[])icon.src=prefix(icon.src);}
fs.writeFileSync(path.join(dir,'manifest.webmanifest'),JSON.stringify(manifest,null,2));
console.log('Prepared explicit memory-only Pages demo:',dir);
