"""add performance analysis

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-08-10 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2b3c4d5e6f7'
down_revision = 'e1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Add user_id to quiz_sessions ─────────────────────────────────
    with op.batch_alter_table('quiz_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(op.f('ix_quiz_sessions_user_id'), ['user_id'], unique=False)

    # ── Step 2: Create performance_analyses table ─────────────────────────────
    op.create_table(
        'performance_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),

        # Deterministic fields (always present)
        sa.Column('performance_level', sa.String(), nullable=False),   # excellent/good/developing/needs_work
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('incorrect_count', sa.Integer(), nullable=False),
        sa.Column('skipped_count', sa.Integer(), nullable=False),
        sa.Column('score_pct', sa.Float(), nullable=False),

        # JSON blobs (stored as TEXT, SQLite-compatible)
        sa.Column('strong_areas', sa.Text(), nullable=True),       # JSON list of TopicInsight
        sa.Column('developing_areas', sa.Text(), nullable=True),   # JSON list of TopicInsight
        sa.Column('priority_areas', sa.Text(), nullable=True),     # JSON list of TopicInsight
        sa.Column('topic_insights', sa.Text(), nullable=True),     # JSON list – full breakdown
        sa.Column('mistake_patterns', sa.Text(), nullable=True),   # JSON list of MistakePattern
        sa.Column('recommendations', sa.Text(), nullable=True),    # JSON list of Recommendation

        # AI-generated fields (may be null if AI call failed)
        sa.Column('overall_summary', sa.Text(), nullable=True),    # AI 2–4 sentence summary
        sa.Column('ai_narrative', sa.Text(), nullable=True),       # Full AI mentor guidance
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='0'),

        # Metadata
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),

        sa.ForeignKeyConstraint(['session_id'], ['quiz_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_performance_analyses_id'), 'performance_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_performance_analyses_session_id'), 'performance_analyses', ['session_id'], unique=True)
    op.create_index(op.f('ix_performance_analyses_space_id'), 'performance_analyses', ['space_id'], unique=False)
    op.create_index(op.f('ix_performance_analyses_user_id'), 'performance_analyses', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_performance_analyses_user_id'), table_name='performance_analyses')
    op.drop_index(op.f('ix_performance_analyses_space_id'), table_name='performance_analyses')
    op.drop_index(op.f('ix_performance_analyses_session_id'), table_name='performance_analyses')
    op.drop_index(op.f('ix_performance_analyses_id'), table_name='performance_analyses')
    op.drop_table('performance_analyses')

    with op.batch_alter_table('quiz_sessions', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_quiz_sessions_user_id'))
        batch_op.drop_column('user_id')
