from typing import Callable, List


import time
import asyncio
import random

def coClock(func):
    '''
    Wraps an asynchronous function to return the result and time it took to execute
    '''
    async def coClocked(*args, **kwargs):
        t0 = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        name = func.__name__
        arg_str = ', '.join(repr(arg) for arg in args)
        if type(result) == list:
            output = result[:5]
        else:
            output = result

        print('\n\n{:.8f}s {}({}) -> {}\n\n'.format(elapsed, name, arg_str, output))
        return result

    return coClocked

def clock(func):
    '''
    Wraps a function to return the result and time it took to execute
    '''
    def clocked(*args):
        t0 = time.perf_counter()
        result = func(*args)
        elapsed = time.perf_counter() - t0
        name = func.__name__
        arg_str = ', '.join(repr(arg) for arg in args)
        print('{:.8f} {}({}) -> {} \n\n'.format(elapsed, name, arg_str, result))
        return result

    return clocked

def noArgClock(func):
    '''
    Wraps a function to return the result and time it took to execute
    '''
    def clocked(*args):
        t0 = time.perf_counter()
        result = func(*args)
        elapsed = time.perf_counter() - t0
        name = func.__name__
        print('{:.8f} {} -> {} \n\n'.format(elapsed, name, result))
        return result

    return clocked

@clock
def testing(wait: int) -> str:
    time.sleep(wait)
    return f'slept for {wait} seconds'


@coClock
async def coTesting(limit: int) -> str:
    ''' increments an internal counter and stops when the limit is reached'''

    wait_time = random.random()

    ticks = 0
    waited = 0

    while waited < limit:
        print(f'Waiting.... {waited} time waited so far')
        await asyncio.sleep(wait_time)
        waited += wait_time
        ticks += 1

    return f'wait time was {wait_time} and it took {ticks} ticks to get there'

async def main() -> None:
    '''
    Test cases for coClock to ensure that the async function calls are being handled and timed concurrently.
    '''
    test_units = [2, 4, 6, 3]

    task1 = asyncio.create_task(coTesting(test_units[0]))
    task2 = asyncio.create_task(coTesting(test_units[1]))
    task3 = asyncio.create_task(coTesting(test_units[2]))
    task4 = asyncio.create_task(coTesting(test_units[3]))

    await task1
    await task2
    await task3
    await task4


if __name__ == '__main__':
    asyncio.run(main())
