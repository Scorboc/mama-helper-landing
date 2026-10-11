"""Whole-interface inspection against the isolated API; only synthetic data.

Run while qa-isolated-api.py and Vite listen on 8787/5173. AXE is local,
version pinned in outputs/qa-impeccable/axe.min.js; no audit data leaves here.
"""
from datetime import date, timedelta
import json
import os
from pathlib import Path
import secrets
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
out = root / 'outputs' / 'qa-impeccable'
phase = os.environ.get('MAMA_QA_PHASE', 'before')
captures = out / phase
captures.mkdir(parents=True, exist_ok=True)
results = []
errors = []
base = 'http://127.0.0.1:5173'

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    context = browser.new_context(viewport={'width':375,'height':812}, reduced_motion='reduce', accept_downloads=True)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))

    def capture(name, screenshot=True):
        page.wait_for_load_state('networkidle')
        page.add_script_tag(path=str(out / 'axe.min.js'))
        audit = page.evaluate('''async () => {
          const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});
          return r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));
        }''')
        geometry = page.evaluate('''() => {
          const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
          const targets=[...document.querySelectorAll('button,a,input,select,textarea,summary,[role="checkbox"]')].filter(visible);
          return {overflow:document.documentElement.scrollWidth>innerWidth+1,width:innerWidth,
          smallTargets:targets.filter(e=>{const r=e.getBoundingClientRect();return r.width<44||r.height<44}).map(e=>({text:(e.getAttribute('aria-label')||e.textContent||e.name||e.tagName).trim().slice(0,100),tag:e.tagName,w:Math.round(e.getBoundingClientRect().width),h:Math.round(e.getBoundingClientRect().height)})),
          headings:[...document.querySelectorAll('h1,h2,h3')].filter(visible).map(e=>e.textContent)};
        }''')
        results.append({'screen':name,'url':page.url,'theme':page.evaluate('document.documentElement.classList.contains("dark")?"dark":"light"'),'axe':audit,**geometry})
        if screenshot:
            page.screenshot(path=str(captures / (name+'.png')), full_page=False)
        print('INSPECTED: '+name+'; axe='+str(len(audit))+'; small='+str(len(geometry['smallTargets']))+'; overflow='+str(geometry['overflow']),flush=True)

    def theme(name):
        page.evaluate('(theme)=>window.mamaTheme.set(theme)',name)

    try:
        for path,name in [('/', 'landing'),('/account','register'),('/account?mode=login','login'),('/account?mode=recover','recover'),('/first-aid','first-aid-public'),('/privacy','privacy'),('/not-a-route','not-found')]:
            page.goto(base+path,wait_until='networkidle')
            for mode in ('light','dark'):
                theme(mode); capture(name+'-'+mode)

        theme('light')
        page.goto(base+'/account',wait_until='networkidle')
        email='impeccable-'+secrets.token_hex(5)+'@example.test'
        password=secrets.token_urlsafe(24)
        page.get_by_label('Электронная почта').fill(email)
        page.get_by_label('Пароль',exact=True).fill(password)
        page.get_by_role('checkbox').check()
        page.get_by_role('button',name='Создать аккаунт',exact=True).click()
        # The recovery secret is never logged, persisted or captured.
        page.get_by_role('button',name='Код сохранён — перейти в кабинет').click()
        page.wait_for_url('**/cabinet')
        expect(page.get_by_role('heading',name='Чат',exact=True)).to_be_visible()
        capture('chat-no-profile')
        page.goto(base+'/cabinet?tab=profile',wait_until='networkidle')
        capture('profile-new')
        page.get_by_label('Имя ребёнка или домашнее имя',exact=False).fill('Тестовый малыш')
        page.locator('label').filter(has_text='Ваш этап').get_by_role('combobox').click()
        page.get_by_role('option',name='Ребёнок родился',exact=True).click()
        page.get_by_label('Дата рождения ребёнка').fill((date.today()-timedelta(days=180)).isoformat())
        page.once('dialog',lambda dialog:dialog.accept())
        page.get_by_role('button',name='Сохранить профиль один раз').click()
        page.wait_for_url('**tab=chat')

        for tab in ('chat','home','trackers','favorites','more','profile','settings','advisor','card','first-aid'):
            page.goto(base+'/cabinet?tab='+tab,wait_until='networkidle')
            for mode in ('light','dark'):
                theme(mode); capture(tab+'-'+mode)
            if tab=='trackers':
                theme('light')
                nav=page.get_by_role('navigation',name='Разделы трекеров')
                for label in ('Скачки роста','Наши открытия','Прикорм','Как я сегодня','К врачу','Семья'):
                    nav.get_by_role('button',name=label,exact=True).click()
                    capture('tracker-'+label)

        for path,name in [('/', 'landing'),('/cabinet?tab=chat','chat'),('/cabinet?tab=trackers','trackers'),('/cabinet?tab=settings','settings'),('/cabinet?tab=profile','profile'),('/first-aid','first-aid-public')]:
            page.goto(base+path,wait_until='networkidle'); theme('light')
            page.set_viewport_size({'width':1280,'height':900}); capture(name+'-desktop')
            page.set_viewport_size({'width':320,'height':740}); capture(name+'-320')
            page.set_viewport_size({'width':375,'height':812})
            page.evaluate("document.documentElement.style.fontSize='24px'")
            capture(name+'-large-text')
            page.evaluate("document.documentElement.style.fontSize=''")

        (out/(phase+'-audit.json')).write_text(json.dumps({'screens':results,'pageErrors':errors,'data':'synthetic temporary database','engine':'Chrome via Playwright; axe-core 4.10.3','physicalDevice':False},ensure_ascii=False,indent=2),encoding='utf-8')
        print('DONE: '+str(len(results))+' states; '+str(len(errors))+' JS errors',flush=True)
    finally:
        browser.close()
