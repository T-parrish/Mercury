import asyncio
from typing import List, Tuple, Generator, Dict, Optional

from functools import partial

from .mediators import DBMediator, GraphMediator

from . import users, message_objs, comm_nodes, entities
from . import tasks, TaskTypes
from . import graph_nodes, interactions
from . import gmail_worker, graph_worker, db_worker

async def create_task_queue(app, loop):
    app.queue = asyncio.Queue(loop=loop, maxsize=app.config.MAX_QUEUE_SIZE)
    app.long_queue = asyncio.Queue(loop=loop, maxsize=app.config.MAX_QUEUE_SIZE)
    app.graph_queue = asyncio.Queue(loop=loop, maxsize=app.config.MAX_QUEUE_SIZE)

    async def db_callback(
        row_generators: List[Tuple[str, Generator[Dict[str, 'Table'], None, None]]],
        user_uuid: str,
        update_graph: Optional[bool] = True,
        *args,
        **kwargs
    ) -> str:

        mediator = DBMediator(app.database, user_uuid, TaskTypes['DB_INSERT'])
        init_db_mediator = await mediator._async_init()
        mediated_db_task = partial(init_db_mediator.handleDbInserts, row_generators)

        # Add the job to the queue
        await app.queue.put(mediated_db_task)

        # if update_graph:
        #     graph_mediator = GraphMediator(app.database, user_uuid, TaskTypes['USER_NODES'])
        #     init_graph_mediator = await mediator._async_init()
        #     mediated_graph_task = partial(
        #         init_graph_mediator.waitForTask,
        #         init_db_mediator.task_uuid,
        #         print('here we goooooo')
        #     )

        #     await app.graph_queue.put(mediated_graph_task)

        # return the task id
        return init_db_mediator.task_uuid

    # Workers to handle pulling Gmail message ids and creating comm nodes
    for i in range(4):
        app.add_task(
            gmail_worker(
                f"Gmail-Worker-{i}",
                app.long_queue,
                db_callback,
            )
        )

    for i in range(2):
        app.add_task(
            graph_worker(
                f"Graph-Worker-{i}",
                app.graph_queue,
                db_callback,
            )
        )

    # Workers to handle updating the DB
    for i in range(2):
        app.add_task(
            db_worker(
                f"DB-Worker-{i}",
                app.queue
            )
        )
