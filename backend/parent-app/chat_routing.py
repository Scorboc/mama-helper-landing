"""Local, bounded routing for the optional two-tier MAMA chat."""
import re
from contextlib import contextmanager
from contextvars import ContextVar

RECENT_HISTORY = ContextVar('chat_routing_recent_history', default=())


@contextmanager
def history_context(history):
    token = RECENT_HISTORY.set(tuple(history or ()))
    try:
        yield
    finally:
        RECENT_HISTORY.reset(token)

COMPLEX = re.compile(
    r'лекарств|дозиров|антибиот|жаропониж|температур|лихорад|аллерги|сыпь|'
    r'не набирает вес|потер[яил] вес|плохо набира|отказ.{0,20}(?:груд|ед|смес|пить)|'
    r'мало мокрых|кашел|кашля|насморк|боли[т ]|болит|запор|понос|'
    r'поперх|подав|давит.{0,20}(?:кусоч|ед)|кусоч.{0,20}давит|рвот|обезвож|магнит|батарей|судорог|диагноз|симптом|лечебн.{0,15}массаж|'
    r'регресс.{0,20}(?:навык|развит|сон)|утрат.{0,15}навык|'
    r'безопасн.{0,20}сон|на животе|пеленан|плед|подушк|бортик.{0,15}кроват|'
    r'прикорм.{0,35}(?:аллерг|кусоч|поперх|не готов)|'
    r'депресси|паническ|послеродов.{0,20}(?:тревог|состояни|депресс)|'
    r'навредить себе|навредить ребёнку|навязчив.{0,30}вред|мысл.{0,30}вред|теряю контроль', re.I)
DOMAINS = (
    re.compile(r'сон|засып|просып|уклад', re.I),
    re.compile(r'корм|гв|груд|смес|прикорм|ед|питани', re.I),
    re.compile(r'развит|навык|игр|ход|полз|говор', re.I),
    re.compile(r'тревог|стресс|устал|плач|выгоран', re.I),
)
FOLLOWUP = re.compile(r'^(а |но |почему|что если|тогда|а если|это |он |она |можно ли)', re.I)


def choose(question, history, ordinary, complex_model):
    """Return a model ID; never sends or stores message text."""
    if not isinstance(question, str) or not question.strip():
        return ordinary
    if COMPLEX.search(question):
        return complex_model
    if len(question) >= 80 and sum(bool(pattern.search(question)) for pattern in DOMAINS) >= 2:
        return complex_model
    if len(question) <= 160 and FOLLOWUP.search(question.strip()):
        previous = next((item.get('text', '') for item in reversed(history if history is not None else RECENT_HISTORY.get())
                         if isinstance(item, dict) and item.get('role') == 'user'), '')
        if isinstance(previous, str) and COMPLEX.search(previous):
            return complex_model
    return ordinary
