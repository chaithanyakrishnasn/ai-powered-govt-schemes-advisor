import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint("level IN ('central', 'state')", name="level"),
        CheckConstraint(
            "benefit_type IN ('cash','subsidy','insurance','loan','training','pension','scholarship','other')",
            name="benefit_type",
        ),
        CheckConstraint(
            "application_mode IN ('online','offline','both')",
            name="application_mode",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    ministry: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'"), default=list
    )
    benefit_type: Mapped[str | None] = mapped_column(Text)
    benefit_amount_min: Mapped[Decimal | None] = mapped_column(Numeric)
    benefit_amount_max: Mapped[Decimal | None] = mapped_column(Numeric)
    benefit_description: Mapped[str | None] = mapped_column(Text)
    application_url: Mapped[str | None] = mapped_column(Text)
    application_mode: Mapped[str | None] = mapped_column(Text)
    documents_required: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'"), default=list
    )
    raw_eligibility_text: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    source_url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_updated: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    eligibility_rules: Mapped[list["EligibilityRule"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    translations: Mapped[list["SchemeTranslation"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Scheme id={self.id} slug={self.slug!r}>"


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"
    __table_args__ = (
        CheckConstraint(
            "operator IN ('eq','neq','lt','lte','gt','gte','in','not_in','between','exists','any_of','all_of')",
            name="operator",
        ),
        CheckConstraint(
            "group_operator IN ('AND','OR')",
            name="group_operator",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"))
    rule_type: Mapped[str] = mapped_column(Text)
    operator: Mapped[str] = mapped_column(Text)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    logic_group: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    group_operator: Mapped[str] = mapped_column(Text, server_default="'AND'", default="AND")
    is_required: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    scheme: Mapped["Scheme"] = relationship(back_populates="eligibility_rules")

    def __repr__(self) -> str:
        return f"<EligibilityRule id={self.id} rule_type={self.rule_type!r}>"


class SchemeTranslation(Base):
    __tablename__ = "scheme_translations"
    __table_args__ = (
        CheckConstraint(
            "language IN ('hi','kn','ta','te','mr','bn')",
            name="language",
        ),
        UniqueConstraint(
            "scheme_id", "language", name="uq_scheme_translations_scheme_id_language"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    benefit_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    scheme: Mapped["Scheme"] = relationship(back_populates="translations")

    def __repr__(self) -> str:
        return (
            f"<SchemeTranslation id={self.id} "
            f"scheme_id={self.scheme_id} language={self.language!r}>"
        )


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "gender IN ('male','female','other','prefer_not_to_say')",
            name="gender",
        ),
        CheckConstraint(
            "caste_category IN ('GEN','OBC','SC','ST','EWS')",
            name="caste_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    annual_income: Mapped[Decimal | None] = mapped_column(Numeric)
    occupation: Mapped[str | None] = mapped_column(Text)
    caste_category: Mapped[str | None] = mapped_column(Text)
    religion: Mapped[str | None] = mapped_column(Text)
    is_farmer: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    land_holding_acres: Mapped[Decimal | None] = mapped_column(Numeric)
    education_level: Mapped[str | None] = mapped_column(Text)
    marital_status: Mapped[str | None] = mapped_column(Text)
    family_size: Mapped[int | None] = mapped_column(Integer)
    has_disability: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    disability_percentage: Mapped[int | None] = mapped_column(Integer)
    employment_status: Mapped[str | None] = mapped_column(Text)
    preferred_language: Mapped[str] = mapped_column(Text, server_default="'en'", default="en")
    session_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    matches: Mapped[list["SchemeMatch"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserProfile id={self.id}>"


class SchemeMatch(Base):
    __tablename__ = "scheme_matches"
    __table_args__ = (
        CheckConstraint(
            "eligibility_status IN ('eligible','likely_eligible','need_more_info','not_eligible')",
            name="eligibility_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE")
    )
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"))
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    eligibility_status: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)
    matched_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    matched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    user: Mapped["UserProfile"] = relationship(back_populates="matches")
    scheme: Mapped["Scheme"] = relationship()

    def __repr__(self) -> str:
        return f"<SchemeMatch id={self.id} user_id={self.user_id} scheme_id={self.scheme_id}>"
