"""Observed care only: deterministic summaries, no adequacy or sleep predictions."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import sleep_summary


def zone(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        return ZoneInfo('Europe/Moscow')


def parse(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result if result.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def period(records, timezone_name='Europe/Moscow', now=None, days=7):
    now = now or datetime.now(timezone.utc)
    local_zone = zone(timezone_name)
    first_day = now.astimezone(local_zone).date() - timedelta(days=days - 1)
    start = datetime.combine(first_day, datetime.min.time(), local_zone)
    selected = []
    for record in records:
        if record.get('kind') == 'mood':
            continue
        at = parse(record.get('at'))
        if at is None or at > now:
            continue
        end = parse(record.get('end'))
        # An ongoing sleep can start before the selected period.
        overlaps = record.get('kind') == 'sleep' and (end or now) > start
        if at >= start or overlaps:
            selected.append(record)
    return sorted(selected, key=lambda r: parse(r['at']), reverse=True)


def summary(records, timezone_name='Europe/Moscow', now=None):
    now = now or datetime.now(timezone.utc)
    local_zone = zone(timezone_name)
    selected = period(records, str(local_zone), now)
    feeding = [r for r in selected if r.get('kind') == 'feeding']
    sleep = sleep_summary.summary(selected, str(local_zone), now)
    daily = []
    for offset in range(6, -1, -1):
        day = now.astimezone(local_zone).date() - timedelta(days=offset)
        daily.append({'date': str(day), 'recordedFeedings': sum(
            parse(r['at']).astimezone(local_zone).date() == day for r in feeding)})
    return {
        'periodDays': 7,
        'timezone': str(local_zone),
        'periodStart': daily[0]['date'],
        'periodEnd': now.astimezone(local_zone).isoformat(),
        'records': len(selected),
        'recordedDays': sum(d['episodesIntersectingDay'] > 0 or any(
            str(parse(r['at']).astimezone(local_zone).date()) == d['date'] for r in selected)
            for d in sleep['days']),
        'completeness': 'unknown',
        'sleep': sleep,
        'feeding': {
            'records': len(feeding),
            'days': daily,
            'lastRecordedAt': parse(feeding[0]['at']).astimezone(local_zone).isoformat() if feeding else None,
            'ongoingTimers': sum(r.get('value') == 'Таймер кормления' and not r.get('end') for r in feeding),
        },
        'rules': 'Это добровольные записи родителя за семь календарных дней в его часовом поясе. '
                 'Полнота дневника неизвестна. День без записей означает отсутствие данных, '
                 'а не отсутствие сна или кормлений. Число кормлений не определяет достаточность '
                 'питания; таймер без окончания не определяет длительность. Не назначай режим, '
                 'объём питания или точное время следующего сна по этим числам. '
                 'Уточни только недостающие для вопроса обстоятельства, предложи один безопасный '
                 'следующий шаг и способ наблюдать результат без обещания эффекта.',
    }
