import asyncio

from p4p.nt import NTScalar
from p4p.server import Server, StaticProvider
from p4p.server.asyncio import SharedPV, Handler

from fastcs.attributes import AttrR, AttrW
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Int
from fastcs.transport.pvxs.handlers import (
    AttrRHandler,
    AttrWHandler,
    pv_metadata_from_datatype,
)

DEFAULT_TIMEOUT = 10.0


class P4PBlock(Handler):
    # This is an `p4p.server.asyncio` import Handler
    def __init__(
        self,
        prefix: str,
        controller: Controller | SubController,
        timeout: float = DEFAULT_TIMEOUT,
        loop: asyncio.AbstractEventLoop | None = None,
        mode: str = "Mask",
    ):
        self._prefix = prefix
        self._controller = controller
        self._loop = loop or asyncio.new_event_loop()
        self._timeout = timeout
        self._mode = mode

        self._pvs: dict[str, SharedPV] = {}
        self._sub_blocks: dict[str, P4PBlock] = {}

    async def _add_pv_from_attribute(self, pv_name: str, attribute: AttrR | AttrW):
        handler = (
            AttrRHandler(attribute)
            if isinstance(attribute, AttrR)
            else AttrWHandler(attribute)
        )
        self._pvs[pv_name] = SharedPV(
            handler=handler,
            **pv_metadata_from_datatype(attribute.datatype),
        )

    async def _add_sub_block(self, pv_name: str, sub_controller: SubController):
        self._sub_blocks[pv_name] = P4PBlock(
            pv_name,
            sub_controller,
            timeout=self._timeout,
            loop=self._loop,
            mode=self._mode,
        )

    def get_providers(self) -> list[StaticProvider]:
        static_providers = []
        for sub_block in self._sub_blocks.values():
            static_providers += sub_block.get_providers()

        this_block_static_provider = StaticProvider(self._prefix)
        for pv_name, pv in self._pvs.items():
            this_block_static_provider.add(pv_name, pv)

        return [this_block_static_provider] + static_providers

    async def walk_attributes(self):
        for attr_name, attribute in self._controller.attributes.items():
            pv_name = f"{self._prefix}:{attr_name.title().replace('_', '')}"
            print("pv_name:", pv_name)
            if isinstance(attribute, (AttrR | AttrW)):
                await self._add_pv_from_attribute(pv_name, attribute)
        for suffix, sub_controller in self._controller.get_sub_controllers().items():
            sub_controller_name = f"{self._prefix}:{suffix.title().replace('_', '')}"
            print("controller:", sub_controller_name)
            await self._add_sub_block(sub_controller_name, sub_controller)
            await self._sub_blocks[sub_controller_name].walk_attributes()

    async def asyncSetUp(self):
        await self.walk_attributes()

    async def asyncTearDown(self):
        print("ASYNC TEARDOWN ", self._prefix)

    def setUp(self):
        self._loop.set_debug(True)
        self._loop.run_until_complete(
            asyncio.wait_for(self.asyncSetUp(), self._timeout)
        )

    def tearDown(self):
        self._loop.run_until_complete(
            asyncio.wait_for(self.asyncTearDown(), self._timeout)
        )


class P4PServer(P4PBlock):
    def __init__(
        self,
        pv_prefix: str,
        controller: Controller,
    ):
        super().__init__(pv_prefix, controller, loop=asyncio.new_event_loop())

    def run(self) -> None:
        self.setUp()

        try:
            Server.forever(providers=self.get_providers())
        finally:
            print("CLOSING LOOP")
            self.tearDown()

    def tearDown(self):
        super().tearDown()
        self._loop.close()


class TestSubController(SubController):
    some_read_int = AttrR(Int(), description="some_read_int")


class TestController(Controller):
    some_read_bool = AttrR(Bool(), description="some_read_bool")
    some_write_bool = AttrW(Bool(), description="some_write_bool")

    def __init__(self):
        super().__init__()
        self.register_sub_controller("sub_controller", TestSubController())


import time


class SomeClassWithACoroutine:
    def __init__(self, data):
        self.data = data

    async def coroutine(self, value):
        print("COROUTINE CALLED: ", self.data, value)


class AttrWHandler:
    def __init__(self, some_object_with_coro: SomeClassWithACoroutine):
        self.some_object_with_coro = some_object_with_coro

    async def put(self, pv, op):
        raw_value = op.value()
        print("USING PUT", raw_value)
        await self.some_object_with_coro.coroutine(raw_value)

        pv.post(raw_value, timestamp=time.time())
        op.done()


class AsyncioProvider:
    def __init__(self, name: str, loop: asyncio.AbstractEventLoop):
        self.name = name
        self._loop = loop
        self._provider = StaticProvider(name)
        self._pvs = []

        self.setUp()

    async def asyncSetUp(self):
        await self.add_pvs()

    async def asyncTearDown(self): ...

    async def add_pvs(self):
        print("ADDING PV")
        pv = SharedPV(
            handler=AttrWHandler(SomeClassWithACoroutine("data")),
            nt=NTScalar("s"),
            initial="initial_value",
        )
        self._pvs.append(pv)
        self._provider.add(f"{self.name}:PV", pv)

    def setUp(self):
        self._loop.set_debug(True)
        self._loop.run_until_complete(asyncio.wait_for(self.asyncSetUp(), 1.0))

    def tearDown(self):
        self._loop.run_until_complete(asyncio.wait_for(self.asyncTearDown(), 1.0))


class TestP4PServer:
    def __init__(
        self,
        pv_prefix: str,
    ):
        self._pv_prefix = pv_prefix
        self._pvs = []

    def run(self):
        loop = asyncio.new_event_loop()
        self.provider = AsyncioProvider(self._pv_prefix, loop)
        try:
            loop.run_until_complete(self._run())
        finally:
            loop.close()

    async def _run(self) -> None:
        try:
            Server.forever(providers=[self.provider._provider])
        finally:
            print("CLOSING LOOP")


TestP4PServer("FASTCS").run()
