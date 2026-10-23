"""Owner-only Telegram summary of local, aggregate MAMA control data."""
import importlib.util


def summary(root):
    path = root.parent.parent / 'marketing-automation' / 'control.py'
    if not path.is_file():
        return 'Контроль продвижения пока недоступен: локальная студия не найдена.'
    spec = importlib.util.spec_from_file_location('mama_marketing_control', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build(root=root.parent.parent)
    good = sum(item['status'] == 'ok' for item in report['services'].values())
    product = report['product']
    ai = report['ai_spend']
    marketing = report['marketing']
    lines = [f'MAMA: контроль проекта\nЛокальные сервисы: {good}/{len(report["services"])} отвечают.',
             f'Активные схемы n8n: {report["automation"]["active"] if report["automation"]["active"] is not None else "нет данных"}.']
    lines.append(f'Копия: {report["backup"].get("age_hours", "—")} ч назад; '
                 f'проверка восстановления: {report["restore"].get("age_hours", "—")} ч назад.')
    if product['status'] == 'ok':
        lines.append(f'За 7 дней: полезное действие сделали {product["activated_people"]} участников; '
                     f'вызовов ИИ {product["ai_calls"]}, технических ошибок {product["ai_errors"]}.')
    else:
        lines.append('Продуктовая статистика: нет данных.')
    if ai['status'] == 'ok':
        cap=report['ai_limits'].get('monthly_cap_rub')
        lines.append(f'Учтённый расход ИИ в этом месяце: {ai["accounted_rub"]} ₽'
                     + (f' из лимита {cap:g} ₽' if cap is not None else '')
                     + ' (включая резерв; сверить с провайдером).')
    balance = report['proxy_balance']
    if balance['status'] == 'ok':
        label = 'бюджет ключа' if balance['scope'] == 'key-budget' else 'баланс аккаунта'
        lines.append(f'ProxyAPI: {label} {balance["balance_rub"]} ₽; проверено {balance["age_minutes"]} мин. назад.')
    else:
        lines.append('ProxyAPI: текущий остаток не подтверждён; /balance — подробности.')
    if marketing['status'] == 'ok':
        lines.append(f'Продвижение: подтверждённых релизов {marketing["verified_release_events"]}, '
                     f'нетестовых черновиков {marketing["real_drafts"]}, записей метрик {marketing["metric_records"]}.')
    lines.append('Выручка: не подтверждена — платёжный провайдер не подключён.')
    lines.extend(f'{item["priority"]}: {item["message"]}' for item in report['alerts'][:4])
    lines.append('Подробности: локальная панель http://127.0.0.1:8793/ → Контроль. Публикация отключена.')
    return '\n'.join(lines)
