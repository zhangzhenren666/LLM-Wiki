"""add_model_config

Revision ID: 3a1b9c0d4e5f
Revises: 02a23b155fc1
Create Date: 2026-10-09 13:00:00.000000

添加大模型配置表，用于存储 OpenAI Chat Completions 兼容接口的模型配置。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1b9c0d4e5f'
down_revision: Union[str, None] = '02a23b155fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='配置名称'),
        sa.Column('base_url', sa.String(length=1000), nullable=False, comment='OpenAI Chat Completions 兼容的 API Base URL'),
        sa.Column('api_key_encrypted', sa.String(length=1000), nullable=True, comment='加密后的 API Key（响应与日志中绝不返回明文）'),
        sa.Column('model_name', sa.String(length=255), nullable=False, comment='模型名称'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, comment='请求超时时间（秒）'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否启用'),
        sa.Column('is_default', sa.Boolean(), nullable=False, comment='是否为默认配置'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='大模型配置',
    )
    op.create_index(op.f('ix_model_config_name'), 'model_config', ['name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_config_name'), table_name='model_config')
    op.drop_table('model_config')
