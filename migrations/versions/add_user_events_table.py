"""add user_events table

Revision ID: a8b9c0d1e2f3
Revises: 17b0edb477b0
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = '17b0edb477b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы user_events
    op.create_table(
        'user_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', 'created_at')
    )

    # Создание индексов
    op.create_index('ix_user_events_tg_id', 'user_events',
                    ['tg_id'], unique=False)
    op.create_index('ix_user_events_event_type', 'user_events',
                    ['event_type'], unique=False)
    op.create_index('ix_user_events_created_at', 'user_events',
                    ['created_at'], unique=False)
    op.create_index('idx_user_events_tg_id_created_at', 'user_events', [
                    'tg_id', 'created_at'], unique=False)

    # Преобразование в hypertable TimescaleDB
    # Это выполнится только если TimescaleDB установлен
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM create_hypertable('user_events', 'created_at', 
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Удаление индексов
    op.drop_index('idx_user_events_tg_id_created_at', table_name='user_events')
    op.drop_index('ix_user_events_created_at', table_name='user_events')
    op.drop_index('ix_user_events_event_type', table_name='user_events')
    op.drop_index('ix_user_events_tg_id', table_name='user_events')

    # Удаление таблицы
    op.drop_table('user_events')
