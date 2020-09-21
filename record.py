#!/Users/tom/.virtualenvs/toggl/bin/python3

import sys
import json
import requests

timesheet = json.loads(sys.argv[1])

URL = 'https://www.toggl.com/api/v8/time_entries'
AUTH = ('4049d5d5f1afc55bf0043376282a220d', 'api_token')
response = requests.post(URL, json=timesheet, auth=AUTH)
if response.status_code == 200:
    print('SUCCESS')
else:
    print('%s - %s' % (response.status_code, response.text))
