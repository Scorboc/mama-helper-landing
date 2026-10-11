"""Local release regressions. Uses a temporary QA API, synthetic accounts only.

No notifications, paid models, email, payments or messages to third parties.
Recovery/invitation secrets are held only in memory, never logged/captured.
"""
from datetime import date, timedelta
import json
from pathlib import Path
import re
import secrets
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[2] / 'outputs/qa-impeccable'
base = 'http://127.0.0.1:5173'
checks = []

def checked(name):
    checks.append(name)
    print('PASS: '+name, flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(viewport={'width':375,'height':812},reduced_motion='reduce',accept_downloads=True)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))

    def api(action, **data):
        result=page.evaluate('''async payload=>{const r=await fetch('/api',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); return {status:r.status,body:await r.json()};}''', {'action':action, **data})
        assert result['status']==200, (action,result['status'])
        return result['body']

    def register(tab):
        email='flow-'+secrets.token_hex(6)+'@example.test'; password=secrets.token_urlsafe(24)
        tab.goto(base+'/account',wait_until='networkidle')
        tab.get_by_label('Электронная почта').fill(email)
        tab.get_by_label('Пароль',exact=True).fill(password)
        tab.get_by_role('checkbox').check()
        tab.get_by_role('button',name='Создать аккаунт',exact=True).click()
        tab.locator('.recovery-code').wait_for()
        recovery=tab.locator('.recovery-code').inner_text()
        tab.get_by_role('button',name='Код сохранён — перейти в кабинет').click()
        tab.wait_for_url('**/cabinet')
        return email,password,recovery

    def profile(tab,name,age):
        tab.goto(base+'/cabinet?tab=profile',wait_until='networkidle')
        tab.get_by_label('Имя ребёнка или домашнее имя',exact=False).fill(name)
        tab.locator('label').filter(has_text='Ваш этап').get_by_role('combobox').click()
        tab.get_by_role('option',name='Ребёнок родился',exact=True).click()
        tab.get_by_label('Дата рождения ребёнка').fill((date.today()-timedelta(days=age)).isoformat())
        tab.once('dialog',lambda d:d.accept())
        tab.get_by_role('button',name='Сохранить профиль один раз').click()
        tab.wait_for_url('**tab=chat')

    def nav(name):
        page.get_by_role('navigation',name='Разделы личного кабинета').get_by_role('button',name=name,exact=True).click()

    try:
        # Real registration; mode buttons and browser Back retain valid semantics.
        page.goto(base+'/account?mode=login',wait_until='networkidle')
        page.get_by_role('navigation',name='Доступ к аккаунту').get_by_role('button',name='Восстановить').click()
        expect(page.get_by_label('Личный код восстановления')).to_be_visible()
        page.go_back(wait_until='networkidle')
        expect(page.get_by_role('navigation',name='Доступ к аккаунту').get_by_role('button',name='Вход',exact=True)).to_have_attribute('aria-pressed','true')
        email,password,recovery=register(page)
        profile(page,'Первый тестовый малыш',180)
        checked('registration, mode URL/Back, one-time profile onboarding')
        nav('Профиль')
        page.get_by_role('button',name='Профили детей',exact=True).click()
        expect(page.get_by_label('Дата рождения ребёнка')).to_be_disabled()
        page.get_by_label('Имя ребёнка или домашнее имя',exact=False).fill('Первый малыш')
        page.get_by_role('button',name=re.compile('Сохранить имя')).click()
        page.wait_for_load_state('networkidle')
        assert api('session')['state']['profile']['childName']=='Первый малыш'
        checked('locked birth data and editable child name')

        nav('Чат')
        page.get_by_role('button',name=re.compile('Выбрать ребёнка:')).click()
        page.get_by_role('dialog').get_by_role('button',name='Добавить ребёнка',exact=True).click()
        page.wait_for_url('**tab=profile')
        profile(page,'Второй малыш',400)
        second_id=api('session')['state']['activeChildId']
        expect(page.get_by_role('button',name=re.compile('Выбрать ребёнка:'))).to_contain_text('Второй малыш')
        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Черновик второго ребёнка')
        page.reload(wait_until='networkidle')
        expect(page.get_by_role('textbox',name='Ваш вопрос',exact=True)).to_have_value('Черновик второго ребёнка')
        page.get_by_role('button',name=re.compile('Выбрать ребёнка:')).click()
        page.get_by_role('dialog').get_by_role('button',name='Первый малыш',exact=True).click()
        expect(page.get_by_role('textbox',name='Ваш вопрос',exact=True)).to_have_value('')
        assert api('session')['state']['activeChildId']!=second_id
        checked('two children, visible active profile, isolated draft after refresh')

        # Actual deterministic urgent reply; paid provider is disabled in fixture.
        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Ребёнок не дышит')
        page.get_by_role('button',name='Отправить',exact=True).click()
        log=page.get_by_role('log',name='Переписка')
        expect(log.get_by_text('112',exact=False).last).to_be_visible()
        page.wait_for_timeout(100)
        assert log.bounding_box()['y'] < page.locator('.chat-composer').bounding_box()['y'] - 100
        assert page.locator('.child-picker').bounding_box()['y'] >= 0
        page.reload(wait_until='networkidle')
        expect(log.get_by_text('112',exact=False).last).to_be_visible()
        assert log.bounding_box()['y'] < page.locator('.chat-composer').bounding_box()['y'] - 100
        page.get_by_role('button',name='В избранное',exact=True).click()
        expect(page.get_by_role('button',name='В избранном',exact=True)).to_be_disabled()
        nav('Избранное')
        expect(page.get_by_role('heading',name='Ребёнок не дышит',exact=True)).to_be_visible()
        page.get_by_role('button',name='Раздел и заметка',exact=True).click()
        page.get_by_label('Моя заметка',exact=True).fill('Тестовая заметка к ответу')
        page.get_by_role('button',name='Сохранить',exact=True).first.click()
        expect(page.get_by_text('Тестовая заметка к ответу',exact=False)).to_be_visible()
        page.reload(wait_until='networkidle')
        expect(page.get_by_text('Тестовая заметка к ответу',exact=False)).to_be_visible()
        checked('urgent chat answer, favorite and note persisted')

        nav('Чат')
        page.locator('.conversation-settings > summary').click()
        page.get_by_role('button',name='+ Новый диалог',exact=True).click()
        page.get_by_label('Название нового диалога').fill('Тестовый разговор о сне')
        page.get_by_role('button',name='Создать',exact=True).click()
        expect(log.get_by_text('Ребёнок не дышит',exact=True)).not_to_be_visible()
        page.get_by_label('Формат ответа',exact=True).select_option('steps')
        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Отдельный черновик диалога')
        page.get_by_role('navigation',name='Диалоги').get_by_role('button',name='Общий разговор',exact=True).click()
        expect(log.get_by_text('Ребёнок не дышит',exact=True)).to_be_visible()
        expect(page.get_by_role('textbox',name='Ваш вопрос',exact=True)).to_have_value('')
        page.get_by_role('navigation',name='Диалоги').get_by_role('button',name='Тестовый разговор о сне',exact=True).click()
        expect(page.get_by_role('textbox',name='Ваш вопрос',exact=True)).to_have_value('Отдельный черновик диалога')
        checked('new/existing conversations, history and separate draft retained')

        nav('Записи')
        tracker=page.get_by_role('navigation',name='Разделы трекеров')
        tracker.get_by_role('button',name='Прикорм',exact=True).click()
        page.get_by_label('Продукт',exact=True).fill('Тестовый продукт')
        page.get_by_role('button',name='Записать продукт',exact=True).click()
        page.wait_for_load_state('networkidle')
        tracker.get_by_role('button',name='Наши открытия',exact=True).click()
        page.get_by_label('Новое умение или понравившаяся игра').fill('Тестовое открытие')
        page.get_by_role('button',name='Сохранить открытие',exact=True).click()
        page.wait_for_load_state('networkidle')
        tracker.get_by_role('button',name='Как я сегодня',exact=True).click()
        page.get_by_role('button',name='Спокойно',exact=True).click()
        page.wait_for_load_state('networkidle')
        tracker.get_by_role('button',name='К врачу',exact=True).click()
        assert 'tracker=doctor' in page.url
        page.reload(wait_until='networkidle')
        expect(tracker.get_by_role('button',name='К врачу',exact=True)).to_have_attribute('aria-pressed','true')
        expect(page.get_by_label('Предпросмотр сводки')).to_be_visible()
        tracker.get_by_role('button',name='Семья',exact=True).click()
        page.go_back(wait_until='networkidle')
        expect(tracker.get_by_role('button',name='К врачу',exact=True)).to_have_attribute('aria-pressed','true')
        assert len(api('care-list')['records'])==3
        checked('food, development and private mood records; tracker deep link, reload and Back')

        # Two separate signed-in browser contexts, no invitation sent externally.
        tracker.get_by_role('button',name='Семья',exact=True).click()
        page.get_by_role('button',name='Создать приглашение',exact=True).click()
        invitation_text=page.get_by_text('Передайте близкому этот код:',exact=False)
        invitation_text.wait_for()
        invite=invitation_text.locator('strong').inner_text()
        guest_context=browser.new_context(viewport={'width':375,'height':812},reduced_motion='reduce')
        guest=guest_context.new_page(); register(guest); profile(guest,'Синтетический профиль близкого',200)
        guest.goto(base+'/cabinet?tab=trackers&tracker=family',wait_until='networkidle')
        guest.get_by_label('Код приглашения от близкого').fill(invite)
        guest.get_by_role('button',name='Принять приглашение',exact=True).click()
        expect(guest.get_by_text('Доступ активен',exact=False)).to_be_visible()
        guest.get_by_role('navigation',name='Разделы трекеров').get_by_role('button',name='Прикорм',exact=True).click()
        selector=guest.get_by_label('Чьи записи',exact=True)
        selector.select_option(index=1)
        expect(guest.get_by_role('button',name='Записать продукт',exact=True)).to_be_disabled()
        expect(guest.get_by_text('Тестовый продукт',exact=False)).to_be_visible()
        guest_context.close()
        page.reload(wait_until='networkidle')
        page.get_by_role('button',name='Отозвать доступ',exact=True).click()
        expect(page.get_by_role('button',name='Отозвать доступ',exact=True)).not_to_be_visible()
        checked('family invitation, separate account, read-only diary access and revoke')

        nav('Профиль')
        page.get_by_role('button',name='Настройки и уведомления',exact=True).click()
        page.get_by_label('Часовой пояс',exact=True).select_option('Asia/Yekaterinburg')
        page.wait_for_load_state('networkidle')
        page.get_by_label('Утреннее уведомление',exact=True).select_option('10')
        page.wait_for_load_state('networkidle'); page.reload(wait_until='networkidle')
        expect(page.get_by_label('Часовой пояс',exact=True)).to_have_value('Asia/Yekaterinburg')
        expect(page.get_by_label('Утреннее уведомление',exact=True)).to_have_value('10')
        assert api('session')['state']['preferences']['answerStyle']=='steps'
        checked('settings and answer style persisted; no push subscription requested')
        page.get_by_role('button',name='Удалить аккаунт и данные',exact=True).click()
        page.get_by_role('dialog').get_by_role('button',name='Отмена',exact=True).click()
        assert api('session')['user'] is not None
        checked('account deletion can be cancelled without data loss')

        def fail_session(route):
            if route.request.post_data_json.get('action')=='session':
                route.fulfill(status=503,content_type='application/json',body='{"error":"Временная потеря связи"}')
            else: route.continue_()
        page.route('**/api',fail_session)
        page.goto(base+'/cabinet?tab=chat',wait_until='networkidle')
        expect(page.get_by_role('button',name='Повторить загрузку',exact=True)).to_be_visible()
        expect(page.get_by_role('link',name='Срочная помощь · 112',exact=True)).to_be_visible()
        page.unroute('**/api',fail_session)
        page.get_by_role('button',name='Повторить загрузку',exact=True).click()
        expect(page.get_by_role('textbox',name='Ваш вопрос',exact=True)).to_be_visible()
        checked('account service failure has retry and public urgent help; recovery works')

        # Recovery rotates a secret; it remains only in local test memory.
        page.get_by_role('button',name='Выйти',exact=True).click()
        page.goto(base+'/account?mode=login',wait_until='networkidle')
        page.get_by_label('Электронная почта').fill(email)
        page.get_by_label('Пароль',exact=True).fill('synthetic-wrong-password')
        page.get_by_role('button',name='Войти',exact=True).click()
        expect(page.get_by_role('alert')).to_be_visible()
        page.get_by_role('navigation',name='Доступ к аккаунту').get_by_role('button',name='Восстановить').click()
        page.get_by_label('Личный код восстановления').fill(recovery)
        page.get_by_label('Новый пароль',exact=True).fill(secrets.token_urlsafe(24))
        page.get_by_role('button',name=re.compile('Восстановить|Сменить пароль')).last.click()
        page.get_by_role('button',name='Код сохранён — перейти в кабинет').click()
        page.wait_for_url('**/cabinet')
        assert api('session')['state']['profile']['childName']=='Первый малыш'
        assert len(api('session')['state']['favorites'])==1
        checked('wrong-password feedback and genuine recovery preserve profiles/favorites')

        page.goto(base+'/first-aid',wait_until='networkidle')
        assert page.get_by_role('link',name='Позвонить 112',exact=True).get_attribute('href')=='tel:112'
        context.set_offline(True)
        page.locator('.first-aid-card summary').first.click()
        expect(page.get_by_text('Начните сердечно-лёгочную реанимацию.',exact=False)).to_be_visible()
        context.set_offline(False)
        checked('loaded first-aid guide works offline; call links preserved')
        assert not errors, errors
        (out/'flow-results.json').write_text(json.dumps({'checks':checks,'pageErrors':errors,'externalServices':'not used','data':'temporary synthetic accounts'},ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        # No screenshots here: registration/recovery/invitation secrets may be on screen.
        print('FAILED near '+str(len(checks))+' completed groups; URL path='+page.url.split('?')[0],flush=True)
        raise
    finally:
        browser.close()
