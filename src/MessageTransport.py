import asyncio

from functools import wraps

import json
import logging
import uuid
import time

import marshmallow

class MessageSchema(marshmallow.Schema):
    type = marshmallow.fields.Str()
    value = marshmallow.fields.Str()

PING_TIMEOUT=1000

class MessageTransportServer:
    def __init__(self, dispatcher, port):
        self.__dispatcher = dispatcher
        self.__clients = {}

        self.__port = port
        self.__msg_schema = MessageSchema()

        self.server = asyncio.create_task(self.start_server())

    def __async_error_handle(func):
        @wraps(func)
        async def tmp(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except:
                logging.exception('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...')
                self.__dispatcher.abort()

        return tmp

    def __error_handle(func):
        @wraps(func)
        def tmp(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except:
                logging.exception('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...')
                self.__dispatcher.abort()

        return tmp

    @__async_error_handle
    async def start_server(self):
        self.server = await asyncio.start_server(self.tcp_handler, '0.0.0.0', self.__port)

        async with self.server:
            await self.server.serve_forever()

    @__async_error_handle
    async def tcp_handler(self, reader, writer):
        client_id = uuid.uuid4().hex
        logging.info(f'Yeni Bağlantı, uuid: {client_id}')
        try:
            while (not writer.is_closing()) and self.check_ping(client_id):
                data=await reader.read()
                logging.debug(f'Mesaj alındı. raw: {data}')

                data=self.__msg_schema.load(json.loads(data))
                logging.debug(f'Mesaj alındı. {data["type"]} {data["msg"]}')

                if not hasattr(self.__dispatcher, data['type']):
                    if hasattr(self, data['type']):
                        x=json.dumps(getattr(self.__dispatcher, data['type'])(data['msg'], reader, writer, client_id=client_id))
                        if not x is None:
                            writer.write(x)
                            await writer.drain()
                            continue

                    else:
                        writer.write({'type': 'error', 'msg': 'This message type is not implemented.'})
                        await writer.drain()
                        continue

                x=json.dumps(getattr(self.__dispatcher, data['type'])(data['msg'], reader, writer, client_id=client_id))
                if not x is None:
                    writer.write(x)
                    await writer.drain()

        except Exception as e:
            logging.exception('conn error')
            await writer.drain()
            writer.close()

    def ping(self, client_id, *args, **kwargs):
        x=int(time.time()*1000)
        self.__clients.update({client_id: x})
        return {'type': 'pong', 'time': x}

    def check_ping(self, client_id):
        if self.__clients.get(client_id) is None:
            self.ping(None, None, None)
            return True

        if (self.__clients.get(client_id) < int(time.time()*1000)-PING_TIMEOUT):
            logging.debug(f'{client_id} dropped out ping.')
            return False

    def stop_message_server(self):
        self.server.cancel()

class MessageTransportClient:
    def __init__(self, ip, port):
        pass
