from contextvars import ContextVar

# Holds the raw base64 userinfo header value for the current request context
current_userinfo: ContextVar[str] = ContextVar('current_userinfo', default='')
