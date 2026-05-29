import requests, json
BASE='http://127.0.0.1:8000'
# login
r = requests.post(f'{BASE}/api/auth/login', data={'username':'devuser','password':'password'})
print('login', r.status_code, r.text)
if r.status_code!=200:
    raise SystemExit(1)
token = r.json().get('access_token')
headers={'Authorization': f'Bearer {token}'}
# create workspace
r = requests.post(f'{BASE}/api/workspaces/', json={'name':'dev-ws','description':'test'}, headers=headers)
print('create workspace', r.status_code, r.text)
if r.status_code not in (200,201):
    raise SystemExit(1)
ws = r.json().get('id')
# upload dataset
files = {'file': open('../data/sample_data.csv','rb')}
r = requests.post(f'{BASE}/api/workspaces/{ws}/datasets/upload', files=files, headers=headers)
print('upload', r.status_code, r.text)
