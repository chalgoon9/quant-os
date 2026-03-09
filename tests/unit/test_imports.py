from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner


def test_package_imports() -> None:
    import quant_os

    assert quant_os.__version__


def test_cli_entrypoint_imports() -> None:
    from quant_os.cli.main import app

    assert app.info.name == "quant-os"


def test_cli_doctor_subcommand_runs() -> None:
    from quant_os.cli.main import app

    runner = CliRunner()
    config_path = Path(__file__).resolve().parents[2] / "conf" / "base.yaml"
    result = runner.invoke(app, ["doctor", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "system=quant-os-mvp" in result.stdout
    assert "execution:PaperAdapter" in result.stdout


def test_runtime_selects_shadow_and_live_adapters() -> None:
    from quant_os.adapters.live import StubLiveAdapter
    from quant_os.adapters.shadow import ShadowAdapter
    from quant_os.adapters.upbit_live import UpbitLiveAdapter
    from quant_os.config.loader import load_settings
    from quant_os.domain.enums import TradingMode
    from quant_os.services.wiring import build_app_runtime

    config_path = Path(__file__).resolve().parents[2] / "conf" / "base.yaml"
    settings = load_settings(config_path)

    shadow_settings = settings.model_copy(
        update={
            "trading": settings.trading.model_copy(update={"mode": TradingMode.SHADOW}),
        }
    )
    live_settings = settings.model_copy(
        update={
            "trading": settings.trading.model_copy(update={"mode": TradingMode.LIVE}),
        }
    )

    assert isinstance(build_app_runtime(shadow_settings).execution_adapter, ShadowAdapter)
    assert isinstance(build_app_runtime(live_settings).execution_adapter, StubLiveAdapter)

    upbit_live_settings = settings.model_copy(
        update={
            "trading": settings.trading.model_copy(update={"mode": TradingMode.LIVE, "venue": "upbit"}),
        }
    )

    import os

    old_access = os.environ.get("UPBIT_ACCESS_KEY")
    old_secret = os.environ.get("UPBIT_SECRET_KEY")
    os.environ["UPBIT_ACCESS_KEY"] = "test-access"
    os.environ["UPBIT_SECRET_KEY"] = "test-secret"
    try:
        assert isinstance(build_app_runtime(upbit_live_settings).execution_adapter, UpbitLiveAdapter)
    finally:
        if old_access is None:
            os.environ.pop("UPBIT_ACCESS_KEY", None)
        else:
            os.environ["UPBIT_ACCESS_KEY"] = old_access
        if old_secret is None:
            os.environ.pop("UPBIT_SECRET_KEY", None)
        else:
            os.environ["UPBIT_SECRET_KEY"] = old_secret
