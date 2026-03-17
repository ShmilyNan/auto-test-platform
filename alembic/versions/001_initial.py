"""初始数据库表

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # 创建项目表
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)
    
    # 创建项目成员表
    op.create_table(
        'project_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_members_id'), 'project_members', ['id'], unique=False)
    
    # 创建测试用例表
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('body', sa.JSON(), nullable=True),
        sa.Column('assertions', sa.JSON(), nullable=True),
        sa.Column('extract', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('timeout', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_cases_id'), 'test_cases', ['id'], unique=False)
    op.create_index(op.f('ix_test_cases_name'), 'test_cases', ['name'], unique=False)
    op.create_index(op.f('ix_test_cases_project_id'), 'test_cases', ['project_id'], unique=False)
    
    # 创建测试用例集表
    op.create_table(
        'test_suites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('case_ids', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_suites_id'), 'test_suites', ['id'], unique=False)
    op.create_index(op.f('ix_test_suites_name'), 'test_suites', ['name'], unique=False)
    op.create_index(op.f('ix_test_suites_project_id'), 'test_suites', ['project_id'], unique=False)
    
    # 创建测试计划表
    op.create_table(
        'test_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('suite_ids', sa.JSON(), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_plans_id'), 'test_plans', ['id'], unique=False)
    op.create_index(op.f('ix_test_plans_name'), 'test_plans', ['name'], unique=False)
    op.create_index(op.f('ix_test_plans_project_id'), 'test_plans', ['project_id'], unique=False)
    
    # 创建执行记录表
    op.create_table(
        'execution_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('triggered_by', sa.Integer(), nullable=False),
        sa.Column('trigger_type', sa.String(length=20), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('total_cases', sa.Integer(), nullable=True),
        sa.Column('passed_cases', sa.Integer(), nullable=True),
        sa.Column('failed_cases', sa.Integer(), nullable=True),
        sa.Column('skipped_cases', sa.Integer(), nullable=True),
        sa.Column('allure_results_path', sa.String(length=500), nullable=True),
        sa.Column('report_url', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['test_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_records_id'), 'execution_records', ['id'], unique=False)
    op.create_index(op.f('ix_execution_records_plan_id'), 'execution_records', ['plan_id'], unique=False)
    op.create_index(op.f('ix_execution_records_project_id'), 'execution_records', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_execution_records_project_id'), table_name='execution_records')
    op.drop_index(op.f('ix_execution_records_plan_id'), table_name='execution_records')
    op.drop_index(op.f('ix_execution_records_id'), table_name='execution_records')
    op.drop_table('execution_records')
    
    op.drop_index(op.f('ix_test_plans_project_id'), table_name='test_plans')
    op.drop_index(op.f('ix_test_plans_name'), table_name='test_plans')
    op.drop_index(op.f('ix_test_plans_id'), table_name='test_plans')
    op.drop_table('test_plans')
    
    op.drop_index(op.f('ix_test_suites_project_id'), table_name='test_suites')
    op.drop_index(op.f('ix_test_suites_name'), table_name='test_suites')
    op.drop_index(op.f('ix_test_suites_id'), table_name='test_suites')
    op.drop_table('test_suites')
    
    op.drop_index(op.f('ix_test_cases_project_id'), table_name='test_cases')
    op.drop_index(op.f('ix_test_cases_name'), table_name='test_cases')
    op.drop_index(op.f('ix_test_cases_id'), table_name='test_cases')
    op.drop_table('test_cases')
    
    op.drop_index(op.f('ix_project_members_id'), table_name='project_members')
    op.drop_table('project_members')
    
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
