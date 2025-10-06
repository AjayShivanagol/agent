import mesop.labs as mel
from collections.abc import Callable
from typing import Any


@mel.web_component(path='./read_cookie.js')
def cookie_reader(
    *,
    on_user_info: Callable[[mel.WebEvent], Any],
    cookie_name: str = 'userinfo',
    key: str | None = None,
):
    """Injects a tiny web component that reads a cookie and emits its value.

    Event name: 'userInfo' with detail { value: string }
    """
    return mel.insert_web_component(
        name='cookie-reader',
        key=key,
        events={'userInfo': on_user_info},
        properties={'cookie_name': cookie_name},
    )
