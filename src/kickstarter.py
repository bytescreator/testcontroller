from functools import wraps

import asyncio

import logging
logging.basicConfig(level=logging.DEBUG)

import MotorController
from MessageTransport import MessageTransportServer

async def start_server():
    dispatcher = MessageDispatcher()

    while True:
        try:
            x = MessageTransportServer(dispatcher, 8000)
            await x.server_task
        except asyncio.exceptions.CancelledError:
            await x.stop_message_server()
            return

def StartController():
    asyncio.run(start_server())

class MessageDispatcher:
    def __init__(self):
        self.mutex = asyncio.Lock()
        logging.info('dispatcher ayarlanıyor...')

    def abort(self):
        print('*abort*')

    def __mutexrun(func):
        @wraps(func)
        async def tmp(self, *args, **kwargs):
            await self.mutex.acquire()
            res = func(self, *args, **kwargs)
            self.mutex.release()
            return res

        return tmp

    async def movement_forward(self):
        pass

    async def movement_backward(self):
        pass

    async def movement_left(self):
        pass

    async def movement_right(self):
        pass

    async def get_stat(self):
        pass
