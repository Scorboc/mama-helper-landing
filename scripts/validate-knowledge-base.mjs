import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const readJson = path => JSON.parse(readFileSync(path,'utf8'));
const taxonomy=readJson('knowledge-base/catalog/question-taxonomy.ru.json');
const redFlags=readJson('knowledge-base/catalog/red-flags.ru.json');
const sources=readJson('knowledge-base/sources/source-registry.json');
const schema=readJson('knowledge-base/cards/card.schema.json');
assert.equal(taxonomy.schema,'mama-helper-question-taxonomy/v1');
assert.ok(taxonomy.catalog.length>=16,'Need broad topic coverage');
const ids=new Set();const questions=[];
for(const topic of taxonomy.catalog){
  assert.match(topic.id,/^[a-z0-9-]+$/);assert.ok(!ids.has(topic.id),'Duplicate topic id');ids.add(topic.id);
  assert.ok(topic.questions.length>=10,`${topic.id} needs enough phrasings`);
  for(const q of topic.questions){assert.ok(q.length>=10);assert.ok(!questions.includes(q),`Duplicate question: ${q}`);questions.push(q);}
}
assert.ok(questions.length>=240,`Only ${questions.length} questions`);
assert.ok(taxonomy.catalog.some(x=>x.id==='father-role'));
assert.ok(taxonomy.catalog.some(x=>x.id==='parent-wellbeing'));
assert.ok(taxonomy.catalog.some(x=>x.risk==='urgent'));
assert.ok(redFlags.groups.length>=4);
assert.ok(sources.never_evidence_domains.includes('babyblog.ru'));
assert.ok(sources.never_evidence_domains.includes('reddit.com'));
assert.ok(sources.tiers.some(t=>t.allowed_domains.includes('cr.minzdrav.gov.ru')));
assert.deepEqual(schema.required,['id','status','topic','audience','intent_examples','answer_contract','safety','provenance','review']);
console.log(`Knowledge-base checks passed: ${taxonomy.catalog.length} topics, ${questions.length} natural-language questions, ${redFlags.groups.length} red-flag groups.`);
