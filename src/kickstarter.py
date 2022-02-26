import asyncio

import logging
logging.basicConfig(level=logging.DEBUG)

import MotorController
from MessageTransport import MessageTransportServer

async def start_server():
    dispatcher = MessageDispatcher()

    while True:
        try:
            x = MessageTransportServer(dispatcher, 8000) # Inherits Controller and calls functions
            await x.server_task
        except asyncio.exceptions.CancelledError:
            await x.stop_message_server()
            return

def StartController():
    asyncio.run(start_server())

class MessageDispatcher:
    def __init__(self):
        logging.info('dispatcher ayarlanıyor...')

    def abort(self):
        print('*abort*')
