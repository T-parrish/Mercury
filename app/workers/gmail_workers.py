import asyncio
import json
import itertools
import uuid

from datetime import datetime

from typing import Callable, Generator, Dict, List, Tuple, Optional

from ..helpers.clock import coClock, clock

# @clock
async def gmail_worker(name: str,
                       long_queue: asyncio.Queue,
                       db_callback: Callable[[
                           List[Tuple[str, Generator[Dict[str, 'Table'], None, None]]],
                           str,
                           Optional[str]], None],
                       * args,
                       **kwargs
                       ) -> None:

    while True:
        try:
            # job will be a query to Gmail API from Gmail interface
            job = await long_queue.get()
        except long_queue.Empty:
            print(f'{name} sleeping for 5')
            await asyncio.sleep(5)
            continue

        size = long_queue.qsize()

        try:
            results, user_uuid = await job(*args, **kwargs)
        except Exception as e:
            print(f'something went wrong with the current task: {e}')
            return

        msg_objs = ({
            'owner': user_uuid,
            'message_id': node.msg_id,
            'thread_id': node.thread_id,
            'last_fetch': datetime.now()
        } for node in results)

        comm_nodes = ({
            'message_id': node.msg_id,
            'html_body': node.html_body,
            'text_body': node.plaintext_body,
            'mimetypes': node.mimetypes,
            'ip_address': node.ip_address,
            'subject': node.subject,
            'date': node.date,
            'keywords': json.dumps(node.keywords),
            'labels': node.labels
        } for node in results)

        # flattens all the Entity arrays nested in array of comm nodes
        all_entities = list(
            itertools.chain.from_iterable(
                [node.entities for node in results]
            )
        )

        entities = ({
            'email': entity.email,
            'name': entity.name,
            'domain': entity.domain,
            'msg_id': entity.msg_id,
            'poc': entity.poc.name
        } for entity in all_entities)

        # free up memory
        del all_entities

        try:
            executables = [
                ('msg_objs', msg_objs),
                ('comm_nodes', comm_nodes),
                ('entities', entities)
            ]

            await db_callback(executables, user_uuid)

        except Exception as e:
            print(f'Error sending results to next long_queue: {e}')
            break

        print(f"{name} has completed a task from {long_queue} with {size} remaining. Sleeping for 3 seconds... \n\n")
        await asyncio.sleep(3)

    return
