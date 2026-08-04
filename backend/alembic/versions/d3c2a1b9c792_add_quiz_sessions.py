"""add quiz sessions

Revision ID: d3c2a1b9c792
Revises: b7e1d43f9a21
Create Date: 2026-08-04 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3c2a1b9c792'
down_revision = 'add_user_auth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create quiz_sessions table
    op.create_table(
        'quiz_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('correct_answers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_exam', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('lang', sa.String(), nullable=False, server_default='en'),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_sessions_id'), 'quiz_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_sessions_space_id'), 'quiz_sessions', ['space_id'], unique=False)

    # Add session_id to quiz_attempts
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_quiz_attempts_session_id'), ['session_id'], unique=False)
        batch_op.create_foreign_key('fk_quiz_attempts_session_id_quiz_sessions', 'quiz_sessions', ['session_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Drop foreign key and column from quiz_attempts
    # Note: SQLite alter table support in alembic can be tricky, but this is standard syntax
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_quiz_attempts_session_id_quiz_sessions', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_quiz_attempts_session_id'))
        batch_op.drop_column('session_id')

    # Drop quiz_sessions table
    op.drop_index(op.f('ix_quiz_sessions_space_id'), table_name='quiz_sessions')
    op.drop_index(op.f('ix_quiz_sessions_id'), table_name='quiz_sessions')
    op.drop_table('quiz_sessions')
