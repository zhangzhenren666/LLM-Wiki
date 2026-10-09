"""add_document_task

Revision ID: 4b2c1d3e5f60
Revises: 3a1b9c0d4e5f
Create Date: 2026-10-09 14:00:00.000000

添加文档 AI 处理任务表与处理记录步骤表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b2c1d3e5f60'
down_revision: Union[str, None] = '3a1b9c0d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_task',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False, comment='关联文档（一个文档一个处理任务）'),
        sa.Column('knowledge_base_id', sa.Integer(), nullable=False, comment='所属知识库'),
        sa.Column('request_id', sa.String(length=128), nullable=True, comment='幂等请求 ID（可选）'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='任务状态'),
        sa.Column('attempts', sa.Integer(), nullable=False, comment='已执行次数（含重试）'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, comment='最大执行次数'),
        sa.Column('progress', sa.Integer(), nullable=False, comment='进度 0-100'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='结束时间'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误摘要（不含完整文档正文）'),
        sa.Column('model_config_id', sa.Integer(), nullable=True, comment='使用的模型配置 ID（预留）'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_base.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='文档 AI 处理任务',
    )
    op.create_index(op.f('ix_document_task_document_id'), 'document_task', ['document_id'], unique=True)
    op.create_index(op.f('ix_document_task_knowledge_base_id'), 'document_task', ['knowledge_base_id'], unique=False)
    op.create_index(op.f('ix_document_task_request_id'), 'document_task', ['request_id'], unique=True)
    op.create_index(op.f('ix_document_task_status'), 'document_task', ['status'], unique=False)

    op.create_table(
        'task_step',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False, comment='所属任务'),
        sa.Column('step_name', sa.String(length=100), nullable=False, comment='步骤名称'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='步骤状态'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='步骤开始时间'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='步骤结束时间'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='失败原因（不含完整文档正文）'),
        sa.Column('page_id', sa.Integer(), nullable=True, comment='关联 Wiki 页面 ID（预留）'),
        sa.Column('relation_id', sa.Integer(), nullable=True, comment='关联关系 ID（预留）'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['document_task.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='处理记录步骤',
    )
    op.create_index(op.f('ix_task_step_task_id'), 'task_step', ['task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_step_task_id'), table_name='task_step')
    op.drop_table('task_step')
    op.drop_index(op.f('ix_document_task_status'), table_name='document_task')
    op.drop_index(op.f('ix_document_task_request_id'), table_name='document_task')
    op.drop_index(op.f('ix_document_task_knowledge_base_id'), table_name='document_task')
    op.drop_index(op.f('ix_document_task_document_id'), table_name='document_task')
    op.drop_table('document_task')
