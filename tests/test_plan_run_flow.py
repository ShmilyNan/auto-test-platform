import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from core.constants import ALLURE_RESULTS_DIR

sys.modules.setdefault("toml", SimpleNamespace(load=lambda *args, **kwargs: {}))

import pytest
from fastapi import BackgroundTasks
import api.v1.endpoints.plans as plan_endpoints
import executor.tasks as executor_tasks
import scheduler.tasks as scheduler_tasks
from executor.service import ExecutorService
from plan.service import PlanService


@pytest.mark.asyncio
async def test_dispatch_test_execution_falls_back_to_background_tasks(monkeypatch):
    background_tasks = BackgroundTasks()

    def raise_broker_error(execution_id: int):
        raise RuntimeError(f"broker unavailable for {execution_id}")

    monkeypatch.setattr(executor_tasks.execute_test_task, "delay", raise_broker_error)

    mode = executor_tasks.dispatch_test_execution(123, background_tasks)

    assert mode == "background_tasks"
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func is executor_tasks.execute_test_task_local
    assert task.args == (123,)


@pytest.mark.asyncio
async def test_cancel_execution_persists_orm_changes(monkeypatch):
    execution = SimpleNamespace(
        id=1,
        project_id=42,
        status="pending",
        end_time=None,
        error_message=None,
    )

    class FakeExecutionRepo:
        def __init__(self, session):
            self.session = session
            self.updated = None

        async def get_by_id(self, execution_id: int):
            assert execution_id == 1
            return execution

        async def update(self, record):
            self.updated = record
            return record

    repo = FakeExecutionRepo(session=object())

    async def fake_check_permission(project_id, user_id, session, required_role):
        assert (project_id, user_id, required_role) == (42, 7, "member")
        return True

    monkeypatch.setattr(plan_endpoints, "ExecutionRecordRepository", lambda session: repo)
    monkeypatch.setattr(plan_endpoints, "check_project_permission", fake_check_permission)

    result = await plan_endpoints.cancel_execution(
        execution_id=1,
        session=object(),
        current_user_id=7,
    )

    assert result == {"message": "执行已取消", "execution_id": 1}
    assert execution.status == "cancelled"
    assert execution.error_message == "用户取消执行"
    assert repo.updated is execution
    assert execution.end_time is not None


def test_check_and_execute_scheduled_plans_uses_existing_plan_fields(monkeypatch):
    scheduled_plan = SimpleNamespace(
        id=9,
        name="nightly",
        cron_expression="* * * * *",
        created_by=33,
        enabled=True,
    )
    dispatched_execution_ids = []
    run_calls = []

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [scheduled_plan]

    class FakeSession:
        async def execute(self, stmt):
            return FakeResult()

    class FakeSessionManager:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakePlanService:
        def __init__(self, session):
            self.session = session

        async def run_plan(self, plan_id: int, user_id: int):
            run_calls.append((plan_id, user_id))
            return SimpleNamespace(id=77)

    monkeypatch.setattr(scheduler_tasks, "async_session_maker", lambda: FakeSessionManager())

    import plan.repository as plan_repository
    import plan.service as plan_service
    import executor.tasks as executor_task_module
    import croniter as croniter_module

    monkeypatch.setattr(plan_repository, "TestPlanRepository", lambda session: object())
    monkeypatch.setattr(plan_service, "PlanService", FakePlanService)
    monkeypatch.setattr(croniter_module.croniter, "match", lambda expr, dt: True)
    monkeypatch.setattr(
        executor_task_module,
        "dispatch_test_execution",
        lambda execution_id: dispatched_execution_ids.append(execution_id),
    )

    scheduler_tasks.check_and_execute_scheduled_plans()

    assert run_calls == [(9, 33)]
    assert dispatched_execution_ids == [77]


@pytest.mark.asyncio
async def test_generate_pytest_files_keeps_case_fstring_intact(tmp_path):
    service = ExecutorService()

    output_dir = await service.generate_pytest_files(
        test_cases=[
            {
                "id": 1,
                "name": "health-check",
                "method": "GET",
                "url": "https://example.com/health",
                "headers": {},
                "params": {},
                "body": None,
                "assertions": [],
                "timeout": 30,
            }
        ],
        output_dir=str(tmp_path),
    )

    generated_file = tmp_path / "test_api.py"
    content = generated_file.read_text(encoding="utf-8")

    assert output_dir == str(tmp_path)
    assert generated_file.exists()
    assert "with allure.step(f\"执行测试: {case['name']}\"):" in content
    assert '"name": "health-check"' in content
    assert 'name="响应信息"' in content


@pytest.mark.asyncio
async def test_parse_test_case_results_extracts_request_and_response(tmp_path):
    service = ExecutorService()

    request_attachment = tmp_path / "request.json"
    request_attachment.write_text(
        '{"id": 101, "name": "health-check", "assertions": [{"type": "status_code", "expected": 200}]}',
        encoding="utf-8",
    )
    response_attachment = tmp_path / "response.json"
    response_attachment.write_text(
        '{"status_code": 200, "body": "{\\"ok\\": true}"}',
        encoding="utf-8",
    )
    result_file = tmp_path / "sample-result.json"
    result_file.write_text(
        """
        {
          "name": "health-check",
          "status": "passed",
          "start": 1000,
          "stop": 1250,
          "attachments": [
            {"name": "请求信息", "source": "request.json", "type": "application/json"},
            {"name": "响应信息", "source": "response.json", "type": "application/json"}
          ]
        }
        """,
        encoding="utf-8",
    )

    results = await service.parse_test_case_results(str(tmp_path))

    assert len(results) == 1
    assert results[0]["case_id"] == 101
    assert results[0]["case_name"] == "health-check"
    assert results[0]["duration"] == 250
    assert results[0]["request"]["assertions"][0]["expected"] == 200
    assert results[0]["response"]["status_code"] == 200


@pytest.mark.asyncio
async def test_plan_service_get_execution_includes_case_results(monkeypatch):
    execution = SimpleNamespace(
        id=5,
        plan_id=9,
        project_id=42,
        status="finished",
        triggered_by=7,
        trigger_type="manual",
        start_time=None,
        end_time=None,
        duration=3,
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        skipped_cases=0,
        allure_results_path=ALLURE_RESULTS_DIR,
        report_url=None,
        summary={"passed": 1},
        error_message=None,
        created_at=datetime.now(timezone.utc),
    )
    result = SimpleNamespace(
        id=11,
        execution_id=5,
        case_id=101,
        case_name="health-check",
        status="passed",
        duration=250,
        request={"url": "https://example.com/health"},
        response={"status_code": 200},
        assertions=[{"type": "status_code", "expected": 200}],
        error_message=None,
        stack_trace=None,
        created_at=datetime.now(timezone.utc),
    )

    class FakeExecutionRepo:
        def __init__(self, session):
            self.session = session

        async def get_by_id(self, execution_id: int):
            assert execution_id == 5
            return execution

    class FakeExecutionResultRepo:
        def __init__(self, session):
            self.session = session

        async def list_by_execution(self, execution_id: int):
            assert execution_id == 5
            return [result]

    monkeypatch.setattr("plan.service.ExecutionRecordRepository", FakeExecutionRepo)
    monkeypatch.setattr("plan.service.ExecutionResultRepository", FakeExecutionResultRepo)

    service = PlanService(session=object())
    detail = await service.get_execution(5)

    assert detail is not None
    assert detail.id == 5
    assert len(detail.results) == 1
    assert detail.results[0].case_name == "health-check"
    assert detail.results[0].response["status_code"] == 200