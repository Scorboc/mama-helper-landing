/* Manual, finite local-file playback. No microphone, remote TTS or storage. */
(function(root){'use strict';
function create(clips,{makeAudio=src=>new Audio(src),onChange=()=>{}}={}){
 let current=null,last=null,muted=false,version=0,status='idle';
 function emit(next){status=next;onChange({status,last,muted,playing:current!==null});}
 function cancel(){version++;const old=current;current=null;if(old){old.onended=null;old.onerror=null;try{old.pause();old.currentTime=0;old.removeAttribute?.('src');old.load?.();}catch{/* Detached media may already be unloaded. */}old.remove?.();}}
 function stop(forget=false){cancel();if(forget)last=null;emit(muted?'muted':'idle');}
 function play(id){
  if(!Object.hasOwn(clips,id)||!/^audio\/[a-z0-9-]+\.mp3$/.test(clips[id].src)){stop(true);return false;}
  cancel();last=id;if(muted){emit('muted');return false;}
  const ticket=version;let audio;
  try{audio=makeAudio(clips[id].src);current=audio;audio.volume=0.65;audio.loop=false;audio.preload='none';
   audio.onended=()=>{if(ticket!==version||current!==audio)return;cancel();emit('ended');};
   audio.onerror=()=>{if(ticket!==version||current!==audio)return;cancel();emit('error');};
   emit('loading');const result=audio.play();
   Promise.resolve(result).then(()=>{if(ticket===version&&current===audio)emit('playing');},()=>{if(ticket===version&&current===audio){cancel();emit('error');}});
   return true;
  }catch{cancel();emit('error');return false;}
 }
 function setMuted(value){muted=value===true;stop(false);}
 return {play,stop,repeat:()=>last!==null?play(last):false,setMuted,snapshot:()=>({status,last,muted,playing:current!==null})};
}
root.MamaGameAudio={create};
})(typeof window!=='undefined'?window:globalThis);
