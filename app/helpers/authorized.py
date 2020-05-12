import json

from functools import wraps
from sanic.response import redirect

import google.oauth2.credentials

from app.db import users, TaskTypes


def authorized():
    '''
    Decorator that redirects to /authorize endpoint if there are no credentials in the session. Otherwise it proceeds as usual.
    '''
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            # Grab the creds from the session
            # Todo: maybe store this ish in postgres
            creds = request['session'].get('credentials', None)

            if not creds:
                return redirect('/authorize')
            else:
                is_authorized = True

            if is_authorized:
                try:
                    credentials = google.oauth2.credentials.Credentials(**creds)
                    
                    # the user is authorized.
                    # run the handler method and return the response
                    response = await f(request, credentials, *args, **kwargs)
                    return response

                except Exception as e:
                    return json({
                        'status': 'Error',
                        'error': f'something went wrong: {e}'
                    }, 500)
            else:
                return json({'status': 'not_authorized'}, 403)

        return decorated_function
    return decorator

