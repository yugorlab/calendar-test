#!/usr/bin/env python3
"""Read Kyodo's PUBLIC Google Calendar iCal feed and build events.json.

Google Calendar all-day DTEND is exclusive; JSON endDate is inclusive.
This importer intentionally does not add links to event posts.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, parse_qs, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

CALENDAR_ID = 'c_397b4b3ccea8f0a91a944db587fc05e95690679f2b1dbeaeb7bd902416092d6a@group.calendar.google.com'
CALENDAR_TIMEZONE = ZoneInfo('America/New_York')
CALENDAR_URL = 'https://calendar.google.com/calendar/ical/' + quote(CALENDAR_ID, safe='') + '/public/basic.ics'
LANGUAGE_RE = re.compile(r'^\s*[\[(](EN|ES|PT|FR|RU|DE|AR)(?:[-_]BR)?[\])]\s*', re.I)
URL_RE = re.compile(r'https?://[^\s<>"\']+', re.I)
IMAGE_RE = re.compile(r'\.(?:png|jpe?g|webp|gif)(?:\?|#|$)', re.I)


def unescape(value: str) -> str:
    return re.sub(r'\\([nN,;\\])', lambda m: '\n' if m.group(1) in ('n','N') else m.group(1), value)


def properties(text: str) -> list[dict[str, list[tuple[str, dict[str,str]]]]]:
    lines: list[str] = []
    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if line.startswith((' ', '\t')) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    events = []
    event = None
    depth = 0
    for line in lines:
        if line == 'BEGIN:VEVENT':
            event = {}
            depth = 1
            continue
        if line == 'END:VEVENT':
            if event is not None:
                events.append(event)
            event = None
            depth = 0
            continue
        if event is None:
            continue
        if line.startswith('BEGIN:'):
            depth += 1
            continue
        if line.startswith('END:'):
            depth -= 1
            continue
        if depth != 1 or ':' not in line:
            continue
        left, val = line.split(':', 1)
        bits = left.split(';')
        name = bits[0].upper()
        args = {}
        for b in bits[1:]:
            if '=' in b:
                k, v = b.split('=',1)
                args[k.upper()] = v.strip('"')
        event.setdefault(name, []).append((val, args))
    return events


def first(event, key, default=''):
    return event.get(key, [(default, {})])[0][0]


def parse_start(value, opts):
    if opts.get('VALUE', '').upper() == 'DATE' or re.fullmatch(r'\d{8}',value):
        return date.fromisoformat(f'{value[:4]}-{value[4:6]}-{value[6:8]}'), True
    tz = ZoneInfo(opts.get('TZID', 'America/New_York').lstrip('/')) if not value.endswith('Z') else timezone.utc
    if value.endswith('Z'):
        x = datetime.strptime(value,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    else:
        fmt = '%Y%m%dT%H%M%S' if len(value)==15 else '%Y%m%dT%H%M'
        x = datetime.strptime(value,fmt).replace(tzinfo=tz)
    return x, False


def event_dates(event):
    starts = event.get('DTSTART', [])
    if not starts:
        return None
    start, all_day = parse_start(*starts[0])
    ends = event.get('DTEND', [])
    end, _ = parse_start(*ends[0]) if ends else (start + timedelta(days=1) if all_day else start, all_day)
    if all_day:
        # Exclusive DTEND, including when the source has an all-day event of one day.
        finish = (end if isinstance(end,date) and not isinstance(end,datetime) else end.date()) - timedelta(days=1)
        if not ends: finish = start
        return start, max(start, finish), start, end, True
    # For timed events, derive the local calendar date; 00:00 end is exclusive.
    start_local = start.astimezone(CALENDAR_TIMEZONE)
    end_local = end.astimezone(CALENDAR_TIMEZONE)
    finish = end_local.date() - (timedelta(days=1) if end_local.time().hour == 0 and end_local.time().minute == 0 and end_local.time().second == 0 and end_local > start_local else timedelta(0))
    return start_local.date(), max(start_local.date(),finish), start, end, False


def as_url(raw):
    raw = raw.strip().rstrip('.,);')
    p = urlsplit(raw)
    return raw if p.scheme in ('https','http') and p.netloc else ''


def google_drive_thumbnail(url):
    parsed = urlsplit(url)
    if parsed.hostname not in ('drive.google.com','docs.google.com'):
        return ''
    m = re.search(r'/file/d/([\w-]+)', parsed.path)
    file_id = m.group(1) if m else parse_qs(parsed.query).get('id', [''])[0]
    return 'https://drive.google.com/thumbnail?id='+quote(file_id)+'&sz=w1000' if file_id else ''


def event_picture(event, description):
    # Public Google Calendar attachments may NOT appear in iCal. Only actual accessible URLs can be used.
    for raw, opts in event.get('ATTACH', []):
        url = as_url(raw)
        label = opts.get('FILENAME','')
        mime = opts.get('FMTTYPE','')
        is_image = mime.lower().startswith('image/') or IMAGE_RE.search(urlsplit(url).path) or IMAGE_RE.search(label)
        if not url or not is_image:
            continue
        if google_drive_thumbnail(url):
            return google_drive_thumbnail(url)
        if IMAGE_RE.search(urlsplit(url).path):
            return url
    for candidate in URL_RE.findall(description):
        candidate = as_url(candidate)
        if candidate and IMAGE_RE.search(urlsplit(candidate).path):
            return candidate
    return ''


def parse_event(event, override_date=None):
    dates = event_dates(event)
    if not dates:
        return None
    start, end, start_full, end_full, all_day = dates
    if override_date is not None:
        duration = end - start
        start = override_date
        end = start + duration
    original = unescape(first(event,'SUMMARY')).strip()
    if not original:
        return None
    lang = ''
    match = LANGUAGE_RE.match(original)
    if match:
        lang = match.group(1).upper()
        original = original[match.end():].strip()
    desc = unescape(first(event,'DESCRIPTION')).strip()
    location = unescape(first(event,'LOCATION')).strip()
    location_url = as_url(location)
    circle_url = location_url if 'kyodo.app' in urlsplit(location_url).netloc.lower() else ''
    circle = location if not location_url else ('Открыть круг' if circle_url else '')
    if location.lower() in ('kyodo', 'official kyodo', 'kyodo community'):
        circle = 'Всё сообщество Кёдо'
    # Optional richer text labels: 'Circle: My Circle' in description.
    m = re.search(r'(?im)^\s*(?:circle|круг)\s*:\s*([^\n]+)', desc)
    if m and not as_url(m.group(1).strip()):
        circle = m.group(1).strip()
    cancelled = first(event,'STATUS').upper() == 'CANCELLED' or bool(re.match(r'^\s*(?:\[cancelled\]|\(cancelled\)|отмен[её]н(?:о|а)?:)',original,re.I))
    uid = first(event,'UID') or (first(event,'SUMMARY')+start.isoformat())
    # Deterministic hash prevents clashing even with recurring calendar events.
    eid = hashlib.sha1((uid+'|'+start.isoformat()).encode('utf-8')).hexdigest()[:16]
    return {
        'id': eid,
        'name': original,
        'startDate': start.isoformat(),
        'endDate': end.isoformat(),
        'language': lang,
        'circle': circle,
        'circleUrl': circle_url,
        'prizeImage': event_picture(event, desc),
        'cancelled': cancelled,
    }


def convert(ics: str) -> list[dict]:
    events = properties(ics)
    if not events:
        raise ValueError('В iCal-ответе нет VEVENT. Проверьте общедоступность календаря и ссылку.')
    records = {}
    # Recurrence is uncommon here; support simple occurrences as supplied by Google.
    for event in events:
        rec = parse_event(event)
        if rec:
            records[rec['id']] = rec
    if not records:
        raise ValueError('Календарь не содержит пригодных датированных ивентов.')
    return sorted(records.values(), key=lambda x:(x['startDate'],x['name']))


def fetch_calendar() -> str:
    request = Request(CALENDAR_URL, headers={'User-Agent':'KyodoEventsCalendarSync/0.2 (+GitHub Pages)','Accept':'text/calendar,*/*'})
    with urlopen(request, timeout=35) as response:
        data = response.read(12_000_000)
        if len(data) >= 12_000_000:
            raise ValueError('Calendar feed is larger than allowed limit.')
    text = data.decode('utf-8-sig', errors='replace')
    if 'BEGIN:VCALENDAR' not in text:
        raise ValueError('Ответ Google не является iCal. Возможно, календарь не открыт для просмотра подробностей.')
    return text


def main():
    ap = argparse.ArgumentParser(description='Sync Kyodo calendar to JSON')
    ap.add_argument('--ics-file',help='Local .ics fixture, for testing without network')
    ap.add_argument('--output',default='events.json')
    args = ap.parse_args()
    text = Path(args.ics_file).read_text(encoding='utf-8') if args.ics_file else fetch_calendar()
    new_events = convert(text)
    out = Path(args.output)
    if out.exists():
        try:
            old = json.loads(out.read_text(encoding='utf-8'))
            if old.get('events') == new_events:
                print(f'No changes ({len(new_events)} events).')
                return
        except (ValueError,TypeError,AttributeError):
            pass
    payload = {'calendar':'Official Kyodo Events!','timezone':'America/New_York',
               'updatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'events':new_events}
    out.parent.mkdir(parents=True,exist_ok=True)
    temp = out.with_suffix('.json.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,out)
    print(f'Updated {out} with {len(new_events)} calendar events.')


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        print(f'Calendar synchronization failed: {err}',file=sys.stderr)
        sys.exit(1)
