class AIServiceError(Exception):
    def __init__(self, message: str, provider: str, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class STTError(AIServiceError):
    pass


class CoachError(AIServiceError):
    pass


class TTSError(AIServiceError):
    pass
