import asyncio

import pytest
from fastapi import HTTPException

from src.interfaces.api.runs import RunRegistry


async def test_a_second_run_is_refused_while_one_is_in_progress():
    registry = RunRegistry()
    gate = asyncio.Event()

    async def long():
        await gate.wait()
        return "done"

    first = asyncio.ensure_future(registry.run("sync", long()))
    await asyncio.sleep(0)

    with pytest.raises(HTTPException) as error:
        await registry.run("init", long())
    assert error.value.status_code == 409

    gate.set()
    assert await first == "done"
    assert not registry.running


async def test_cancelling_stops_the_run_and_answers_409():
    registry = RunRegistry()

    async def forever():
        await asyncio.sleep(3600)

    class Engine:
        def begin(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def execute(self, *_):
            return None

    run = asyncio.ensure_future(registry.run("sync", forever()))
    await asyncio.sleep(0)

    assert await registry.cancel(Engine()) == "sync"
    with pytest.raises(HTTPException) as error:
        await run
    assert error.value.status_code == 409
    assert not registry.running
