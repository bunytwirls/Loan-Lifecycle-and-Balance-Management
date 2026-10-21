class ServiceError(Exception):
    """Public service error: status is an HTTP status, code is a stable string."""
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)
