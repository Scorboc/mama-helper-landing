import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function compile(path, require, globals={}) {
  const source=fs.readFileSync(new URL(path,import.meta.url),'utf8').replaceAll('import.meta.env.BASE_URL',JSON.stringify('/'));
  const module={exports:{}};
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{module,exports:module.exports,require,URLSearchParams,...globals});
  return module.exports.default;
}
const jsx=(type,props)=>({type,props});
test('an explicit tour is usable before session resolves, ordinary visit still waits',()=>{
  const Tour=()=>null;
  for(const intro of [true,false]){
    const react={useState:value=>[value,()=>{}],useEffect(){},useRef:value=>({current:value})};
    const require=name=>name==='react'?react:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:
      name==='react-router-dom'?{useNavigate:()=>()=>{},useSearchParams:()=>[new URLSearchParams(intro?'intro=1':'')],Link:'a'}:
      name.endsWith('RoomIntroduction')?{default:Tour}:name.endsWith('RoomGuestEntry')?{default:()=>null}:
      name.endsWith('parent-api')?{api:()=>new Promise(()=>{})}:name.endsWith('room-experience')?{}:(()=>{throw Error(name)})();
    const Index=compile('../src/pages/Index.tsx',require);
    const tree=Index();
    assert.equal(tree.type,intro?Tour:'main');
  }
});

test('the first touch wakes a decoder that ignores preload, before RAF playback',()=>{
  const effects=[],handlers=new Map();let plays=0;const frames=[];
  const style={getPropertyValue:()=>'',setProperty(){},removeProperty(){}};
  const track={style,dataset:{},getBoundingClientRect:()=>({top:0})};
  const video={readyState:0,seeking:false,paused:true,currentTime:0,pause(){this.paused=true;},play(){plays++;this.paused=false;return Promise.resolve();},addEventListener(){},removeEventListener(){}};
  const react={useRef:value=>({current:value===null?track:value}),useState:value=>[typeof value==='function'?value():value,()=>{}],useLayoutEffect(){},useEffect:fn=>effects.push(fn)};
  const require=name=>name==='react'?react:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:
    name==='react-router-dom'?{Link:'a'}:name==='lucide-react'?{ArrowDown:'icon',ArrowRight:'icon'}:
    name.endsWith('room-media')?{useRoomVideo:()=>({current:video})}:
    name.endsWith('room-experience')?{ROOM_OUTRO_START:20.25,roomCues:[]}:
    name.endsWith('room-motion')?{RoomMotion:class{target=0;position=0;moving=false;begin(){}scroll(){}step(){return 0;}release(){}},ROOM_MAX_SPEED:1.25}:(()=>{throw Error(name)})();
  const win={innerHeight:844,innerWidth:390,matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}}),dispatchEvent(){},addEventListener:(name,fn)=>handlers.set(name,fn),removeEventListener(){},clearTimeout(){}};
  const Tour=compile('../src/components/RoomIntroduction.tsx',require,{window:win,document:{documentElement:{classList:{add(){},remove(){}},style}},requestAnimationFrame:fn=>{frames.push(fn);return frames.length;},cancelAnimationFrame(){},performance:{now:()=>100},Event:class{}});
  Tour({returning:false,onComplete(){}});
  const cleanups=effects.map(fn=>fn());
  assert.equal(plays,0,'loading does not start unrequested playback');
  handlers.get('touchstart')({touches:[{clientY:600}],target:{closest:()=>null}});
  assert.equal(plays,1,'play/loading is requested synchronously from the gesture');
  assert.equal(video.paused,true,'a stationary tap never starts movement');
  video.readyState=4;
  for(let i=0;i<3&&frames.length;i++)frames.shift()(120+i*16);
  assert.equal(video.paused,true);assert.equal(video.currentTime,0);
  handlers.get('touchend')();
  assert.equal(video.paused,true,'touchend retries loading without automatic movement');
  for(const cleanup of cleanups)cleanup?.();
});


test('finishing before the delayed session resolves preserves the member destination',async()=>{
  const effects=[],destinations=[];let resolveSession;
  const request=new Promise(resolve=>{resolveSession=resolve;});
  const react={useState:value=>[value,()=>{}],useEffect:fn=>effects.push(fn),useRef:value=>({current:value})};
  const require=name=>name==='react'?react:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:
    name==='react-router-dom'?{useNavigate:()=>path=>destinations.push(path),useSearchParams:()=>[new URLSearchParams('intro=1')],Link:'a'}:
    name.endsWith('RoomIntroduction')?{default:()=>null}:name.endsWith('RoomGuestEntry')?{default:()=>null}:
    name.endsWith('parent-api')?{api:()=>request}:name.endsWith('room-experience')?{rememberRoom(){},ROOM_CHAT:'/chat?scene=room'}: {};
  const win={setTimeout:()=>1,clearTimeout(){},dispatchEvent(){},scrollTo(){}};
  const Index=compile('../src/pages/Index.tsx',require,{window:win,CustomEvent:class{}});
  const tree=Index();
  const cleanup=effects[1]();
  const completion=tree.props.onComplete();
  assert.deepEqual(destinations,[],'completion waits for the actual session');
  resolveSession({});await completion;
  assert.deepEqual(destinations,['/chat?scene=room']);
  cleanup();
});


test('a never-resolving session cannot trap the skip button; unmount cancels navigation',async()=>{
  for(const unmount of [false,true]){
    const effects=[],destinations=[],timers=[];
    const react={useState:value=>[value,()=>{}],useEffect:fn=>effects.push(fn),useRef:value=>({current:value})};
    const require=name=>name==='react'?react:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:
      name==='react-router-dom'?{useNavigate:()=>path=>destinations.push(path),useSearchParams:()=>[new URLSearchParams('intro=1')],Link:'a'}:
      name.endsWith('RoomIntroduction')?{default:()=>null}:name.endsWith('RoomGuestEntry')?{default:()=>null}:
      name.endsWith('parent-api')?{api:()=>new Promise(()=>{})}:name.endsWith('room-experience')?{rememberRoom(){},ROOM_CHAT:'/chat?scene=room'}:{};
    const win={setTimeout:(fn,ms)=>{timers.push({fn,ms});return timers.length;},clearTimeout(){},dispatchEvent(){},scrollTo(){}};
    const Index=compile('../src/pages/Index.tsx',require,{window:win,CustomEvent:class{}});
    const tree=Index(),cleanup=effects[1]();
    const completion=tree.props.onComplete();
    if(unmount)cleanup();
    const timer=timers.at(-1);assert.equal(timer.ms,2500);timer.fn();
    await completion;
    assert.deepEqual(destinations,unmount?[]:['/']);
    if(!unmount)cleanup();
  }
});
