from uuid import UUID


class SchemeNotFoundError(Exception):
    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Scheme not found: {slug}")


class ProfileNotFoundError(Exception):
    def __init__(self, profile_id: UUID):
        self.profile_id = profile_id
        super().__init__(f"Profile not found: {profile_id}")


class LLMUnavailableError(Exception):
    def __init__(self, message: str = "LLM provider is currently unavailable"):
        self.message = message
        super().__init__(self.message)
