from django.apps import AppConfig


class PlaygroundConfig(AppConfig):
    name = 'playground'

    def ready(self):
        import playground.signals