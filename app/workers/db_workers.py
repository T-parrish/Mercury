import asyncio

async def db_worker(name: str,
                    queue: asyncio.Queue,
                    *args,
                    **kwargs
                    ) -> None:
    while True:
        try:
            # job will be a query to Gmail API from Gmail interface
            job = await queue.get()
        except queue.Empty:
            print(f'{name} sleeping for 5')
            await asyncio.sleep(5)
            continue

        size = queue.qsize()


        try:
            # executes the db statement by passing args and kwargs
            # eg query=insert_statement or values=values
            await job(*args, **kwargs)
        except Exception as e:
            print(f'Error saving data to DB: {e}')
            break

        print(f"{name} finished a job with {queue}. {size} remaining and sleeping 3 seconds... \n\n")
        await asyncio.sleep(3)

    return
