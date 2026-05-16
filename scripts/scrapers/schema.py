from typing import Literal

from pydantic import BaseModel

BenefitType = Literal["cash", "subsidy", "insurance", "loan", "training", "pension", "scholarship", "other"]
ApplicationMode = Literal["online", "offline", "both"]


class RawScheme(BaseModel):
    slug: str
    name: str
    description: str | None = None
    ministry: str | None = None
    level: Literal["central", "state"]
    state: str | None = None
    categories: list[str] = []
    tags: list[str] = []
    benefit_type: BenefitType | None = None
    benefit_description: str | None = None
    raw_eligibility_text: str | None = None
    application_url: str | None = None
    application_mode: ApplicationMode | None = None
    documents_required: list[str] = []
    source_url: str
    source: str = "myscheme"
