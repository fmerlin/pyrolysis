class Resource:
    def __init__(self, uri=None, output=None, modified=None, expires=None):
        self.uri = uri
        self.output = output
        self.modified = modified
        self.expires = expires

    def __str__(self):
        return self.uri
