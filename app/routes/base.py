from sanic import Blueprint
from sanic.response import json, text, redirect, html

from json import loads

import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow

from app.db import tasks, TaskTypes
from app.helpers import credentials_to_dict, get_flow, user_to_json
from app.workers.mediators import AuthMediator

from app.db import User

base_bp = Blueprint('base')

@base_bp.route('/')
async def root(request):
    return text('yup, this is a page')

@base_bp.route('/login', methods=['GET', 'POST'])
async def login_page(request):
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

@base_bp.route('/hermes/auth', methods=["POST"])
async def create_user(request):
    token = loads(request.body)

    authenticator = AuthMediator(
        request.app.database,
        '',
        TaskTypes['AUTHENTICATE']
    )

    try:
        auth_obj = await authenticator.handleJWT(token['token'])
    except Exception as e:
        return json({'status': 'Error', 'message': f'Error authenticating user: {e}'}, 500)

    user = user_to_json(auth_obj.hermes_user)

    return json({'status': 'Success', 'user': user}, 200)

# host/authorize/user_uuid
# authorization endpoint for when you have an authenticated user
# takes the user_uuid and stores the Oauth2 credentials on the User in
# the users table so you don't have to re-authenticate between scrapes
@base_bp.route('/authorize/<user_id:uuid>')
# @cross_origin(app)
async def authorize(request, user_id):
    redirect_uri = request.app.url_for(
        'base.oauth2callback',
        # ToDo: Lift this up as a variable into environment
        _server='localhost:5000',
        _external=True
    )

    flow = get_flow(
        redirect_uri,
        request.app.config.CLIENT_SECRETS_FILE,
        request.app.config.OAUTH_VERIFIER
    )

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    request['session']['state'] = state
    request['session']['user_id'] = str(user_id)

    return redirect(authorization_url)


# Authorization endpoint to use when an authentication strategy 
# has not yet been implemented.
@base_bp.route('/authorize')
async def authorize(request):
    redirect_uri = request.app.url_for(
        'base.oauth2callback',
        # ToDo: Lift this up as a variable into environment
        _server='localhost:5000',
        _external=True
    )

    flow = get_flow(
        redirect_uri,
        request.app.config.CLIENT_SECRETS_FILE,
        request.app.config.OAUTH_VERIFIER
    )

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    request['session']['state'] = state

    return redirect(authorization_url)

# host/oauth2callback
@base_bp.route('/oauth2callback')
async def oauth2callback(request):
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = request['session'].get("state", None)

    redirect_uri = request.app.url_for(
        'base.oauth2callback',
        # ToDo: Lift this up as a variable into environment
        _server='localhost:5000',
        _external=True
    )

    flow = get_flow(
        redirect_uri,
        request.app.config.CLIENT_SECRETS_FILE,
        request.app.config.OAUTH_VERIFIER,
        state=state,
    )

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store creds in postgres on user by id
    credentials = flow.credentials
    cred_dict = await credentials_to_dict(credentials)

    request['session']['credentials'] = cred_dict

    return redirect('/api/gmail/scrape')
