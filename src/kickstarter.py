import asyncio

import logging
logging.basicConfig(level=logging.DEBUG)

import MotorController
from MessageTransport import MessageTransportServer

async def start_server():
    dispatcher = MessageDispatcher()

    x = MessageTransportServer(dispatcher, 8000) # Inherits Controller and calls functions
    await x.server

def StartController():
    asyncio.run(start_server())

class MessageDispatcher:
    def __init__(self):
        logging.info('dispatcher ayarlanıyor...')

    async def pong(data, reader, writer):
        print(data)

    def abort(self):
        print('*abort*')
