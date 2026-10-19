// Fixed handoff only: no diagnosis, age assumptions or treatment instructions.
// The server keeps its wider safety checks; this works before/offline during a request.
export function localEmergencyNotice(question: string): string {
  const text = question.toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ");
  const critical = /не дыш(?:ит|ат)|не могу дышать|не может дышать|задыха(?:ется|юсь|ются)|без сознания|потерял[аи]? сознание|посинел[аи]?|синеют губы|судороги|(?:проглотил[аи]?|проглотили)\s+(?:батарейк|магнит)|(?:сильное|обильное|не останавливается)\s+кровотечение|не хочу жить|хочу (?:умереть|убить себя)|сейчас (?:наврежу|причиню вред) (?:себе|ребенку)/;
  if (!critical.test(text)) return "";
  return "Если это происходит сейчас, звоните 112. Не ждите ответа чата. Сообщите диспетчеру, что произошло, и следуйте его указаниям.";
}
