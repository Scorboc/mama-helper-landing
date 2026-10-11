"""Check emitted assets and lazy-route failure, entirely on loopback.

Port 5174 serves dist/. QA-only bridge forwards API requests to the isolated
5173 proxy with its allowlisted origin; application security config is untouched.
"""
from datetime import date, timedelta
import json
from pathlib import Path
import secrets
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[2] / 'outputs/qa-impeccable'
checks = []

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(viewport={'width':375,'height':812},reduced_motion='reduce')
    page=context.new_page(); errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))

    def bridge(route):
        req=route.request
        response=context.request.post('http://127.0.0.1:5173/api',data=req.post_data,
            headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:5173'})
        route.fulfill(response=response)

    page.route('**/api',bridge)
    try:
        for path,heading in [('/',None),('/account?mode=login','Своя маленькая опора'),('/privacy','Данные в тестовой версии'),('/first-aid','Первая помощь'),('/does-not-exist','Страница не найдена')]:
            page.goto('http://127.0.0.1:5174'+path,wait_until='networkidle')
            if heading: expect(page.get_by_role('heading',name=heading,exact=True)).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        checks.append('direct production routes: landing, account, privacy, first aid and 404')
        page.goto('http://127.0.0.1:5174/account',wait_until='networkidle')
        page.get_by_label('Электронная почта').fill('built-'+secrets.token_hex(6)+'@example.test')
        page.get_by_label('Пароль',exact=True).fill(secrets.token_urlsafe(24))
        page.get_by_role('checkbox').check()
        page.get_by_role('button',name='Создать аккаунт',exact=True).click()
        page.get_by_role('button',name='Код сохранён — перейти в кабинет').click()
        page.wait_for_url('**/cabinet')
        page.goto('http://127.0.0.1:5174/cabinet?tab=profile',wait_until='networkidle')
        page.get_by_label('Имя ребёнка или домашнее имя',exact=False).fill('Тестовый малыш')
        page.locator('label').filter(has_text='Ваш этап').get_by_role('combobox').click()
        page.get_by_role('option',name='Ребёнок родился',exact=True).click()
        page.get_by_label('Дата рождения ребёнка').fill((date.today()-timedelta(days=180)).isoformat())
        page.once('dialog',lambda d:d.accept())
        page.get_by_role('button',name='Сохранить профиль один раз').click()
        page.wait_for_url('**tab=chat')
        for theme in ('light','dark'):
            page.evaluate('(value)=>window.mamaTheme.set(value)',theme)
            page.add_script_tag(path=str(out/'axe.min.js'))
            violations=page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});return r.violations.map(v=>v.id)}""")
            assert not violations, violations
            assert page.get_by_role('button',name='Голосовой ввод',exact=True).bounding_box()['width']>=44
            page.screenshot(path=str(out/'after'/('built-chat-'+theme+'.png')))
        checks.append('built chat: actual registration/profile via isolated API bridge, light/dark AXE, composer targets')
        page.get_by_role('textbox',name='Ваш вопрос',exact=True).fill('Ребёнок не дышит')
        page.get_by_role('button',name='Отправить',exact=True).click()
        log=page.get_by_role('log',name='Переписка')
        expect(log.get_by_text('112',exact=False).last).to_be_visible()
        page.wait_for_timeout(150)
        assert 60 <= log.bounding_box()['y'] < page.locator('.chat-composer').bounding_box()['y']-100
        page.reload(wait_until='networkidle')
        expect(log.get_by_text('112',exact=False).last).to_be_visible()
        assert log.bounding_box()['y'] < page.locator('.chat-composer').bounding_box()['y']-100
        page.screenshot(path=str(out/'after'/'built-chat-response.png'))
        checks.append('built chat scrolls to reply and returns to conversation after reload; child selector remains visible')
        assert not errors, errors

        # Fresh context: a route module fails to download. Shared first aid is
        # already in the entry bundle and does not need that failed module.
        fallback_context=browser.new_context(viewport={'width':375,'height':812},reduced_motion='reduce')
        fallback=fallback_context.new_page()
        fallback.route('**/assets/ParentWorkspace-*.js',lambda r:r.abort('failed'))
        fallback.goto('http://127.0.0.1:5174/cabinet',wait_until='networkidle')
        expect(fallback.get_by_role('heading',name='Не удалось открыть страницу',exact=True)).to_be_visible()
        assert fallback.get_by_role('link',name='Позвонить 112',exact=True).get_attribute('href')=='tel:112'
        fallback_context.set_offline(True)
        fallback.get_by_text('Открыть памятку первой помощи',exact=True).click()
        expect(fallback.get_by_role('heading',name='Сначала вызовите помощь',exact=True)).to_be_visible()
        fallback.locator('.first-aid-card summary').first.click()
        expect(fallback.get_by_text('Начните сердечно-лёгочную реанимацию.',exact=False)).to_be_visible()
        fallback_context.set_offline(False)
        fallback.screenshot(path=str(out/'after'/'built-chunk-failure-help.png'))
        checks.append('failed lazy-route download: recovery screen, native call and loaded first-aid guide work offline')
        fallback_context.close()
        (out/'build-results.json').write_text(json.dumps({'checks':checks,'pageErrors':errors,'build':'dist assets','API':'isolated QA bridge, no production configuration changes','externalAI':'disabled','coldOffline':'not supported or claimed'},ensure_ascii=False,indent=2),encoding='utf-8')
        for item in checks: print('PASS: '+item,flush=True)
    finally:
        browser.close()
