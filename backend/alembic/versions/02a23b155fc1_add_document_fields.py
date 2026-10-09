"""add_document_fields

Revision ID: 02a23b155fc1
Revises: 84cbb2262d26
Create Date: 2026-09-24 17:41:42.028371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '02a23b155fc1'
down_revision: Union[str, None] = '84cbb2262d26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('document') as batch_op:
        batch_op.add_column(sa.Column('knowledge_base_id', sa.Integer(), nullable=False, comment='所属知识库'))
        batch_op.add_column(sa.Column('page_id', sa.Integer(), nullable=True, comment='生成的 Wiki 页面 ID'))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True, comment='失败原因'))
        batch_op.create_index('ix_document_knowledge_base_id', ['knowledge_base_id'])
        batch_op.create_index('ix_document_page_id', ['page_id'])
        batch_op.create_foreign_key('fk_document_kb', 'knowledge_base', ['knowledge_base_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_document_page', 'wiki_page', ['page_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('document') as batch_op:
        batch_op.drop_constraint('fk_document_kb', type_='foreignkey')
        batch_op.drop_constraint('fk_document_page', type_='foreignkey')
        batch_op.drop_index('ix_document_page_id')
        batch_op.drop_index('ix_document_knowledge_base_id')
        batch_op.drop_column('error_message')
        batch_op.drop_column('page_id')
        batch_op.drop_column('knowledge_base_id')