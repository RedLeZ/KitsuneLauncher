from kitsune.application.services.launch_service import LaunchService
from kitsune.domain.models import LaunchPlan, LaunchRequest, LaunchResult


class _RuntimeStub:
    def build_plan(self, request: LaunchRequest) -> LaunchPlan:
        return LaunchPlan(
            version=request.version,
            install_required=False,
            command_preview=["java", "-jar", "game.jar"],
            launcher_options={"username": request.username},
        )

    def start(self, plan: LaunchPlan) -> LaunchResult:
        return LaunchResult(started=True, pid=12345, message="started")


def test_build_plan_success() -> None:
    service = LaunchService(_RuntimeStub())
    plan = service.build_plan(
        LaunchRequest(
            username="Player123",
            version="1.21.5",
            minecraft_path="/tmp/.minecraft",
            java_path=None,
        )
    )
    assert plan.version == "1.21.5"
    assert plan.launcher_options["username"] == "Player123"


def test_build_plan_rejects_empty_username() -> None:
    service = LaunchService(_RuntimeStub())
    try:
        service.build_plan(
            LaunchRequest(
                username="   ",
                version="1.21.5",
                minecraft_path="/tmp/.minecraft",
                java_path=None,
            )
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "username" in str(exc)
