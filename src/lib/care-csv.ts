import type { CareRecord } from './care-journal';
const fields=['kind','at','end','note','value','side','sleepType','wakeType','settlingAt','feeling'] as const;
export function parseCareCsv(text:string): { records:CareRecord[]; errors:string[] } {
  const rows:string[][]=[]; let row:string[]=[], cell='', quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(c===','&&!quoted){row.push(cell);cell='';}
    else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(Boolean))rows.push(row);row=[];cell='';}
    else cell+=c;
  }
  if(quoted)return {records:[],errors:['Не закрыты кавычки CSV.']};
  row.push(cell);if(row.some(Boolean))rows.push(row);
  const header=rows.shift();
  if(!header || header.join(',')!==fields.join(','))return {records:[],errors:['Нужен CSV формата MAMA: '+fields.join(',')]};
  if(rows.length>100)return {records:[],errors:['Максимум 100 строк за один импорт.']};
  const records:CareRecord[]=[],errors:string[]=[];
  const validTime=(v:string)=>/T\d{2}:\d{2}.*(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))&&Date.parse(v)<=Date.now();
  rows.forEach((values,i)=>{
    const r=Object.fromEntries(fields.map((key,j)=>[key,values[j]||''])) as unknown as CareRecord;
    if(values.length!==fields.length||!['sleep','wake','feeding','food','achievement'].includes(r.kind)||!validTime(r.at)||(r.end&&!validTime(r.end))||(r.end&&Date.parse(r.end)<=Date.parse(r.at))|| (r.kind==='sleep'&&!r.end) || (r.note||'').length>500 || (r.value||'').length>120){errors.push(`Строка ${i+2}: проверьте вид, время с часовым поясом и длину текста. Сон должен иметь окончание.`);return;}
    Object.keys(r).forEach(k=>{if(r[k as keyof CareRecord]==='')delete r[k as keyof CareRecord];});
    records.push(r);
  });
  return {records,errors};
}
export function exportCareCsv(records:CareRecord[]) {
  // A spreadsheet must not interpret a parent's note as a formula.
  const quote=(v:string)=>'"'+(/^[=+@\-\t\r]/.test(v)?"'":'')+v.replace(/"/g,'""')+'"';
  return fields.join(',')+'\r\n'+records.filter(r=>r.kind!=='mood').map(r=>fields.map(k=>quote(String(r[k]||''))).join(',')).join('\r\n');
}
