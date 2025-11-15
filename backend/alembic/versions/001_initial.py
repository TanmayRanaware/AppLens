"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('full_name', sa.String(255), nullable=False, unique=True),
        sa.Column('html_url', sa.String(512), nullable=False),
        sa.Column('default_branch', sa.String(100), default='main'),
        sa.Column('visibility', sa.String(50), default='public'),
        sa.Column('provider', sa.String(50), default='github'),
        sa.Column('owner', sa.String(255), nullable=False),
        sa.Column('last_scanned_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_repositories_full_name', 'repositories', ['full_name'])
    op.create_index('ix_repositories_owner', 'repositories', ['owner'])

    # Create services table
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('path_hint', sa.String(512), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('homepage', sa.String(512), nullable=True),
        sa.Column('last_commit_sha', sa.String(40), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_services_name', 'services', ['name'])

    # Create endpoints table
    op.create_table(
        'endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Enum('HTTP', 'Kafka', 'gRPC', 'Other', name='endpointkind'), nullable=False),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('url_path', sa.String(512), nullable=True),
        sa.Column('topic', sa.String(255), nullable=True),
        sa.Column('direction', sa.Enum('producer', 'consumer', 'client', 'server', name='direction'), nullable=True),
        sa.Column('protocol', sa.String(50), nullable=True),
        sa.Column('code_ref_file', sa.String(512), nullable=True),
        sa.Column('code_ref_line', sa.Integer, nullable=True),
        sa.Column('example_payload_json', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_endpoint_service_kind', 'endpoints', ['service_id', 'kind', 'url_path'])
    op.create_index('idx_endpoint_topic', 'endpoints', ['topic'])

    # Create interactions table
    op.create_table(
        'interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edge_type', sa.Enum('HTTP', 'Kafka', 'gRPC', 'Other', name='edgetype'), nullable=False),
        sa.Column('http_method', sa.String(10), nullable=True),
        sa.Column('http_url', sa.String(512), nullable=True),
        sa.Column('kafka_topic', sa.String(255), nullable=True),
        sa.Column('confidence', sa.Float, default=0.5),
        sa.Column('evidence', sa.Text, nullable=True),
        sa.Column('source_repo_commit_sha', sa.String(40), nullable=True),
        sa.Column('detected_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('detector_name', sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(['source_service_id'], ['services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_service_id'], ['services.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_interaction_source', 'interactions', ['source_service_id'])
    op.create_index('idx_interaction_target', 'interactions', ['target_service_id'])
    op.create_index('idx_interaction_edge_type', 'interactions', ['edge_type', 'kafka_topic'])
    op.create_index('idx_interaction_http', 'interactions', ['http_method', 'http_url'])

    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'success', 'error', name='scanstatus'), default='queued'),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('finished_at', sa.DateTime, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_scans_user_id', 'scans', ['user_id'])

    # Create scan_targets table
    op.create_table(
        'scan_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch', sa.String(100), default='main'),
        sa.Column('commit_sha', sa.String(40), nullable=True),
        sa.Column('subpath', sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ondelete='CASCADE'),
    )

    # Create log_pastes table
    op.create_table(
        'log_pastes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('parsed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_log_pastes_user_id', 'log_pastes', ['user_id'])

    # Create implications table
    op.create_table(
        'implications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('log_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('confidence', sa.Float, default=0.5),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['log_id'], ['log_pastes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )

    # Create doc_chunks table
    op.create_table(
        'doc_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sha', sa.String(40), nullable=True),
        sa.Column('chunk_index', sa.Integer, default=0),
        sa.Column('embedding', sa.Text, nullable=True),  # JSON array for now
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_doc_chunk_repo', 'doc_chunks', ['repo_id'])
    op.create_index('idx_doc_chunk_service', 'doc_chunks', ['service_id'])

    # Create service_graph table
    op.create_table(
        'service_graph',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('in_degree', sa.Integer, default=0),
        sa.Column('out_degree', sa.Integer, default=0),
        sa.Column('last_computed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('service_graph')
    op.drop_table('doc_chunks')
    op.drop_table('implications')
    op.drop_table('log_pastes')
    op.drop_table('scan_targets')
    op.drop_table('scans')
    op.drop_table('interactions')
    op.drop_table('endpoints')
    op.drop_table('services')
    op.drop_table('repositories')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS scanstatus')
    op.execute('DROP TYPE IF EXISTS edgetype')
    op.execute('DROP TYPE IF EXISTS endpointkind')
    op.execute('DROP TYPE IF EXISTS direction')

