from sanic import Blueprint
from sanic.response import json, redirect

from functools import partial

from app.wrappers import Pipeline, Gmail
from app.workers.mediators import HermesMediator
from app.db import TaskTypes
from app.helpers import credentials_to_dict, authorized, withOauth

import uuid

gmail_bp = Blueprint('gmail', url_prefix='/gmail')

# Use @withOauth() decorator if authentication has been configured
# to store and retrieve user creds from Postgres via user UUID

# Otherwise, use @authorized() decorator to retrieve creds from session


# host/api/gmail/start
@gmail_bp.route('/start', methods=['POST', 'GET'])
@authorized()
async def load_data(request, auth_obj, user_uuid):
    try:
        pipeline_interface = Pipeline(auth_obj, 0.7, '')

        mediator = HermesMediator(
            request.app,
            user_uuid,
            TaskTypes['HERMES'],
            pipeline_interface,
        )

        hermes_tracker = await mediator._async_init()
        tracked_hermes = partial(hermes_tracker.wrap_pipeline, 500, 2500, 15, 4, True)

        await request.app.long_queue.put(tracked_hermes)

    except Exception as e:
        return json({
            'status': 'Error starting task',
            'message': f'something went wrong: {e}'
        }, 500)


    return json({'status': 'Success', 'message': 'Task queued successfully', 'task_id': auth_obj.task_uuid}, 200)




# host/api/gmail/getmessage/<msg_id>
@gmail_bp.route('/getmessage/<msg_id>', methods=['POST', 'GET'])
@authorized()
async def get_single_message(request, auth_obj, msg_id):
    try:
        interface = Gmail(auth_obj.credentials)
        message = await interface.getSingleMessage(msg_id)
    except Exception as e:
        return json({
            'status': 'Error',
            'message': f'error querying gmail API: {e}'
        }, 500)

    return json({
        'status': 'Success',
        'message': message
    }, 200)


# host/api/gmail/scrape
# Route that will scrape and dump gmail w/o task tracking
@gmail_bp.route('/scrape', methods=['GET'])
@authorized()
async def scrape_data(request, credentials):
    try:
        pipeline_interface = Pipeline(credentials, 0.7, '')

        untracked_hermes = partial(pipeline_interface.hermes, 500, 2500, 15, 4)

        await request.app.long_queue.put(untracked_hermes)

    except Exception as e:
        return json({
            'status': 'Error starting task',
            'message': f'something went wrong: {e}'
        }, 500)

    raw_uuid = uuid.uuid4()
    task_uuid = str(raw_uuid)

    return json({'status': 'Success', 'message': 'Task queued successfully', 'task_id': task_uuid}, 200)
