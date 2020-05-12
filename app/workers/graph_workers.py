import asyncio
import itertools
import uuid

from typing import Callable, Generator, Dict, List, Tuple

from ..data_structures.UserNode import UserNodeBuilder

from ..helpers.clock import coClock, clock

# @clock
async def graph_worker(name: str,
                       graph_queue: asyncio.Queue,
                       db_callback: Callable[[
                           List[Tuple[str, Generator[Dict[str, 'Table'], None, None]]],
                           str,
                           str], None],
                       * args,
                       **kwargs
                       ) -> None:

    while True:
        try:
            # job will be a query to Gmail API from Gmail interface
            job = await graph_queue.get()
        except graph_queue.Empty:
            print(f'{name} sleeping for 5')
            await asyncio.sleep(5)
            continue

        size = graph_queue.qsize()

        # Gets a Generator of entity and comm node data clustered by msg_id
        results, user_uuid = await job(*args, **kwargs)

        obj = UserNodeBuilder()
        obj.handleClusters(results)
        obj.process_nodes(user_uuid)

        graph_nodes = ({
            'domain': obj.graph[key].domain,
            'email': obj.graph[key].email,
            'name': obj.graph[key]._get_name()
        } for key in obj.graph.keys())

        interactions = ({
            'id': conn.interaction_key,
            'date': conn.date,
            'date_string': conn.date_string,
            'message_id': conn.message_id,
            'node_u': conn.node_u,
            'node_v': conn.node_v,
            'conn_type': conn.conn_type,
            'score': conn.score,
        } for conn in obj.interactions)

        def get_edges():
            for key in obj.graph.keys():
                for edge in obj.graph[key].edges:
                    interaction_obj = {
                        'owner': user_uuid,
                        'parent_node': obj.graph[key].email,
                        'interaction_id': edge
                    }
                    yield interaction_obj

        interaction_groups = get_edges()


        executables = [
            ('graph_nodes', graph_nodes),
            ('interactions', interactions),
            ('interaction_groups', iter(interaction_groups))
        ]

        await db_callback(executables, user_uuid)

        print(f"{name} has completed a task from {graph_queue} with {size} remaining. Sleeping for 3 seconds... \n\n")
        await asyncio.sleep(3)

    return
