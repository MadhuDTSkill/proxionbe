import jwt
import traceback
from urllib.parse import parse_qs
from django.conf import settings
from channels.db import database_sync_to_async
from auth_app.models import User
from helper import utils

@database_sync_to_async
def get_user(id):
    """ Fetches the user from the database asynchronously. """
    try:
        return User.objects.get(id=id)
    except User.DoesNotExist:
        return None    

@database_sync_to_async
def get_session(session_key):
    """ Retrieves session data from the database asynchronously. """
    return utils.retrieve_session(session_key)

class WsAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def authenticate(self, scope, send):
        try:
            query_string = scope.get('query_string', b'').decode('utf-8')
            query_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(query_string).items()}  
            scope["query_params"] = query_params  # Store parsed query params in scope

            token = query_params.get("token")
            if not token:
                await self.close_connection(send, "Missing authentication token.", 4401)
                return None

            decoded_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            session_key = decoded_payload.get('session_key')

            if not session_key:
                await self.close_connection(send, "Invalid token payload.", 4401)
                return None

            session_data = await get_session(session_key)
            if not session_data:
                await self.close_connection(send, "Invalid session.", 4401)
                return None

            user_id = session_data.get('user_id')
            return await get_user(user_id)

        except jwt.ExpiredSignatureError:
            await self.close_connection(send, "Token has expired.", 4403)
            return None
        except jwt.InvalidTokenError:
            await self.close_connection(send, "Invalid token.", 4401)
            return None
        except Exception as e:
            print("🔥 WebSocket Authentication Error:", str(e))
            traceback.print_exc()
            await self.close_connection(send, "Authentication error.", 4401)
            return None

    async def close_connection(self, send, message, code):
        """ Sends an error message and closes the WebSocket connection. """
        print(f"❌ Closing WebSocket: {message} (Code: {code})")
        await send({
            "type": "websocket.close",
            "code": code
        })

    async def __call__(self, scope, receive, send):
        try:
            user = await self.authenticate(scope, send)
            if user is None:
                return  
            scope['user'] = user
            return await self.app(scope, receive, send)

        except Exception as e:
            print("🔥 UNHANDLED ERROR in WebSocket Middleware:", str(e))
            traceback.print_exc()
            await self.close_connection(send, "Internal Server Error.", 4500)
