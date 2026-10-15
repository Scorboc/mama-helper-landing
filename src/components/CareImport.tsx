import {useEffect,useState} from 'react';
import type {CareRecord} from '@/lib/care-journal';
import {parseCareCsv,exportCareCsv} from '@/lib/care-csv';
import {api} from '@/lib/parent-api';
import {ruCount} from '@/lib/ru-count';
import {Button} from './ui/button';
import {Input} from './ui/input';

const kindLabels: Record<CareRecord['kind'],string> = {
  sleep:'Сон', wake:'Пробуждение', feeding:'Кормление', food:'Прикорм',
  achievement:'Навык', mood:'Самочувствие родителя',
};

export default function CareImport({childId,version,records,onSaved}:{childId:string;version:string;records:CareRecord[];onSaved:()=>Promise<void>}){
  const [preview,setPreview]=useState<CareRecord[]>([]),[error,setError]=useState(''),[status,setStatus]=useState(''),[busy,setBusy]=useState(false),[snapshot,setSnapshot]=useState('');
  useEffect(()=>{setPreview([]);setError('');setStatus('');},[childId]);
  function download(){const url=URL.createObjectURL(new Blob([exportCareCsv(records)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='mama-care.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <details className="sleep-section"><summary>Перенести дневник · CSV</summary><p>Поддерживается только формат MAMA CSV, до 100 строк. Время содержит Z или смещение часового пояса, например +03:00. Файл читается на устройстве; выбранные записи передаются серверу после подтверждения. Импорт дополняет дневник, не заменяет его. Переписка и самочувствие не включаются.</p>
    <Button variant="outline" onClick={download}>Скачать CSV / образец формата</Button>
    <label className="form-field mt-4">Выбрать CSV<Input type="file" accept=".csv,text/csv" disabled={busy} onChange={async e=>{const file=e.target.files?.[0];setPreview([]);setStatus('');if(!file)return;if(file.size>200000){setError('Файл должен быть не больше 200 КБ.');return;}const result=parseCareCsv(await file.text());setError(result.errors.join('\n'));setPreview(result.errors.length?[]:result.records);setSnapshot(version);}}/></label>
    {error&&<p role="alert" style={{whiteSpace:'pre-wrap'}}>{error}</p>}
    {preview.length>0&&<><p>Предпросмотр: {ruCount(preview.length,'запись','записи','записей')}. Точные совпадения будут пропущены; пересечение сна отменит весь импорт.</p>{preview.map((r,i)=><p key={i}>{kindLabels[r.kind]} · {new Date(r.at).toLocaleString('ru-RU')} {r.end?' → '+new Date(r.end).toLocaleString('ru-RU'):''}{r.value?' · '+r.value:''}{r.note?' · '+r.note:''}</p>)}<Button disabled={busy||snapshot!==version} onClick={async()=>{setBusy(true);setError('');try{const result=await api<{added:number;skipped:number}>('care-import',{childId,contextVersion:snapshot,records:preview});setPreview([]);setStatus(`Добавлено: ${result.added}. ${ruCount(result.skipped,'совпадение','совпадения','совпадений')} пропущено.`);await onSaved();window.dispatchEvent(new Event('care-records-changed'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>Подтвердить добавление в активный профиль</Button><Button variant="ghost" disabled={busy} onClick={()=>setPreview([])}>Отменить предпросмотр</Button>{snapshot!==version&&<p role="alert">Дневник изменился. Выберите файл снова для нового предпросмотра.</p>}</>}
    {status&&<p role="status">{status}</p>}
  </details>;
}
