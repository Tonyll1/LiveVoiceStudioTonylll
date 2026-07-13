class ReconnectPolicy:
    def __init__(
        self,
        max_retries: int = 5,
        delay_seconds: int = 5
    ):
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds