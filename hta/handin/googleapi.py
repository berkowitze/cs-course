from google.oauth2.credentials import Credentials
from apiclient.discovery import build
import json
from helpers import load_data

data_file = '/course/cs0050/ta/assignments.json'
data = load_data(data_file)

secret_path = 'client_secret.json'
j_creds = json.load(open(secret_path))
client_id = j_creds['installed']['client_id']
client_secret = j_creds['installed']['client_secret']

def sheets_api():
    sheets_refresh_tok_path = 'ref_tok.txt'
    ref_tok = open(sheets_refresh_tok_path).read().strip()
    credentials = Credentials(
        None,
        refresh_token=ref_tok,
        token_uri="https://accounts.google.com/o/oauth2/token",
        client_id=client_id,
        client_secret=client_secret
    )

    ss_id = data['sheet_id']
    rng = '%s!%s%s:%s' % (data['sheet_name'], data['start_col'],
                          data['start_row'], data['end_col'])

    service = build('sheets', 'v4', credentials=credentials)
    return service

def drive_api():
    drive_refresh_token_path = 'ref_tok.txt'
    ref_tok = open(drive_refresh_token_path).read().strip()
    credentials = Credentials(
        None,
        refresh_token=ref_tok,
        token_uri="https://accounts.google.com/o/oauth2/token",
        client_id=client_id,
        client_secret=client_secret
    )

    drive = build('drive', 'v3', credentials=credentials)
    return drive

