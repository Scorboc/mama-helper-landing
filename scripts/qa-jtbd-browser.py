"""Browser regression with real local API and synthetic records only.

Run with the isolated API fixture and Vite. Needs Python Playwright and Chrome.
Never point this script at production or an existing user database.
"""
from datetime import date, timedelta
import json
from pathlib import Path
import secrets
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
out = root / 'outputs' / 'qa-v3'
out.mkdir(parents=True, exist_ok=True)
checks = []


def checked(name):
    checks.append(name)
    print('PASS: ' + name, flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    context = browser.new_context(viewport={'width':375,'height':812}, reduced_motion='reduce', accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto('http://127.0.0.1:5173/account', wait_until='networkidle')
        # Registration is real; its recovery code is never printed or captured.
        page.get_by_label('Электронная почта').fill('jtbd-'+secrets.token_hex(5)+'@example.test')
        page.get_by_label('Пароль', exact=True).fill(secrets.token_urlsafe(24))
        page.get_by_role('checkbox').check()
        page.get_by_role('button', name='Создать аккаунт', exact=True).click()
        page.get_by_role('button', name='Код сохранён — перейти в кабинет').click()
        page.wait_for_url('**/cabinet')
        checked('registration and authenticated cabinet')
        page.goto('http://127.0.0.1:5173/cabinet?tab=profile', wait_until='networkidle')
        page.get_by_label('Имя ребёнка или домашнее имя', exact=False).fill('Тестовый малыш')
        page.locator('label').filter(has_text='Ваш этап').get_by_role('combobox').click()
        page.get_by_role('option', name='Ребёнок родился', exact=True).click()
        page.get_by_label('Дата рождения ребёнка').fill((date.today()-timedelta(days=180)).isoformat())
        page.once('dialog',lambda dialog: dialog.accept())  # synthetic one-time profile confirmation
        page.get_by_role('button', name='Сохранить профиль один раз').click()
        page.wait_for_url('**tab=chat')
        quick = page.get_by_role('region',name='Быстрые отметки')
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_enabled()
        checked('one-time profile onboarding and chat-first return')

        # API queries through the real signed-in browser; report only counts.
        def api(action, **data):
            result=page.evaluate('''async payload => {
              const r=await fetch('/api',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
              return {status:r.status,body:await r.json()};
            }''', {'action':action, **data})
            assert result['status']==200, (action,result['status'])
            return result['body']

        quick.get_by_role('button',name='Сон',exact=True).click()
        quick.get_by_role('button',name='Дневной сон',exact=True).click()
        expect(quick.get_by_role('button',name='Проснулся',exact=True)).to_be_enabled()
        quick.get_by_role('button',name='Проснулся',exact=True).click()
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_enabled()
        quick.get_by_role('button',name='Кормление',exact=True).click()
        quick.get_by_role('button',name='ГВ · левая',exact=True).click()
        expect(quick.get_by_text('Отметка сохранена в дневнике',exact=True)).to_be_visible()
        expect(quick.get_by_role('button',name='Кормление',exact=True)).to_be_enabled()
        quick.get_by_role('button',name='Утренний подъём',exact=True).click()
        expect(quick.get_by_role('button',name='Заметка',exact=True)).to_be_enabled()
        quick.get_by_role('button',name='Заметка',exact=True).click()
        quick.get_by_label('Что хотите отметить?').fill('Синтетическая заметка для проверки')
        quick.get_by_role('button',name='Сохранить заметку',exact=True).click()
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_enabled()
        listing=api('care-list')
        assert len(listing['records'])==4
        assert listing['summary']['feeding']['records']==1
        assert listing['summary']['sleep']['sleepRecords']==1
        checked('sleep, feeding, wake and note saved in the same diary')

        # Lose the acknowledgement AFTER a genuine committed write.
        def lose_response(route):
            if route.request.post_data_json.get('action')=='care-put':
                route.fetch()  # server commit, then simulate dropped response
                route.abort('failed')
            else:
                route.continue_()
        page.route('**/api',lose_response)
        quick.get_by_role('button',name='Кормление',exact=True).click()
        quick.get_by_role('button',name='Бутылочка',exact=True).click()
        expect(quick.get_by_role('button',name='Повторить сохранение',exact=True)).to_be_visible()
        page.unroute('**/api',lose_response)
        quick.get_by_role('button',name='Повторить сохранение',exact=True).click()
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_enabled()
        assert len(api('care-list')['records'])==5
        checked('lost save acknowledgement retries without duplicate')

        page.reload(wait_until='networkidle')
        expect(quick.get_by_text('Записи за 7 дней · 5',exact=True)).to_be_visible()
        quick.locator('summary').click()
        expect(quick.get_by_text('Эпизодов сна: 1.',exact=False)).to_be_visible()
        for width,height,name in [(375,812,'phone-light'),(812,375,'landscape'),(768,1024,'tablet')]:
            page.set_viewport_size({'width':width,'height':height})
            quick.scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            assert all(button.bounding_box()['height']>=44 for button in quick.get_by_role('button').all())
            composer=page.get_by_role('textbox',name='Ваш вопрос',exact=True).bounding_box()
            assert composer['y'] >= 0 and composer['y']+composer['height'] <= height-74
            urgent=page.get_by_role('link',name='Срочная помощь · 112',exact=True).bounding_box()
            assert urgent['y'] >= 0 and urgent['y']+urgent['height'] <= height-74
            page.screenshot(path=str(out/(name+'.png')))
        checked('375px, landscape and tablet: no horizontal overflow; quick targets at least 44px')
        page.set_viewport_size({'width':375,'height':812})
        page.evaluate("document.documentElement.style.fontSize='24px'")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        composer=page.get_by_role('textbox',name='Ваш вопрос',exact=True).bounding_box()
        assert composer['y']+composer['height'] <= 812-74
        page.screenshot(path=str(out/'phone-large-text.png'))
        page.evaluate("document.documentElement.style.fontSize=''")
        checked('question composer stays visible above navigation including larger text')
        page.evaluate("document.documentElement.classList.add('dark')")
        page.screenshot(path=str(out/'phone-dark.png'))
        page.evaluate("document.documentElement.classList.remove('dark')")
        checked('dark and reduced-motion rendered')

        quick.get_by_role('button',name='Графики',exact=True).click()
        page.wait_for_url('**tab=trackers')
        expect(page.get_by_role('navigation',name='Разделы трекеров')).to_be_visible()
        page.get_by_role('navigation',name='Разделы трекеров').get_by_role('button',name='К врачу',exact=True).click()
        preview=page.get_by_label('Предпросмотр сводки',exact=True)
        expect(preview).to_have_value(__import__('re').compile('.*отметок кормлений: 2.*',__import__('re').DOTALL))
        with page.expect_download() as download_info:
            page.get_by_role('button',name='Скачать сводку',exact=True).click()
        download=download_info.value
        report_path=out/'synthetic-consultation.txt'
        download.save_as(report_path)
        report=report_path.read_text(encoding='utf-8')
        assert 'Полнота дневника неизвестна' in report
        assert 'Синтетическая заметка для проверки' in report
        checked('graphs navigation, specialist preview and actual text download')

        # A failed load must not present actionable stale controls.
        def fail_list(route):
            if route.request.post_data_json.get('action')=='care-list':
                route.fulfill(status=503,content_type='application/json',body='{"error":"Тестовая потеря связи"}')
            else:route.continue_()
        page.route('**/api',fail_list)
        page.goto('http://127.0.0.1:5173/cabinet?tab=chat',wait_until='networkidle')
        expect(quick.get_by_text('Не удалось обновить дневник.',exact=False)).to_be_visible()
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_disabled()
        page.unroute('**/api',fail_list)
        quick.get_by_role('button',name='Обновить дневник',exact=True).click()
        expect(quick.get_by_role('button',name='Сон',exact=True)).to_be_enabled()
        checked('load failure disables unsafe actions and recovers with retry')

        # Existing profile data and dialogs stay intact through new actions.
        session=api('session')
        assert session['state']['profile']['childName']=='Тестовый малыш'
        assert session['state']['profile']['birthDate']==(date.today()-timedelta(days=180)).isoformat()
        assert len(api('care-list')['records'])==5
        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Ребёнок не дышит')
        page.get_by_role('button',name='Отправить',exact=True).click()
        expect(page.get_by_role('log',name='Переписка').get_by_text('112',exact=False).last).to_be_visible()
        checked('local emergency response remains available without an AI provider')
        page.get_by_role('link',name='Срочная помощь · 112',exact=True).click()
        page.wait_for_url('**/first-aid')
        assert '112' in page.inner_text('body')
        checked('public urgent-help route')
        assert not errors, errors
        (out/'browser-results.json').write_text(json.dumps({'checks':checks,'pageErrors':errors,'externalAI':'not called','data':'synthetic temporary database'},ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        if '/cabinet' in page.url or '/first-aid' in page.url:
            page.screenshot(path=str(out/'failure.png'),full_page=True)
            print(json.dumps({'url':page.url,'alerts':page.get_by_role('alert').all_text_contents()},ensure_ascii=False),flush=True)
        raise
    finally:
        browser.close()
