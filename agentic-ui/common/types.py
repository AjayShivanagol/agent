# Compatibility re-exports so legacy tests can import common.types
# These map to the a2a-sdk Message part types used in the codebase.
try:
    from a2a.types import DataPart, FilePart, TextPart
except Exception as e:
    # Provide minimal shims to avoid import errors during test collection
    # Note: These are placeholders and won't be used if a2a is installed.
    class _Base:
        pass
    class DataPart(_Base):
        def __init__(self, data=None):
            self.data = data
            self.kind = 'data'
    class FileLike:
        def __init__(self, uri: str = '', mimeType: str = ''):
            self.uri = uri
            self.mimeType = mimeType
    class FilePart(_Base):
        def __init__(self, file=None):
            self.file = file or FileLike()
            self.kind = 'file'
    class TextPart(_Base):
        def __init__(self, text: str = ''):
            self.text = text
            self.kind = 'text'
