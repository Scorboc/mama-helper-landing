/* A finite, adult-led picture activity. No recording, grading or automatic advance. */
(function(root){'use strict';
const whoUrl='https://www.who.int/news-room/detail/24-04-2019-to-grow-up-healthy-children-need-to-sit-less-and-play-more';
const warning='ВОЗ не рекомендует сидячее экранное время детям младше 2 лет. Для детей 2 лет — не более 1 часа за весь день; меньше — лучше. Это суммарное время всех экранов, а не длительность занятия. Играйте вместе со взрослым и заканчивайте при потере интереса. Наша игра не оценивалась и не одобрена ВОЗ.';
const bands=[
 [24,'Назовите предмет сами и предложите показать его на картинке. Ответ словом не нужен.','Покажите знакомую вещь рядом сами — искать или приносить её не нужно.'],
 [26,'Назовите предмет и оставьте паузу: ребёнок может показать его или ответить звуком.','Предложите показать похожую вещь рядом; если её нет, вспомните её вместе.'],
 [28,'Спросите: «Что это?» Если ответа нет, спокойно назовите сами.','Добавьте одно знакомое действие: «Мяч катится», «Мишка спит», «На стуле сидят».'],
 [30,'Предложите выбрать: назвать предмет, показать его или послушать ваше слово.','Скажите короткую фразу о знакомой вещи рядом и предложите дополнить словом или жестом.'],
 [32,'Предложите рассказать о картинке одним словом или жестом. Можно просто послушать маму.','Вспомните, где дома бывает такой предмет. Подскажите один вариант, без проверки ответа.'],
 [34,'Поговорите о том, что можно делать с этим предметом. Назовите один пример сами.','Придумайте короткую фразу о похожей вещи рядом. Ребёнок может добавить слово, жест или только слушать.']
];
const pictures=[['⚽','Мяч'],['🧸','Мишка'],['🪑','Стул']];
function eligible(age){return Number.isInteger(age)&&age>=24&&age<36;}
function create(age){if(!eligible(age))return null;const band=bands[Math.floor((age-24)/2)];return {type:'toddler',minMonths:band[0],maxMonths:band[0]+2,prompt:band[1],real:band[2],index:0,phase:'picture',done:false};}
function advance(s){if(!s||s.type!=='toddler'||s.done)return false;if(s.phase==='picture'){s.phase='real';return true;}if(s.phase!=='real')return false;if(s.index===pictures.length-1){s.done=true;s.phase='done';}else{s.index++;s.phase='picture';}return true;}
root.TogetherToddler={eligible,create,advance,pictures,warning,whoUrl};
})(typeof window!=='undefined'?window:globalThis);
