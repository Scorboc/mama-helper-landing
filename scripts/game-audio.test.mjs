import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
const read=name=>fs.readFileSync(new URL('../public/together-games/'+name,import.meta.url),'utf8');
const box={window:{}};for(const name of ['audio-player.js','audio-manifest.js','toddler-core.js'])vm.runInNewContext(read(name),box);
const {MamaGameAudio:A,MamaGameClips:clips,TogetherToddler:T}=box.window;
function harness(){const media=[],events=[];const makeAudio=src=>{let resolve,reject;const pending=new Promise((a,b)=>{resolve=a;reject=b;});const m={src,pauseCount:0,removed:false,play(){return pending;},pause(){this.pauseCount++;},removeAttribute(name){if(name==='src')this.src='';},load(){},remove(){this.removed=true;},resolve,reject};media.push(m);return m;};return {media,events,player:A.create(clips,{makeAudio,onChange:s=>events.push(s)})};}
const settle=()=>new Promise(resolve=>setImmediate(resolve));

test('audio is manual and rejects unknown names and external file paths',()=>{
 const {player:p,media}=harness();assert.equal(media.length,0);assert.equal(p.repeat(),false);
 for(const id of ['missing','__proto__',null])assert.equal(p.play(id),false);
 const bad=A.create({bad:{src:'https://outside.invalid/audio.mp3'}},{makeAudio:()=>{throw Error('must not run');}});assert.equal(bad.play('bad'),false);
 assert.equal(p.play('cat'),true);assert.equal(media.length,1);assert.equal(media[0].volume,0.65);assert.equal(media[0].loop,false);assert.equal(media[0].preload,'none');
});

test('new sound cancels old media and late rejected play or ended events cannot alter it',async()=>{
 const {player:p,media}=harness();p.play('cat');const oldEnded=media[0].onended;p.play('red');
 assert.equal(media[0].pauseCount,1);assert.equal(media[0].src,'');assert.equal(media[0].removed,true);
 media[0].reject(Error('aborted'));oldEnded();media[1].resolve();await settle();assert.equal(p.snapshot().status,'playing');assert.equal(p.snapshot().last,'red');
 media[1].onended();assert.equal(p.snapshot().status,'ended');assert.equal(p.snapshot().playing,false);assert.equal(media[1].removed,true);
 assert.equal(media.length,2);assert.equal(p.repeat(),true);assert.equal(media.length,3);
});

test('mute and reset cancel loading and never resume automatically',async()=>{
 const {player:p,media}=harness();p.play('sound-dog');p.setMuted(true);media[0].resolve();await settle();
 assert.equal(p.snapshot().status,'muted');assert.equal(p.repeat(),false);assert.equal(media.length,1);
 p.setMuted(false);assert.equal(media.length,1);assert.equal(p.repeat(),true);p.stop(true);media[1].reject(Error('aborted'));await settle();assert.equal(p.snapshot().last,null);assert.equal(p.repeat(),false);assert.equal(p.snapshot().status,'idle');
});

test('failed playback leaves a manual retry and text-led game available',async()=>{
 const {player:p,media}=harness();p.play('blue');media[0].reject(Error('browser blocked'));await settle();assert.equal(p.snapshot().status,'error');assert.equal(p.snapshot().playing,false);assert.equal(media.length,1);assert.equal(p.repeat(),true);
 media[1].onerror();assert.equal(p.snapshot().status,'error');assert.equal(media[1].removed,true);
});

test('every toddler round maps its actual picture or selected option to a local clip',()=>{
 const used=new Set();for(let age=24;age<36;age++)for(const theme of Object.keys(T.themes)){
  const s=T.create(age,theme);for(let part=0;part<3;part++){
   if(['colors','shapes','sizes'].includes(theme)){assert.equal(T.audioId(s),null);for(const i of [0,1]){T.choose(s,i);const id=T.audioId(s);assert.ok(clips[id],id);used.add(id);}}
   else{const id=T.audioId(s);assert.ok(clips[id]);used.add(id);}
   if(theme==='animals'){assert.ok(clips[T.soundId(s)]);used.add(T.soundId(s));}
   T.advance(s);assert.equal(T.audioId(s),null);assert.equal(T.soundId(s),null);T.advance(s);
  }assert.equal(T.audioId(s),null);
 }
 assert.equal(used.size,21);assert.equal(Object.keys(clips).length,21);
 for(const [id,clip]of Object.entries(clips)){assert.ok(clip.label);assert.match(clip.src,/^audio\/[a-z0-9-]+\.mp3$/);assert.ok(fs.statSync(new URL('../public/together-games/'+clip.src,import.meta.url)).size>500,id);}
 assert.match(clips['big-circle'].label,/Большой круг/);assert.match(clips['small-triangle'].label,/Маленький треугольник/);
});


test('active speech files use the normal-voice edition and match published credits',()=>{
 const credits=JSON.parse(fs.readFileSync(new URL('../public/together-games/audio/credits.json',import.meta.url),'utf8'));
 assert.equal(credits.speech.files.length,18);
 for(const item of credits.speech.files){
  assert.match(item.file,/^voice-full-[a-z-]+\.mp3$/);
  const bytes=fs.readFileSync(new URL('../public/together-games/audio/'+item.file,import.meta.url));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),item.sha256);
  assert.ok(Object.values(clips).some(c=>c.src==='audio/'+item.file));
 }
 for(const [id,clip] of Object.entries(clips))if(!id.startsWith('sound-'))assert.match(clip.src,/^audio\/voice-full-/);
});
