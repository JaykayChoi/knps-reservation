from datetime import date, timedelta

DAY_NUMBERS = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3,
               'Fri': 4, 'Sat': 5, 'Sun': 6}
MAX_EXPLICIT_DAYS = 120


def knps_target_dates(options: dict, *, today: date) -> list[str]:
    dates: set[date] = set()
    if options.get('date_mode') == 'weekday':
        selected = {DAY_NUMBERS[day] for day in options.get('days', [])}
        for offset in range(options.get('weeks_ahead', 0) * 7):
            candidate = today + timedelta(days=offset)
            if candidate.weekday() in selected:
                dates.add(candidate)

    start = options.get('start_date')
    end = options.get('end_date')
    if start and end:
        current, stop = date.fromisoformat(start), date.fromisoformat(end)
        for _ in range(MAX_EXPLICIT_DAYS):
            if current > stop:
                break
            dates.add(current)
            current += timedelta(days=1)
    return [value.strftime('%Y%m%d') for value in sorted(dates)]
