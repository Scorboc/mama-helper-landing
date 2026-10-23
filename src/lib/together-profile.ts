import type {Profile} from '@/lib/parent-model';
import {ageValue} from '@/lib/parent-model';
export function playAge(profile:Profile|null, now=new Date()):number|null {
  if(!profile || profile.stage!=='child' || !/^\d{4}-\d{2}-\d{2}$/.test(profile.birthDate))return null;
  const parsed=new Date(profile.birthDate+'T00:00:00Z');
  if(!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0,10)!==profile.birthDate)return null;
  const age=ageValue(profile,now);
  return Number.isInteger(age)&&age>=0&&age<84?age:null;
}
