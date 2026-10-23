import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

// Exercise the actual JSX, including the reduced-motion/video-failure still,
// under both the domain root and a nested Pages installation.
function render(file, base, reduced=false) {
  const source=fs.readFileSync(new URL('../src/components/'+file,import.meta.url),'utf8')
    .replaceAll('import.meta.env.BASE_URL',JSON.stringify(base));
  const jsx=(type,props)=>({type,props});
  const react={useState:v=>[typeof v==='function'?v():v,()=>{}],useRef:v=>({current:v}),
    useEffect(){},useLayoutEffect(){},useCallback:fn=>fn};
  const module={exports:{}};
  const require=name=> name==='react'?react:name==='react/jsx-runtime'?{jsx,jsxs:jsx,Fragment:'fragment'}:
    name==='react-router-dom'?{useLocation:()=>({pathname:'/',search:'?intro=1'}),Link:'a'}:
    name==='lucide-react'?{ArrowDown:'icon',ArrowRight:'icon'}:
    name.endsWith('room-experience')?{isRoomLocation:()=>true,roomCues:[],ROOM_OUTRO_START:20.25}:
    name.endsWith('room-media')?{useRoomVideo:()=>({current:null})}:
    name.endsWith('room-handoff')?{startCamera(){}}:
    name.endsWith('room-motion')?{RoomMotion:class{},ROOM_MAX_SPEED:2}:(()=>{throw new Error(name)})();
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{module,exports:module.exports,require,URLSearchParams,window:{matchMedia:()=>({matches:reduced})}});
  const tree=module.exports.default({returning:false,onComplete(){}}), nodes=[];
  function walk(n){if(!n||typeof n!=='object')return;if(Array.isArray(n)){n.forEach(walk);return;}nodes.push(n);walk(n.props?.children);}
  walk(tree);return nodes;
}
for(const base of ['/','/mama-helper-landing/']) {
  test('persistent introduction media resolves inside '+base,()=>{
    const nodes=render('RoomTransition.tsx',base),video=nodes.find(n=>n.type==='video');
    assert.equal(video.props.src,base+'media/room/journey-v13-seek.mp4');
    assert.equal(video.props.poster,base+'media/room/start-v12.webp');
    assert.equal(video.props.muted,true);assert.equal(video.props.playsInline,true);
    assert.equal(video.props.preload,'auto','cold intro must load without a prior prepare event');
    for(const img of nodes.filter(n=>n.type==='img'))assert.ok(img.props.src.startsWith(base+'media/room/'));
  });
  test('accessible still fallback resolves inside '+base,()=>{
    const still=render('RoomIntroduction.tsx',base,true).find(n=>n.type==='img');
    assert.equal(still.props.src,base+'media/room/start-v12.webp');assert.ok(still.props.alt.includes('�����'));
  });
}
