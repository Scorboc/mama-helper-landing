export type TypingKey = { code: string; en: string; ru: string; x: number; z: number; width: number };
const rows: [string, string, string, number?][][] = [
  [['Backquote','`','ё'],...Array.from('1234567890',n=>['Digit'+n,n,n] as [string,string,string]),['Minus','−','−'],['Equal','=','=',1],['Backspace','⌫','⌫',2]],
  [['Tab','Tab','Tab',1.5],...Array.from('QWERTYUIOP', (n,i)=>['Key'+n,n,'ЙЦУКЕНГШЩЗ'[i]] as [string,string,string]),['BracketLeft','[','Х'],['BracketRight',']','Ъ'],['Backslash','\\','\\',1.5]],
  [['CapsLock','Caps','Caps',1.75],...Array.from('ASDFGHJKL',(n,i)=>['Key'+n,n,'ФЫВАПРОЛД'[i]] as [string,string,string]),['Semicolon',';','Ж'],['Quote',"'",'Э'],['Enter','Enter','Enter',2.25]],
  [['ShiftLeft','Shift','Shift',2.25],...Array.from('ZXCVBNM',(n,i)=>['Key'+n,n,'ЯЧСМИТЬ'[i]] as [string,string,string]),['Comma',',','Б'],['Period','.','Ю'],['Slash','/','.',1],['ShiftRight','Shift','Shift',2.75]],
  [['ControlLeft','Ctrl','Ctrl',1.25],['MetaLeft','◇','◇',1.25],['AltLeft','Alt','Alt',1.25],['Space','⎵','⎵',6.25],['AltRight','Alt','Alt',1.25],['ArrowLeft','←','←',1.25],['ArrowDown','↓','↓',1.25],['ArrowRight','→','→',1.25]],
];
export const KEY_PITCH = .021;
export const typingKeys: TypingKey[] = rows.flatMap((row,index)=>{
  let offset = -7.5;
  return row.map(([code,en,ru,width=1])=>{
    const key={code,en,ru,x:(offset+width/2)*KEY_PITCH,z:(index-2)*KEY_PITCH,width:width*KEY_PITCH-.002};
    offset+=width;
    return key;
  });
});
export function typingKey(code: string, key = ''): TypingKey | undefined {
  const direct = typingKeys.find(item=>item.code===code);
  if (direct) return direct;
  const letter=key.toUpperCase();
  if (key===' ') return typingKeys.find(item=>item.code==='Space');
  const shifted: Record<string, string> = {
    '!':'Digit1', '@':'Digit2', '#':'Digit3', '$':'Digit4', '%':'Digit5', '^':'Digit6', '&':'Digit7', '*':'Digit8', '(':'Digit9', ')':'Digit0',
    '_':'Minus', '-':'Minus', '+':'Equal', '{':'BracketLeft', '}':'BracketRight', '|':'Backslash', ':':'Semicolon', '"':'Quote', '<':'Comma', '>':'Period', '?':'Slash', '~':'Backquote',
  };
  const fallback = shifted[key];
  return typingKeys.find(item=>item.en.toUpperCase()===letter || item.ru.toUpperCase()===letter || item.code===(fallback || key));
}
export type TypingPulse = { code: string; russian: boolean; id: number };
