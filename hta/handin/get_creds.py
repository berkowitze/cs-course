import os
from oauth2client import client, file, tools
# this script gets a refresh token using credentials.json
# you will need to copy the refresh token into ref_tok.txt
os.umask(0o007)
if os.path.exists('credentials.json'):
    import sys
    print('credentials.json already exists, remove to continue.')
    sys.exit(1)

secret_path = 'client_secret.json'
store = file.Storage('credentials.json')
SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://mail.google.com/',
          'https://www.googleapis.com/auth/spreadsheets']
flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
creds = tools.run_flow(flow, store)
os.umask(0o007)
ref_tok = creds.refresh_token
print(f'Refresh Token: {ref_tok}')
with open('ref_tok.txt', 'w') as f:
    f.write(ref_tok)

print(f'Written to ref_tok.txt')
