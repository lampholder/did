#!/Users/tom/.virtualenvs/did/bin/python3
import time
import json
from pathlib import Path

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

home = str(Path.home())
with open('%s/.toggl.json' % home, 'w') as taskfile:
    taskfile.write(json.dumps({'tasks': task_list}))
