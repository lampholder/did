#!/Users/tom/.virtualenvs/did/bin/python3
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

class TimeParser(object):

    @staticmethod
    def is_float(string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    @staticmethod
    def parse_time(text):
        if TimeParser.is_float(text):
            return '%s minutes' % text
        else:
            if len(text.split()) == 2:
                tokens = text.split()
                if TimeParser.is_float(tokens[0]):
                    size = tokens[0]
                    units = tokens[1].lower()[0]
                    if units == 'm':
                        return '%s minutes' % size
                    elif units == 'h':
                        return '%s hours' % size

text = ' '.join(sys.argv[1:]).strip()

home = str(Path.home())
with open('%s/.toggl.json' % home, 'r') as taskfile:
    tasks = json.loads(taskfile.read()).get('tasks')

    items = []
    for task in tasks:
        line = '%s %s %s' % (task.get('client'), task.get('project'), task.get('task'))
        if text is '' or (text.lower() in line.lower() or text.lower().startswith(line.lower())):
            items.append({
                'type': 'task',
                'uid': task.get('tid'),
                'title': line,
                'autocomplete': '%s ' % line
            })

    if len(items) == 1 and text.lower().startswith(items[0].get('title').lower()):
        item = items[0]
        duration_string = TimeParser.parse_time(text[len(item.get('autocomplete')):])
        if duration_string:
            (size, units) = duration_string.split()
            duration = float(size) * 60
            if units == 'hours':
                duration *= 60
        else:
            duration = 0
        duration = int(duration)
        start = datetime.utcnow() - timedelta(seconds=duration)
        print(json.dumps({'items': [{
            'type': 'timesheet',
            'uid': item.get('uid'),
            'title': '%s %s' % (item.get('title'), duration_string if duration_string else ''),
            'arg': json.dumps({
                'time_entry': {
                    'tid': item.get('uid'),
                    'start': '%s+00:00' % start.isoformat()[:19],
                    'duration': duration,
                    'created_with': 'AlfredToggl'
                }
            })
            }]}, indent=2))
    else:
        print(json.dumps({'items': items}, indent=2))
