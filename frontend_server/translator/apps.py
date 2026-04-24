from django.apps import AppConfig


class TranslatorConfig(AppConfig):
    name = "translator"

    def ready(self) -> None:
        from . import simulation_runner  # noqa: PLC0415

        simulation_runner.resume_all_running()
