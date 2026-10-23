/* Pure local game rules. No storage, timers, network or personal information. */
(function(root){'use strict';
const symbols=['●','▲','★','♥'];
const pictures=[['🐻','Мишка'],['🏡','Дом'],['☀️','Солнце'],['🌧️','Дождь'],['🌳','Дерево'],['🚂','Поезд'],['🍎','Яблоко'],['🌙','Луна'],['🧺','Корзинка'],['⚽','Мяч'],['🌼','Цветок'],['⭐','Звезда']];
function eligible(months){return Number.isInteger(months)&&months>=36&&months<84;}
function settings(months,level){if(!eligible(months))return null;const max=Math.floor(months/12)-3;const n=level===undefined?max:Math.max(0,Math.min(max,Math.floor(level)));return {level:n,pairs:3+n,length:2+n,story:3+n};}
function shuffle(values,random=Math.random){const a=values.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function memory(months,level,random){const config=settings(months,level);if(!config)return null;const ids=shuffle(pictures.map((_,i)=>i),random).slice(0,config.pairs);return {type:'pairs',config,cards:shuffle(ids.concat(ids),random),open:[],matched:[],turn:0,pending:false,done:false};}
function tap(s,index){if(!s||s.type!=='pairs'||s.pending||s.done||!Number.isInteger(index)||index<0||index>=s.cards.length||s.open.includes(index)||s.matched.includes(index))return false;s.open.push(index);if(s.open.length===2){s.pending=true;if(s.cards[s.open[0]]===s.cards[s.open[1]])s.matched.push(...s.open);s.done=s.matched.length===s.cards.length;}return true;}
function next(s){if(!s||s.type!=='pairs'||!s.pending||s.done)return false;s.open=[];s.pending=false;s.turn=1-s.turn;return true;}
function pattern(months,level,leader=0){const config=settings(months,level);return config?{type:'pattern',config,leader:leader===1?1:0,phase:'compose',target:[],answer:[],done:false}:null;}
function put(s,id){if(!s||s.type!=='pattern'||s.done||!Number.isInteger(id)||id<0||id>=symbols.length||!['compose','repeat'].includes(s.phase))return false;const line=s.phase==='compose'?s.target:s.answer;if(line.length>=s.config.length)return false;line.push(id);return true;}
function handover(s){if(!s||s.type!=='pattern'||s.phase!=='compose'||s.target.length!==s.config.length)return false;s.phase='repeat';return true;}
function compare(s){if(!s||s.type!=='pattern'||s.phase!=='repeat'||s.answer.length!==s.config.length)return null;const same=s.target.every((v,i)=>v===s.answer[i]);s.phase='done';s.done=true;return same;}
function undo(s){if(!s||s.type!=='pattern'||!['compose','repeat'].includes(s.phase))return false;const line=s.phase==='compose'?s.target:s.answer;if(!line.length)return false;line.pop();return true;}
function story(months,level,leader=0){const config=settings(months,level);return config?{type:'story',config,chosen:[],leader:leader===1?1:0,turn:leader===1?1:0,done:false}:null;}
function choose(s,id){if(!s||s.type!=='story'||s.done||!Number.isInteger(id)||id<0||id>=pictures.length)return false;s.chosen.push(id);s.turn=1-s.turn;s.done=s.chosen.length===s.config.story;return true;}
function detective(months,level){const config=settings(months,level);return config?{type:'detective',config,round:0,phase:'prepare',clue:null,done:false}:null;}
function readyDetective(s){if(!s||s.type!=='detective'||s.phase!=='prepare')return false;s.phase='clue';return true;}
function setClue(s,id){if(!s||s.type!=='detective'||s.phase!=='clue'||s.done||!Number.isInteger(id)||id<0||id>5)return false;s.clue=id;s.phase='find';return true;}
function found(s){if(!s||s.type!=='detective'||s.phase!=='find'||s.done)return false;s.round++;s.done=s.round===2;s.phase=s.done?'done':'handover';return true;}
function detectiveNext(s){if(!s||s.type!=='detective'||s.phase!=='handover'||s.done)return false;s.phase='clue';s.clue=null;return true;}
const api={readyDetective,detective,setClue,found,detectiveNext,symbols,pictures,eligible,settings,memory,tap,next,pattern,put,handover,compare,undo,story,choose};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.TogetherGames=api;
})(typeof window!=='undefined'?window:globalThis);
