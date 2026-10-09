"""add_relation_fields_and_anomaly

Revision ID: 6d4e3f5a7b82
Revises: 5c3d2e4f6a71
Create Date: 2026-10-09 17:00:00.000000

1. 为 page_relation 添加 relation_reason 和 relation_evidence 字段
2. 创建 relation_anomaly 表（关系异常记录）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d4e3f5a7b82'
down_revision: Union[str, None] = '5c3d2e4f6a71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 为 page_relation 添加新列
    op.add_column(
        'page_relation',
        sa.Column('relation_reason', sa.String(length=500), nullable=True,
                  comment='关系创建理由（简短说明）'),
    )
    op.add_column(
        'page_relation',
        sa.Column('relation_evidence', sa.String(length=2000), nullable=True,
                  comment='支持关系的文本依据'),
    )

    # 2. 创建 relation_anomaly 表
    op.create_table(
        'relation_anomaly',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False, comment='所属处理任务'),
        sa.Column('knowledge_base_id', sa.Integer(), nullable=False, comment='所属知识库'),
        sa.Column('anomaly_type', sa.String(length=30), nullable=False, comment='异常类型'),
        sa.Column('source_page_id', sa.Integer(), nullable=True, comment='源页面（新生成的页面）'),
        sa.Column('target_page_id', sa.Integer(), nullable=True, comment='目标页面（疑似相关/冲突的页面）'),
        sa.Column('reason', sa.Text(), nullable=False, comment='触发原因'),
        sa.Column('evidence', sa.Text(), nullable=True, comment='原文证据'),
        sa.Column('suggestion', sa.Text(), nullable=True, comment='处理建议'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='处理状态'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_base.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_page_id'], ['wiki_page.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_page_id'], ['wiki_page.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['document_task.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='关系异常记录',
    )
    op.create_index(op.f('ix_relation_anomaly_anomaly_type'), 'relation_anomaly', ['anomaly_type'], unique=False)
    op.create_index(op.f('ix_relation_anomaly_knowledge_base_id'), 'relation_anomaly', ['knowledge_base_id'], unique=False)
    op.create_index(op.f('ix_relation_anomaly_source_page_id'), 'relation_anomaly', ['source_page_id'], unique=False)
    op.create_index(op.f('ix_relation_anomaly_status'), 'relation_anomaly', ['status'], unique=False)
    op.create_index(op.f('ix_relation_anomaly_target_page_id'), 'relation_anomaly', ['target_page_id'], unique=False)
    op.create_index(op.f('ix_relation_anomaly_task_id'), 'relation_anomaly', ['task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_relation_anomaly_task_id'), table_name='relation_anomaly')
    op.drop_index(op.f('ix_relation_anomaly_target_page_id'), table_name='relation_anomaly')
    op.drop_index(op.f('ix_relation_anomaly_status'), table_name='relation_anomaly')
    op.drop_index(op.f('ix_relation_anomaly_source_page_id'), table_name='relation_anomaly')
    op.drop_index(op.f('ix_relation_anomaly_knowledge_base_id'), table_name='relation_anomaly')
    op.drop_index(op.f('ix_relation_anomaly_anomaly_type'), table_name='relation_anomaly')
    op.drop_table('relation_anomaly')
    op.drop_column('page_relation', 'relation_evidence')
    op.drop_column('page_relation', 'relation_reason')