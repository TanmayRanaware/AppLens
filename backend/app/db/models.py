"""SQLAlchemy database models"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class EdgeType(str, enum.Enum):
    """Edge type enumeration"""
    HTTP = "HTTP"
    KAFKA = "Kafka"
    GRPC = "gRPC"
    OTHER = "Other"


class EndpointKind(str, enum.Enum):
    """Endpoint kind enumeration"""
    HTTP = "HTTP"
    KAFKA = "Kafka"
    GRPC = "gRPC"
    OTHER = "Other"


class Direction(str, enum.Enum):
    """Direction enumeration"""
    PRODUCER = "producer"
    CONSUMER = "consumer"
    CLIENT = "client"
    SERVER = "server"


class ScanStatus(str, enum.Enum):
    """Scan status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class Repository(Base):
    """Repository model"""
    __tablename__ = "repositories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), unique=True, nullable=False, index=True)
    html_url = Column(String(512), nullable=False)
    default_branch = Column(String(100), default="main")
    visibility = Column(String(50), default="public")
    provider = Column(String(50), default="github")
    owner = Column(String(255), nullable=False, index=True)
    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    services = relationship("Service", back_populates="repo", cascade="all, delete-orphan")
    scan_targets = relationship("ScanTarget", back_populates="repo")


class Service(Base):
    """Service model"""
    __tablename__ = "services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    language = Column(String(50), nullable=True)
    path_hint = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    homepage = Column(String(512), nullable=True)
    last_commit_sha = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    repo = relationship("Repository", back_populates="services")
    endpoints = relationship("Endpoint", back_populates="service", cascade="all, delete-orphan")
    source_interactions = relationship(
        "Interaction",
        foreign_keys="Interaction.source_service_id",
        back_populates="source_service"
    )
    target_interactions = relationship(
        "Interaction",
        foreign_keys="Interaction.target_service_id",
        back_populates="target_service"
    )


class Endpoint(Base):
    """Endpoint model"""
    __tablename__ = "endpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    kind = Column(Enum(EndpointKind), nullable=False)
    method = Column(String(10), nullable=True)  # GET, POST, etc. for HTTP
    url_path = Column(String(512), nullable=True)
    topic = Column(String(255), nullable=True)  # For Kafka
    direction = Column(Enum(Direction), nullable=True)
    protocol = Column(String(50), nullable=True)
    code_ref_file = Column(String(512), nullable=True)
    code_ref_line = Column(Integer, nullable=True)
    example_payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    service = relationship("Service", back_populates="endpoints")
    
    __table_args__ = (
        Index("idx_endpoint_service_kind", "service_id", "kind", "url_path"),
        Index("idx_endpoint_topic", "topic"),
    )


class Interaction(Base):
    """Interaction (edge) model"""
    __tablename__ = "interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    target_service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    edge_type = Column(Enum(EdgeType), nullable=False)
    http_method = Column(String(10), nullable=True)
    http_url = Column(String(512), nullable=True)
    kafka_topic = Column(String(255), nullable=True)
    confidence = Column(Float, default=0.5)
    evidence = Column(Text, nullable=True)
    source_repo_commit_sha = Column(String(40), nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    detector_name = Column(String(100), nullable=True)
    
    source_service = relationship("Service", foreign_keys=[source_service_id], back_populates="source_interactions")
    target_service = relationship("Service", foreign_keys=[target_service_id], back_populates="target_interactions")
    
    __table_args__ = (
        Index("idx_interaction_source", "source_service_id"),
        Index("idx_interaction_target", "target_service_id"),
        Index("idx_interaction_edge_type", "edge_type", "kafka_topic"),
        Index("idx_interaction_http", "http_method", "http_url"),
    )


class Scan(Base):
    """Scan model"""
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)  # GitHub user ID
    status = Column(Enum(ScanStatus), default=ScanStatus.QUEUED)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    targets = relationship("ScanTarget", back_populates="scan", cascade="all, delete-orphan")


class ScanTarget(Base):
    """Scan target model"""
    __tablename__ = "scan_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    branch = Column(String(100), default="main")
    commit_sha = Column(String(40), nullable=True)
    subpath = Column(String(512), nullable=True)
    
    scan = relationship("Scan", back_populates="targets")
    repo = relationship("Repository", back_populates="scan_targets")


class LogPaste(Base):
    """Log paste model"""
    __tablename__ = "log_pastes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parsed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    implications = relationship("Implication", back_populates="log_paste", cascade="all, delete-orphan")


class Implication(Base):
    """Implication model"""
    __tablename__ = "implications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(UUID(as_uuid=True), ForeignKey("log_pastes.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    log_paste = relationship("LogPaste", back_populates="implications")
    service = relationship("Service")


class DocChunk(Base):
    """Document chunk model for embeddings"""
    __tablename__ = "doc_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=True)
    file_path = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    sha = Column(String(40), nullable=True)
    chunk_index = Column(Integer, default=0)
    embedding = Column(Text, nullable=True)  # JSON array or pgvector type
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_doc_chunk_repo", "repo_id"),
        Index("idx_doc_chunk_service", "service_id"),
    )


class ServiceGraph(Base):
    """Materialized view for graph statistics"""
    __tablename__ = "service_graph"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), unique=True, nullable=False)
    in_degree = Column(Integer, default=0)
    out_degree = Column(Integer, default=0)
    last_computed_at = Column(DateTime, default=datetime.utcnow)
    
    service = relationship("Service")

