import asyncio
import os
import string
import random

from typing import Dict

from datetime import datetime, date

import json

from google_auth_oauthlib.flow import Flow

async def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

async def print_index_table():
    return ('<table>' +
            '<tr><td><a href="/test">Test an API request</a></td>' +
            '<td>Submit an API request and see a formatted JSON response. ' +
            '    Go through the authorization flow if there are no stored ' +
            '    credentials for the user.</td></tr>' +
            '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
            '<td>Go directly to the authorization flow. If there are stored ' +
            '    credentials, you still might not be prompted to reauthorize ' +
            '    the application.</td></tr>' +
            '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
            '<td>Revoke the access token associated with the current user ' +
            '    session. After revoking credentials, if you go to the test ' +
            '    page, you should see an <code>invalid_grant</code> error.' +
            '</td></tr>' +
            '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
            '<td>Clear the access token currently stored in the user session. ' +
            '    After clearing the token, if you <a href="/test">test the ' +
            '    API request</a> again, you should go back to the auth flow.' +
            '</td></tr></table>')

# Fix for code verifier:
# https://github.com/googleapis/google-auth-library-python-oauthlib/issues/46
def random_string(length=10):
    password_characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(password_characters) for i in range(length))

def get_flow(redirect_uri: str,
             path_to_secrets: str,
             verification_string: str,
             state=None,
             ) -> 'Flow':
    ''' 
    Utility method to handle OAuth conversation with Google

    Params:
    -------
        redirect_uri: str
            Path to callback endpoint
        path_to_secrets: str
            Path to json file containing oauth secrets
        verification_string: str
            Random string to serve as an auth check on the callback

    '''

    flow = Flow.from_client_secrets_file(
        path_to_secrets,
        scopes=os.environ.get('SCOPES').split(','),
        state=state,
    )

    flow.redirect_uri = redirect_uri
    flow.code_verifier = verification_string
    return flow

def user_to_json(row: 'Record') -> json:
    output = {}
    for col in row:
        if type(row[col]) == datetime:
            output[col] = row[col].strftime("%m/%d/%Y, %H:%M:%S")
        else:
            output[col] = str(row[col])

    return json.dumps(output)

def handle_datestring(date_string: str) -> datetime:
    # output = datetime.strptime(date_string, '%a %b %d %Y %H:%M:%S')
    output = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    # datetime(*(time.strptime(date_string, format)[0:6]))
    # output = date.fromIsoFormat(date_string)
    return output

def record_to_object(record: 'Record') -> Dict[str, any]:
    '''
    Function that takes a Postgres Record object and returns
    a dictionary mapping of that Postgres Record row.
    '''
    output = {}
    for key in record._row.keys():
        output[key] = record._row[key]

    return output
