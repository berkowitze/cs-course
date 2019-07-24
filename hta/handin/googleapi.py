import json
import sys
import httplib2

from apiclient.discovery import Resource, build
from google.oauth2.credentials import Credentials
from helpers import BASE_PATH, locked_file, pjoin

client_path = pjoin(BASE_PATH, 'hta/handin/client_secret.json')
with locked_file(client_path) as f:
    j_creds = json.load(f)

client_id = j_creds['installed']['client_id']
client_secret = j_creds['installed']['client_secret']

ref_tok_path = pjoin(BASE_PATH, 'hta/handin/ref_tok.txt')
with locked_file(ref_tok_path) as f:
    ref_tok: str = f.read().strip()

def sheets_api() -> Resource:
    credentials = Credentials(
        None,
        refresh_token=ref_tok,
        token_uri="https://accounts.google.com/o/oauth2/token",
        client_id=client_id,
        client_secret=client_secret
    )
    try:
        sheets = build('sheets', 'v4', credentials=credentials)
    except httplib2.ServerNotFoundError:
        print('httplib2 exception in sheets build')
        sys.exit(1)
    except Exception as e:
        print(f'{e} exception in sheets build')
        sys.exit(1)

    return sheets


def drive_api() -> Resource:
    with locked_file(ref_tok_path) as f:
        ref_tok = f.read().strip()

    credentials = Credentials(
        None,
        refresh_token=ref_tok,
        token_uri="https://accounts.google.com/o/oauth2/token",
        client_id=client_id,
        client_secret=client_secret
    )
    try:
        drive = build('drive', 'v3', credentials=credentials)
    except httplib2.ServerNotFoundError:
        print('httplib2 exception in drive build')
        sys.exit(1)
    except Exception as e:
        print(f'{e} exception in drive build')
        sys.exit(1)

    return drive
