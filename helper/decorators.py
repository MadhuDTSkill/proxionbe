from .consumers import BaseChatAsyncJsonWebsocketConsumer 
 
def consumer_method_exception_handler(func):
    async def wrapper(self, *args, **kwargs):
        try:
            await func(self, *args, **kwargs)
        except Exception as e:
            query = args[0]
            string = str(e)
            uuid : str = await BaseChatAsyncJsonWebsocketConsumer.generate_random_id()        
            success = False
            await self.stream_response(string, query, uuid, success)
            await self.close()
    return wrapper
