# models.py

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship

from database import Base  # <-- yahan apne Base ko import karein (jo aapne pehle banaya hai)


# ------------------------------------------------------
# Enums
# ------------------------------------------------------
class PRReviewStatus(str, enum.Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"
    LIMIT_REACHED = "limit_reached"


# ------------------------------------------------------
# Plan – Free / Pro / Enterprise etc.
# ------------------------------------------------------
class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)         # e.g. "Free", "Pro"
    slug = Column(String(50), unique=True, index=True)  # e.g. "free", "pro"
    monthly_pr_limit = Column(Integer, nullable=False)  # e.g. 20, 200, 1000
    monthly_token_limit = Column(Integer, nullable=True)  # optional: AI token based limit
    stripe_price_id = Column(String(100), nullable=True)  # Stripe price ID
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="plan")


# ------------------------------------------------------
# User – mapped to GitHub user + current plan
# ------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # GitHub identity
    github_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    github_username = Column(String(100), index=True, nullable=False)
    email = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Billing / subscription
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)

    # Usage tracking
    pr_used_this_period = Column(Integer, default=0, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=True)  # e.g. billing cycle start
    period_end = Column(DateTime(timezone=True), nullable=True)    # e.g. billing cycle end

    # Meta
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    plan = relationship("Plan", back_populates="users")
    installations = relationship("Installation", back_populates="user")
    pr_reviews = relationship("PRReviewLog", back_populates="user")


# ------------------------------------------------------
# Installation – GitHub App installation
# ------------------------------------------------------
class Installation(Base):
    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, index=True)

    installation_id = Column(BigInteger, unique=True, index=True, nullable=False)
    account_login = Column(String(255), nullable=False)  # org/user login
    account_type = Column(String(50), nullable=True)     # "User" / "Organization"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="installations")
    repositories = relationship("Repository", back_populates="installation")
    pr_reviews = relationship("PRReviewLog", back_populates="installation")


# ------------------------------------------------------
# Repository – which repos are active for reviews
# ------------------------------------------------------
class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)

    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False)
    repo_full_name = Column(String(255), index=True, nullable=False)  # e.g. "abdul/my-app"
    is_active = Column(Boolean, default=True)  # user can disable reviews for a repo

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    installation = relationship("Installation", back_populates="repositories")


# ------------------------------------------------------
# PRReviewLog – each AI review request (for analytics & debugging)
# ------------------------------------------------------
class PRReviewLog(Base):
    __tablename__ = "pr_review_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=True)
    repo_full_name = Column(String(255), nullable=False)
    pr_number = Column(Integer, nullable=False)

    status = Column(Enum(PRReviewStatus), default=PRReviewStatus.SUCCESS, nullable=False)
    tokens_used = Column(Integer, nullable=True)  # if you track from LLM response
    error_message = Column(String(2000), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="pr_reviews")
    installation = relationship("Installation", back_populates="pr_reviews")
