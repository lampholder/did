#!/Users/tom/.virtualenvs/did/bin/python3

from pathlib import Path
import os
import psutil


import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta

import requests

class SimpleToggl(object):
    USER_AGENT = 'SimpleToggl'

    def __init__(self, token, workspace_id):
        self._auth = (token, 'api_token')
        self._workspace_id = workspace_id
        self._delay = 0

    def _request(self, *args, **kwargs):
        while True:
            time.sleep(self._delay)
            response = requests.request(*args, **kwargs)
            if response.status_code == 429:
                print('rate limiting')
                self._delay = 1
            else:
                return response

    def clients(self):
        URL = 'https://www.toggl.com/api/v8/workspaces/%s/clients' % self._workspace_id
        query = {
            'user_agent':  self.USER_AGENT
        }
        clients_json = self._request('GET', URL, params=query, auth=self._auth).json()
        return [{
            'id': client.get('id'),
            'name': client.get('name')
            } for client in clients_json]

    def projects(self):
        URL = 'https://www.toggl.com/api/v8/workspaces/%s/projects' % self._workspace_id
        query = {
            'user_agent':  self.USER_AGENT
        }
        projects_json = self._request('GET', URL, params=query, auth=self._auth).json()
        return [{
            'id': project.get('id'),
            'client': project.get('cid'),
            'name': project.get('name')
            } for project in projects_json
            if project.get('cid')] # Forget projects with no client attached.

    def tasks(self, project_id):
        URL = 'https://api.track.toggl.com/api/v8/projects/%s/tasks' % project_id
        query = {
            'user_agent':  self.USER_AGENT
        }
        tasks_json = self._request('GET', URL, params=query, auth=self._auth).json()
        if tasks_json:
            return [{
                'id': task.get('id'),
                'project': task.get('pid'),
                'name': task.get('name')
                } for task in tasks_json]
        else:
            return []

class TimeParser(object):

    @staticmethod
    def parse_time(text):
        if text.isdigit():
            return '%s minutes' % text
        else:
            if len(text.split()) == 2:
                tokens = text.split()
                if tokens[0].isdigit():
                    size = tokens[0]
                    units = tokens[1].lower()[0]
                    if units == 'm':
                        return '%s minutes' % size
                    elif units == 'h':
                        return '%s hours' % size

class FileCache(object):

    def __init__(self, file_path, max_age= 5 * 60 * 1000):
        self._file_path = file_path
        self._max_age = max_age

    def age(self):
        now = int(datetime.utcnow().timestamp() * 1000)
        try:
            modified_time = int(datetime.utcfromtimestamp(os.path.getmtime(self._file_path)).timestamp() * 1000)
        except FileNotFoundError:
            modified_time = 0
        age = now - modified_time
        return age

    def tasks(self):
        try:
            with open(self._file_path, 'r') as f:
                tasks = json.loads(f.read()).get('tasks')
        except FileNotFoundError:
            tasks = []

        if self.age() > self._max_age and not self._refresh_in_progress():
            pid = os.fork()
            if pid == 0: # We're the child
                print('I am fork', file=sys.stderr)
                self._refresh_cache()
                exit(1)
            else:
                print('I am OG', file=sys.stderr)

        return tasks

    def _get_pidfile(self):
        home = str(Path.home())
        pidfile = '%s/.didpid' % home
        return pidfile

    def _refresh_in_progress(self):
        try:
            with open(self._get_pidfile(), 'r') as f:
                return True
            #    pid = int(f.read())
            #if psutil.pid_exists(pid):
            #    return True
            #else:
            #    os.remove(self,_get_pidfile())
            #    return False
        except FileNotFoundError:
            return False
        except ValueError:
            return False

    def _refresh_cache(self):
        with open(self._get_pidfile(), 'w') as f:
            f.write(str(os.getpid()))
        refreshed_content = self.refresh_cache()
        with open(self._file_path, 'w') as f:
            f.write(refreshed_content)
        os.remove(self._get_pidfile())

    def refresh_cache(self):
        raise NotImplementedError

class TogglCache(FileCache):

    def refresh_cache(self):
        st = SimpleToggl(token='4049d5d5f1afc55bf0043376282a220d', workspace_id=2668357)

        def to_id_dict(lst):
            return {x.get('id'): x for x in lst}

        clients = to_id_dict(st.clients())
        projects = st.projects()

        task_list = []

        for project in projects:
            client = clients.get(project.get('client'))
            tasks = st.tasks(project.get('id'))
            for task in tasks:
                task_object = {
                    'client': client.get('name'),
                    'project': project.get('name'),
                    'task': task.get('name'),
                    'tid': task.get('id')
                }
                task_list.append(task_object)

        return json.dumps({'tasks': task_list})

toggl = TogglCache('test.txt')

text = ' '.join(sys.argv[1:]).strip()

items = []
for task in toggl.tasks():
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
        duration = int(size) * 60
        if units == 'hours':
            duration *= 60
    else:
        duration = 0
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
