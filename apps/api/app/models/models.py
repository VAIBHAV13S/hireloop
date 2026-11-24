# SQLAlchemy Models for HireLoop

import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    Table,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

# Association tables
candidate_skills = Table(
    "candidate_skills",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
    Column("level", Integer),
    Column("years", Float),
    UniqueConstraint("user_id", "skill_id", name="uq_candidate_skill"),
)

job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
    Column("required", Boolean, nullable=False, server_default="true"),
    UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="candidate")  # candidate, recruiter, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    profile = relationship("CandidateProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("MatchFeedback", back_populates="user", cascade="all, delete-orphan")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name = Column(String)
    headline = Column(String)
    location = Column(String)
    years_exp = Column(Float)
    summary = Column(Text)
    parsed_json = Column(JSONB)
    profile_embedding = Column(Vector(1024))
    embedding_model = Column(String)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")
    skills = relationship("Skill", secondary=candidate_skills, back_populates="candidates")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    storage_key = Column(String, nullable=False)
    raw_text = Column(Text)
    status = Column(String, nullable=False, server_default="uploaded")  # uploaded, parsing, parsed, failed
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="resumes")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    aliases = Column(ARRAY(String), nullable=False, server_default="{}")

    candidates = relationship("CandidateProfile", secondary=candidate_skills, back_populates="skills")
    jobs = relationship("Job", secondary=job_skills, back_populates="skills")

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    website = Column(String)

    jobs = relationship("Job", back_populates="company")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    posted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source = Column(String, nullable=False, default="recruiter")  # recruiter, kaggle, import
    external_id = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String)
    remote_type = Column(String)  # onsite, hybrid, remote
    min_years = Column(Float)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    status = Column(String, nullable=False, server_default="open")  # open, closed, draft
    job_embedding = Column(Vector(1024))
    embedding_model = Column(String)
    tsv = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_job_source_external"),
        Index("jobs_filter", "status", "remote_type", "location"),
        Index("jobs_tsv_gin", "tsv", postgresql_using="gin"),
        Index(
            "jobs_embedding_hnsw",
            "job_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"job_embedding": "vector_cosine_ops"},
        ),
    )

    company = relationship("Company", back_populates="jobs")
    skills = relationship("Skill", secondary=job_skills, back_populates="jobs")

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, server_default="saved")  # saved, applied, interview, offer, rejected
    cover_letter = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)

    user = relationship("User", back_populates="applications")
    job = relationship("Job")

class MatchFeedback(Base):
    __tablename__ = "match_feedback"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    signal = Column(String, primary_key=True)  # viewed, saved, dismissed, applied
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="feedback")
    job = relationship("Job")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, tool
    content = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("messages_conv", "conversation_id", "id"),)

    conversation = relationship("Conversation", back_populates="messages")

class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, nullable=False)  # preference, fact, goal, constraint
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))
    importance = Column(Float, nullable=False, server_default="0.5")
    source_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "memories_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    user = relationship("User", back_populates="memories")
    source_message = relationship("Message")

class LLMCall(Base):
    __tablename__ = "llm_calls"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    purpose = Column(String)
    model = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    latency_ms = Column(Integer)
    cost_usd = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    conversation = relationship("Conversation")
