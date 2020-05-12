from sanic import Blueprint
from sanic.response import json

from json import loads

from datetime import datetime
from functools import partial

from app.workers.mediators import GraphMediator
from app.db import TaskTypes
from app.helpers import handle_datestring, record_to_object
from app.db.queries.dumpz import contact_counts, all_edges, all_nodes

hermes_bp = Blueprint('hermes', url_prefix='/hermes')

# host/api/hermes/graphtest
@hermes_bp.route('/graphtest', methods=['POST'])
async def index(request):
    body = loads(request.body)
    user_id = body['userData'].get('id', None)

    if not user_id:
        return json({
            'status': 'Not Authorized',
        }, 401)

    # Date strings come in through the body from front end
    startDate = body['dateFilters'].get('startDate', None)
    endDate = body['dateFilters'].get('endDate', None)

    if not startDate:
        startDate = datetime(1900, 1, 1)

    if not endDate:
        endDate = datetime.now()

    mediator = GraphMediator(
        request.app.database,
        user_id,
        TaskTypes['USER_NODES']
    )

    node_gen_tracker = await mediator._async_init()

    tracked_node_gen = partial(
        node_gen_tracker.loadGraphClusters,
        handle_datestring(startDate),
        handle_datestring(endDate)
    )

    await request.app.graph_queue.put(tracked_node_gen)

    return json({
        'status': 'Queued GraphBuilder',
        'task_id': node_gen_tracker.task_uuid
    }, 200)

# Need a route to handle long polling from front end
# host/api/hermes/track/<task_id:uuid>
@hermes_bp.route('/track/<task_type>')
async def checkTaskStatus(request, task_type):
    user_id = request.ctx.user_id

    try:
        task_query = '''
        SELECT * FROM tasks
        WHERE tasks.owner = :owner_id AND tasks.task_type = :task_type
        '''

        result = await request.app.database.fetch_one(
            query=task_query,
            values={'owner_id': user_id, 'task_type': task_type.upper()}
        )

    except Exception as e:
        return json({
            "status": 'Error',
            "message": f'Unable to query tasks: {e}'
        })

    if not result:
        return json({
            'status': 'No result found',
        }, 200)

    if result['success'] is True:
        return json({
            'status': 'Success',
            'finished': result['time_finished'].date()
        }, 200)

    if result['success'] is False:
        return json({
            'status': 'Failure',
            'message': 'Task was not completed successfully',
            'finished': result['time_finished'].date()
        }, 200)

    else:
        return json({
            'status': 'Error',
            'error': str(result['error'])
        }, 500)

# Need a route to handle long polling from front end
# host/api/hermes/loadgraph
@hermes_bp.route('/loadgraph', methods=["POST"])
async def fetchGraph(request):
    body = loads(request.body)
    user_id = body['userData'].get('id', None)

    if not user_id:
        return json({
            'status': 'Not Authorized',
        }, 401)

    try:
        node_query = all_nodes
        edge_query = all_edges

        node_results = await request.app.database.fetch_all(
            query=node_query,
            values={'owner_id': user_id}
        )

        edge_results = await request.app.database.fetch_all(
            query=edge_query,
            values={'owner_id': user_id}
        )

    except Exception as e:
        return json({
            "status": 'Error',
            "message": f'Unable to fetch data: {e}'
        }, 500)

    if not node_results:
        return json({
            'status': 'No result found',
        }, 404)

    try:
        graph_nodes = [record_to_object(res) for res in node_results]
        graph_edges = [record_to_object(res) for res in edge_results]
    except Exception as e:
        print(f'error handling results: {e}')


    # if result:
    #     t = [(row['name'],
    #           row['email'],
    #           row['node_v'],
    #           row['to_count'],
    #           row['from_count'],
    #           row['cc_count'],
    #           row['bcc_count']) for row in result]

    return json({
        'status': 'Success',
        'graph_nodes': graph_nodes,
        'graph_edges': graph_edges
    }, 200)
