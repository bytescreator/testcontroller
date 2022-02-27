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

        self.server_task = asyncio.create_task(self.start_server())

    def __async_error_handle(func):
        @wraps(func)
        async def tmp(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)

            except asyncio.exceptions.CancelledError:
                self.__dispatcher.abort()
                await self.stop_message_server()

            except:
                if len(args) > 0 and isinstance(args[1], asyncio.StreamWriter):
                    args[1].close()
                    await args[1].wait_closed()

                logging.debug('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...', exc_info=True)
                logging.info('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...')
                self.__dispatcher.abort()

        return tmp

    def __error_handle(func):
        @wraps(func)
        def tmp(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except:
                logging.debug('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...', exc_info=True)
                logging.info('Mesaj alımı esnasında hata operasyonlar sıfırlanıyor...')
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
            while True:
                asyncio.create_task(self.check_ping(client_id, reader, writer))
                data=await reader.readline()
                data=self.__msg_schema.load(json.loads(data))
                logging.debug(f'Mesaj alındı. {data["type"]} {data.get("msg")}')

                if not hasattr(self.__dispatcher, data['type']):
                    if hasattr(self, data['type']):
                        try:
                            x=json.dumps(getattr(self, data['type'])(data.get('msg'), reader, writer, client_id=client_id)).encode('utf-8')

                        except Exception as e:
                            logging.debug('Kod çalıştırırken hata, hataya karşılık operasyonlar durduruldu.', exc_info=True)
                            logging.info('Kod çalıştırırken hata, hataya karşılık operasyonlar durduruldu.')
                            self.__dispatcher.abort()
                            writer.write(json.dumps({'type': 'error', 'msg': str(e)}))
                            await writer.drain()

                            continue

                        if not x is None:
                            writer.write(x)
                            await writer.drain()
                        else:
                            writer.write('\n')
                            await writer.drain()
                        
                        continue

                    else:
                        self.__dispatcher.abort()
                        logging.warning('İmplemente edilmemiş mesaj tipi, hata olmasına karşılık operasyonlar durduruldu.')
                        writer.write(json.dumps({'type': 'error', 'msg': 'This message type is not implemented.'}).encode('utf-8'))
                        await writer.drain()
                        continue

                try:
                    x=json.dumps(getattr(self.__dispatcher, data['type'])(data['msg'], reader, writer, client_id=client_id)).encode('utf-8')
                except Exception as e:
                    self.__dispatcher.abort()
                    writer.write(json.dumps({'type': 'error', 'msg': str(e)}))
                    await writer.drain()

                    continue

                if not x is None:
                    writer.write(x)
                    await writer.drain()
                else:
                    writer.write('\n')
                    await writer.drain()

            logging.debug(f'{client_id} bağlantı kapatılıyor')
            writer.close()

        except ConnectionResetError:
            self.__dispatcher.abort()
            logging.warning(f'conn reset {client_id}')
            self.__clients.pop(client_id)

    def ping(self, *args, **kwargs):
        client_id = kwargs['client_id']

        x=int(time.time()*1000)
        self.__clients.update({client_id: (x, args[1], args[2])})
        return {'type': 'pong', 'time': x}

    async def check_ping(self, client_id, reader, writer):
        if self.__clients.get(client_id) is None:
            self.ping(None, reader, writer, client_id=client_id)

        await asyncio.sleep((self.__clients.get(client_id)[0]+PING_TIMEOUT-int(time.time()*1000))/1000)

        if (not self.__clients.get(client_id) is None) and (self.__clients.get(client_id)[0] < int(time.time()*1000)-PING_TIMEOUT):
            logging.debug(f'{client_id} ping e cevap vermedi.')
            
            clnt=self.__clients.pop(client_id)
            clnt[2].close() # Causes the read to be failed.
            await clnt[2].wait_closed()

    async def stop_message_server(self):
        logging.info('Stopping server')
        for client in self.__clients:
            self.__clients[client][2].close()
            await self.__clients[client][2].wait_closed()

        self.server.close()
        self.server_task.cancel()

class MessageTransportClient:
    def __init__(self, ip, port):
        self.init_clients()
        self.__msg_schema = MessageSchema()
        self.ping_task = asyncio.create_task(self.pinger())

    async def init_clients(self):
        self.reader, self.writer = await asyncio.open_connection(
            ip, port
        )

    async def pinger(self):
        while True:
            asyncio.sleep(PING_TIMEOUT/2)
            self.send('ping', None)

    async def request(self, type, data):
        writer.write(self.__msg_schema.dump({'type': type, 'msg': data}).encode('utf-8'))
        await writer.drain()

        output = self.__msg_schema.loads(await reader.readline())
        if output['type'] == 'error':
            raise Exception(output['msg'])

        return output['type'], output['msg']

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()
