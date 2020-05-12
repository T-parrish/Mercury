from sanic import Blueprint
from sanic.response import json, redirect
from datetime import datetime
from json import loads

from app.workers.mediators import DBMediator
from app.db import TaskTypes

form_bp = Blueprint('form_routes')

# host/api/gmail/start
@form_bp.route('/subscribe', methods=['POST'])
async def handle_subscription(request):
    body = loads(request.body)
    email = body.get('email', None)
    time = datetime.now()

    insert_obj = {'email': email, 'timestamp': time}


    print(f'Request body: {body} \nTimestamp: {time} \n\n')

    if email is not None:
        try:
            mediator = DBMediator(request.app.database, '', TaskTypes['DB_INSERT'])
            await mediator.insertRow('subscriptions', insert_obj)
            if mediator.successful:
                return json({'status': 'Success', 'message': 'Subscribed'}, 200)
            else:
                return json({'status': 'Error', 'message': 'Error saving data: {}'.format(', '.join(mediator.errors))}, 400)
        except Exception as e:
            return json({'status': 'Error', 'message': f'Something went wrong: {e}'}, 500)

    else:
        return json({'status': 'Invalid', 'message': 'Not a valid Email'}, 400)
