(function(root){'use strict';
function validAge(n){return Number.isInteger(n)&&n>=0&&n<84;}
function select(cards,age,filters={}){if(!validAge(age))return [];return cards.filter(c=>c.minMonths<=age&&age<c.maxMonths&&(!filters.area||c.category===filters.area)&&(!filters.noMaterials||c.noMaterials)&&(!filters.stationary||c.stationary)&&(!filters.education||c.education));}
function page(cards,cursor=0,all=false){const start=Number.isInteger(cursor)&&cursor>=0&&cursor<cards.length?cursor:0;return {start,items:all?cards:cards.slice(start,start+3),next:start+3>=cards.length?0:start+3};}
function context(data,origin,expectedOrigin,sameSource){if(!sameSource||origin!==expectedOrigin||data?.type!=='mama-games-context'||data.mode!=='profile')return null;return {mode:data.mode,ageMonths:validAge(data.ageMonths)?data.ageMonths:null};}
root.TogetherLibrary={validAge,select,page,context};
})(typeof window!=='undefined'?window:globalThis);
