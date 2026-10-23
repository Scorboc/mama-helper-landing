import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

function render(permission, accepted) {
  const calls=[];const confirmations=[];
  const jsx=(type,props)=>({type,props:props||{}});
  const source=ts.transpileModule(fs.readFileSync(new URL('../src/components/DoctorQuestions.tsx',import.meta.url),'utf8'),{
    fileName:'DoctorQuestions.tsx',compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022},
  }).outputText;
  const hooks={useState:value=>[typeof value==='function'?value():value,()=>{}],useRef:value=>({current:value}),useEffect:()=>{}};
  const req=name=>name==='react'?hooks:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:
    name.endsWith('confirm-action')?{confirmAction:async message=>{confirmations.push(message);return accepted;}}:
    name.endsWith('ui/button')?{Button:'button'}:{};
  const module={exports:{}};new Function('require','module','exports',source)(req,module,module.exports);
  const tree=module.exports.DoctorQuestionList({questions:[{id:'synthetic',note:'Test question'}],permission,
    onChange:async(...args)=>{calls.push(args);return true;}});
  const nodes=[];function walk(node){if(!node||typeof node!=='object')return;nodes.push(node);for(const c of [node.props?.children].flat(Infinity))walk(c);}walk(tree);
  return {button:nodes.find(n=>n.type==='button'&&n.props.children==='Удалить'),calls,confirmations};
}
test('owner deletion requires explicit confirmation; cancel sends no write',async()=>{
  for(const accepted of [false,true]){
    const r=render('owner',accepted);assert.ok(r.button);r.button.props.onClick();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(r.confirmations.length,1);
    assert.equal(r.calls.length,accepted?1:0);
  }
});
test('read and write participants have no ordinary delete control',()=>{
  for(const role of ['read','write'])assert.equal(render(role,true).button,undefined);
});
