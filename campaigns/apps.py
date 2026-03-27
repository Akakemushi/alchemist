from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    name = 'campaigns'

    def ready(self):
        import campaigns.signals  # noqa: F401 — registers signal handlers
