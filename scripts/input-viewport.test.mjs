import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source=fs.readFileSync(new URL('../src/lib/input-viewport.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
class Events {
  listeners=new Map();
  addEventListener(n,f){if(!this.listeners.has(n))this.listeners.set(n,new Set());this.listeners.get(n).add(f);}
  removeEventListener(n,f){this.listeners.get(n)?.delete(f);}
  emit(n){for(const f of this.listeners.get(n)||[])f({type:n});}
}
function setup(withViewport=true){
  class Element {
    parentElement=null;scrollHeight=0;clientHeight=0;overflowY='visible';y=650;
    matches(){return true;}
    getBoundingClientRect(){return {top:this.y,bottom:this.y+48,height:48};}
  }
  const doc=new Events(), win=new Events(), values=new Map(), frames=new Map();let serial=0;
  doc.documentElement={dataset:{},style:{setProperty:(n,v)=>values.set(n,v),removeProperty:n=>values.delete(n)}};
  doc.activeElement=null;doc.body=new Element();
  win.innerHeight=844;win.innerWidth=390;win.getComputedStyle=e=>e;
  win.requestAnimationFrame=f=>{frames.set(++serial,f);return serial;};
  win.cancelAnimationFrame=id=>frames.delete(id);
  const scrolls=[];win.scrollBy=x=>scrolls.push(x.top);
  if(withViewport)win.visualViewport=Object.assign(new Events(),{height:844,offsetTop:0,scale:1});
  const module={exports:{}};vm.runInNewContext(code,{module,exports:module.exports,HTMLElement:Element});
  const stop=module.exports.installInputViewport(win,doc);
  const flush=()=>{for(let i=0;i<5&&frames.size;i++){const tasks=[...frames.values()];frames.clear();tasks.forEach(f=>f());}};
  const focus=()=>{doc.activeElement=new Element();doc.emit('focusin');flush();};
  return {doc,win,values,scrolls,stop,flush,focus,Element};
}
test('iOS visual-only keyboard sets visible height, overlap and reveals focused field',()=>{
  const s=setup();s.focus();s.scrolls.length=0;s.win.visualViewport.height=360;s.win.visualViewport.emit('resize');s.flush();
  assert.equal(s.doc.documentElement.dataset.inputKeyboard,'open');
  assert.equal(s.values.get('--input-viewport-height'),'360px');
  assert.equal(s.values.get('--input-keyboard-overlap'),'484px');assert.equal(s.scrolls.at(-1),410);
});
test('viewport panning updates offset without fighting user scrolling',()=>{
  const s=setup();s.focus();s.scrolls.length=0;s.win.visualViewport.height=360;s.win.visualViewport.offsetTop=100;s.win.visualViewport.emit('scroll');s.flush();
  assert.equal(s.values.get('--input-viewport-top'),'100px');assert.equal(s.values.get('--input-keyboard-overlap'),'384px');assert.equal(s.scrolls.length,0);
});
test('layout-resizing keyboard and browsers without VisualViewport use focused baseline',()=>{
  for(const vv of [true,false]){const s=setup(vv);s.focus();s.win.innerHeight=330;if(vv)s.win.visualViewport.height=330;s.win.emit('resize');s.flush();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'open');assert.equal(s.values.get('--input-keyboard-overlap'),'0px');}
});
test('hardware focus and pinch zoom do not masquerade as keyboard',()=>{
  const s=setup();s.focus();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'closed');
  s.win.visualViewport.scale=2;s.win.visualViewport.height=300;s.win.visualViewport.emit('resize');s.flush();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'closed');assert.equal(s.values.get('--input-viewport-height'),'844px');
});
test('close restores layout; cleanup removes listeners and CSS state',()=>{
  const s=setup();s.focus();s.win.visualViewport.height=360;s.win.visualViewport.emit('resize');s.flush();
  s.win.visualViewport.height=844;s.win.visualViewport.emit('resize');s.flush();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'closed');
  s.stop();assert.equal(s.values.size,0);assert.equal(s.doc.documentElement.dataset.inputKeyboard,undefined);
  for(const e of [s.win,s.doc,s.win.visualViewport])for(const set of e.listeners.values())assert.equal(set.size,0);
});
test('focused field scrolls inside its dialog before the document',()=>{
  const s=setup();s.focus();const parent=new s.Element();parent.y=20;parent.getBoundingClientRect=()=>({top:20,bottom:340});parent.overflowY='auto';parent.scrollHeight=900;parent.clientHeight=320;
  parent.scrollBy=({top})=>{s.doc.activeElement.y-=top;};s.doc.activeElement.parentElement=parent;s.scrolls.length=0;
  s.win.visualViewport.height=360;s.win.visualViewport.emit('resize');s.flush();assert.equal(s.doc.activeElement.y,240);assert.equal(s.scrolls.length,0);
});

test('small address-bar resize does not snap back; zoom keeps open layout',()=>{
 const s=setup();s.focus();s.win.visualViewport.height=360;s.win.visualViewport.emit('resize');s.flush();s.scrolls.length=0;
 s.win.visualViewport.height=340;s.win.visualViewport.emit('resize');s.flush();assert.equal(s.scrolls.length,0);
 s.win.visualViewport.scale=2;s.win.visualViewport.height=170;s.win.visualViewport.emit('resize');s.flush();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'open');assert.equal(s.values.get('--input-viewport-height'),'340px');
 s.doc.activeElement=null;s.doc.emit('focusout');s.flush();assert.equal(s.doc.documentElement.dataset.inputKeyboard,'closed');assert.equal(s.values.get('--input-keyboard-overlap'),'0px');
});
