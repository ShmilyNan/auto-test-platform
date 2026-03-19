"""add celery_task_id to execution_records

Revision ID: 002_add_celery_task_id
Revises: 001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_celery_task_id'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 celery_task_id 字段
    op.add_column('execution_records',
                  sa.Column('celery_task_id', sa.String(100), nullable=True)
                  )

    # 添加索引
    op.create_index('ix_execution_records_celery_task_id', 'execution_records', ['celery_task_id'])


def downgrade():
    # 删除索引
    op.drop_index('ix_execution_records_celery_task_id', 'execution_records')

    # 删除字段
    op.drop_column('execution_records', 'celery_task_id')
