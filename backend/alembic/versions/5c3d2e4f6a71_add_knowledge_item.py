"""add_knowledge_item

Revision ID: 5c3d2e4f6a71
Revises: 4b2c1d3e5f60
Create Date: 2026-10-09 16:00:00.000000

添加知识提取条目表，记录从文档中提取的每条知识及其状态/来源证据。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c3d2e4f6a71'
down_revision: Union[str, None] = '4b2c1d3e5f60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False, comment='所属处理任务'),
        sa.Column('document_id', sa.Integer(), nullable=False, comment='来源文档'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='知识标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='知识正文（Markdown）'),
        sa.Column('tags', sa.Text(), nullable=True, comment='标签（JSON 数组字符串）'),
        sa.Column('evidence_text', sa.Text(), nullable=True, comment='原文证据片段'),
        sa.Column('page_number', sa.String(length=50), nullable=True, comment='页码'),
        sa.Column('chapter', sa.String(length=255), nullable=True, comment='章节标识'),
        sa.Column('paragraph', sa.String(length=50), nullable=True, comment='段落标识'),
        sa.Column('uncertainty_note', sa.Text(), nullable=True, comment='不确定说明或疑似重复线索'),
        sa.Column('duplicate_candidate_id', sa.Integer(), nullable=True, comment='疑似重复的目标页面 ID'),
        sa.Column('anomaly_reason', sa.Text(), nullable=True, comment='异常原因（程序校验判定）'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='条目状态'),
        sa.Column('wiki_page_id', sa.Integer(), nullable=True, comment='自动生成的 Wiki 页面 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['duplicate_candidate_id'], ['wiki_page.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['document_task.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wiki_page_id'], ['wiki_page.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='知识提取条目',
    )
    op.create_index(op.f('ix_knowledge_item_document_id'), 'knowledge_item', ['document_id'], unique=False)
    op.create_index(op.f('ix_knowledge_item_status'), 'knowledge_item', ['status'], unique=False)
    op.create_index(op.f('ix_knowledge_item_task_id'), 'knowledge_item', ['task_id'], unique=False)
    op.create_index(op.f('ix_knowledge_item_wiki_page_id'), 'knowledge_item', ['wiki_page_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_item_wiki_page_id'), table_name='knowledge_item')
    op.drop_index(op.f('ix_knowledge_item_task_id'), table_name='knowledge_item')
    op.drop_index(op.f('ix_knowledge_item_status'), table_name='knowledge_item')
    op.drop_index(op.f('ix_knowledge_item_document_id'), table_name='knowledge_item')
    op.drop_table('knowledge_item')