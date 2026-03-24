import requests, json
BASE='http://localhost:8000/api'
sid='79239f77-b45a-4f5f-98cc-31ab7366a58a'
for q in ['Analyze the loan approval patterns in this dataset','Predict whether a new customer will get approved','Show me the distribution of credit scores']:
    print('\n=== QUERY:', q)
    resp = requests.post(BASE+'/query', json={'session_id':sid,'query':q})
    print('Status', resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print('No JSON:', resp.text)
