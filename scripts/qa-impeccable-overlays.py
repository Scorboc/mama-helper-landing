"""Local overlay, consent and recovery checks with synthetic data only.

Notification denial and idea-list failures are simulated. No device permission,
paid provider, external message or real account is used.
"""
from datetime import date, timedelta
import json
from pathlib import Path
import secrets
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[2] / 'outputs/qa-impeccable'
checks, audits, errors = [], [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    context = browser.new_context(viewport={'width':375,'height':812}, reduced_motion='reduce')
    context.add_init_script("""window.permissionCalls=0;
      if(window.Notification) Notification.requestPermission=async()=>{window.permissionCalls++;return 'denied'};
    """)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))

    def audit(name):
        page.add_script_tag(path=str(out/'axe.min.js'))
        violations = page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});return r.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)}))}""")
        audits.append({'screen':name,'violations':violations})
        assert not violations, (name, violations)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(out/'after'/(name+'.png')))
        page.evaluate("window.mamaTheme.set('dark')")
        page.wait_for_timeout(300)
        dark = page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});return r.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)}))}""")
        audits.append({'screen':name+'-dark','violations':dark})
        page.screenshot(path=str(out/'after'/(name+'-dark.png')))
        assert not dark, (name+'-dark',dark)
        page.evaluate("window.mamaTheme.set('light')")
        page.wait_for_timeout(300)

    def checked(name):
        checks.append(name); print('PASS: '+name, flush=True)

    try:
        page.goto('http://127.0.0.1:5173/account', wait_until='networkidle')
        page.get_by_label('Электронная почта').fill('overlay-'+secrets.token_hex(6)+'@example.test')
        page.get_by_label('Пароль', exact=True).fill(secrets.token_urlsafe(24))
        page.get_by_role('checkbox').check()
        page.get_by_role('button', name='Создать аккаунт', exact=True).click()
        page.get_by_role('button', name='Код сохранён — перейти в кабинет').click()
        page.wait_for_url('**/cabinet')
        page.goto('http://127.0.0.1:5173/cabinet?tab=profile', wait_until='networkidle')
        page.get_by_label('Имя ребёнка или домашнее имя',exact=False).fill('Тестовый малыш')
        page.locator('label').filter(has_text='Ваш этап').get_by_role('combobox').click()
        page.get_by_role('option',name='Ребёнок родился',exact=True).click()
        page.get_by_label('Дата рождения ребёнка').fill((date.today()-timedelta(days=180)).isoformat())
        page.once('dialog',lambda d:d.accept())
        page.get_by_role('button',name='Сохранить профиль один раз').click()
        page.wait_for_url('**tab=chat')

        child = page.get_by_role('button',name=__import__('re').compile('Выбрать ребёнка:'))
        child.click(); audit('overlay-child-picker')
        page.keyboard.press('Escape')
        expect(page.get_by_role('dialog')).not_to_be_visible()
        expect(child).to_be_focused()
        checked('child sheet is accessible, Escape closes it and restores focus')

        page.get_by_role('button',name='Голосовой ввод',exact=True).click()
        expect(page.get_by_role('heading',name='Включить микрофон?',exact=True)).to_be_visible()
        audit('overlay-voice-consent')
        page.get_by_role('dialog').get_by_role('button',name='Отмена',exact=True).click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        checked('microphone disclosure can be cancelled before recognition starts')

        def ideas_error(route):
            if route.request.post_data_json.get('action')=='suggestion-list':
                route.fulfill(status=503,content_type='application/json',body='{"error":"Тестовая потеря связи"}')
            else: route.continue_()
        page.route('**/api',ideas_error)
        page.locator('.chat-ideas-button').click()
        expect(page.get_by_role('button',name='Обновить идеи',exact=True)).to_be_visible()
        audit('overlay-ideas-error')
        page.unroute('**/api',ideas_error)
        page.get_by_role('button',name='Обновить идеи',exact=True).click()
        expect(page.get_by_role('button',name='Обновить идеи',exact=True)).not_to_be_visible()
        expect(page.get_by_role('dialog').get_by_text('На этой неделе идей для голосования нет.',exact=True)).to_be_visible()
        audit('overlay-ideas-current-week')
        page.keyboard.press('Escape')
        checked('ideas recover from a failed load; actual weekly voting phase is shown')

        # Explicit UI fixture for the weekday form; the real API enforces its date.
        def collecting(route):
            if route.request.post_data_json.get('action')=='suggestion-list':
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'phase':'collecting','week':'fixture','canSubmit':True,'remainingSubmissions':2,'submissionCount':0,'items':[],'myVote':None,'winners':[]}))
            else: route.continue_()
        page.route('**/api',collecting)
        page.locator('.chat-ideas-button').click()
        expect(page.get_by_role('button',name='Добавить анонимно',exact=True)).to_be_disabled()
        page.get_by_label('Коротко: что добавить или изменить?',exact=True).fill('Тестовое предложение по интерфейсу')
        expect(page.get_by_role('button',name='Добавить анонимно',exact=True)).to_be_enabled()
        audit('overlay-ideas-collecting-fixture')
        page.keyboard.press('Escape'); page.unroute('**/api',collecting)
        checked('weekday idea form has labels and minimum-length validation (UI fixture, no submission)')

        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Ребёнок не дышит')
        page.get_by_role('button',name='Отправить',exact=True).click()
        page.get_by_role('log',name='Переписка').get_by_role('button',name='Не помогло',exact=True).click()
        expect(page.get_by_role('dialog').get_by_role('checkbox')).not_to_be_checked()
        audit('overlay-feedback-consent')
        page.get_by_role('dialog').get_by_label('Комментарий — необязательно',exact=True).fill('Синтетический отзыв о читаемости')
        page.get_by_role('dialog').get_by_role('button',name='Отправить',exact=True).click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        expect(page.get_by_role('log',name='Переписка').get_by_text('Спасибо! Отзыв сохранён для разработчика.',exact=True)).to_be_visible()
        checked('feedback saved through actual API without consenting to attach profile/history')

        page.goto('http://127.0.0.1:5173/cabinet?tab=settings',wait_until='networkidle')
        assert page.evaluate('window.permissionCalls')==0
        page.get_by_role('button',name='Включить push',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('Уведомления не разрешены')
        assert page.evaluate('window.permissionCalls')==1
        expect(page.get_by_role('button',name='Включить push',exact=True)).to_be_enabled()
        checked('push permission is requested only after a click; simulated refusal leaves account usable')

        page.get_by_role('button',name='Удалить аккаунт и данные',exact=True).click()
        audit('overlay-delete-account')
        page.get_by_role('dialog').get_by_role('button',name='Отмена',exact=True).click()
        checked('delete-account sheet has clear confirmation and a working cancel')
        assert not errors, errors
        (out/'overlay-results.json').write_text(json.dumps({'checks':checks,'audits':audits,'pageErrors':errors,'permissions':'simulated refusal; no subscription','data':'temporary synthetic database'},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        browser.close()
