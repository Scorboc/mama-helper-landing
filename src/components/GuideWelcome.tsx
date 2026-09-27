import {useState} from 'react';
import {BookOpen, X} from 'lucide-react';
import './guide-welcome.css';

const guide='/mamin-pomoshchnik-instruction.pdf?v=20260921-guidance';

function LittleGuide(){
 return <div className="guide-baby-stage" aria-hidden="true">
  <div className="guide-baby-travel"><div className="guide-baby-sprite"/></div>
  <div className="guide-baby-joke guide-baby-joke-first">Я уже дополз.<br/>Теперь ваша очередь!</div>
  <div className="guide-baby-joke guide-baby-joke-second">Вот эта кнопка!<br/>Да-да, эта 😄</div>
 </div>;
}

export default function GuideWelcome(){
 // Test version: no persistent dismissal; every cabinet entry shows the guide again.
 const [visible,setVisible]=useState(true);
 return <section className={`guide-welcome ${visible?'':'guide-welcome-compact'}`} aria-label="Инструкция к сайту">
  {visible&&<LittleGuide/>}
  <div className="guide-welcome-copy">
   {visible&&<><span className="guide-welcome-kicker">Ваш маленький проводник</span><h2>Пс-с… тут всё по шагам!</h2><p>Как общаться с помощником, выбирать игры и сохранять полезное — загляните в инструкцию.</p></>}
   <a className="guide-open-button" href={guide} target="_blank" rel="noreferrer"><BookOpen size={19}/>Открыть инструкцию<span className="guide-pdf-label">PDF</span></a>
   {visible&&<small>Откроется в новой вкладке. Можно сохранить на телефон.</small>}
  </div>
  {visible&&<button type="button" className="guide-close" onClick={()=>setVisible(false)} aria-label="Скрыть подсказку до следующего входа"><X size={19}/></button>}
 </section>;
}
