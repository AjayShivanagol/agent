import mesop.labs as mel


@mel.web_component(path='./scroll_bottom.js')
def scroll_bottom(*, key: str | None = None):
    """Inserts a tiny web component that scrolls the nearest scrollable parent to bottom.

    Remount by changing the key (e.g., tie to len(messages)) to force scrolling again
    when new messages arrive.
    """
    return mel.insert_web_component(
        name='scroll-bottom-el',
        key=key,
        events={},
        properties={},
    )
