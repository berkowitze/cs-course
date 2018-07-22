from oauth2client import file, client, tools
import os

if os.path.exists('credentials.json'):
    import sys
    print 'credentials.json already exists, remove to continue.'
    sys.exit(0)

secret_path = 'client_secret.json'
store = file.Storage('credentials.json')
SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://mail.google.com/',
          'https://www.googleapis.com/auth/spreadsheets']
flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
creds = tools.run_flow(flow, store)

print 'The refresh token is:\n%s' % creds.refresh_token

