import mesop.labs as mel
from collections.abc import Callable
from typing import Any


@mel.web_component(path='./logout_helper.js')
def logout_helper(*, redirect_to: str = '/logout', key: str | None = None):
    """Inserts a component that clears cookies and redirects to the given URL."""
    return mel.insert_web_component(
        name='logout-helper',
        key=key,
        events={},
        properties={'redirect_to': redirect_to},
    )
