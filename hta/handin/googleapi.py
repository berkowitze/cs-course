import json
import sys

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
        return build('sheets', 'v4', credentials=credentials)
    except OSError as e:
        print(f'Sheets network unreachable with errno {e.errno}')
        sys.exit(1)


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
        return build('drive', 'v3', credentials=credentials)
    except OSError as e:
        print(f'Drive network unreachable with errno {e.errno}')
        sys.exit(1)
