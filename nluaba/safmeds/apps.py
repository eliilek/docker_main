from django.apps import AppConfig


class SafmedsConfig(AppConfig):
    name = 'safmeds'

    def ready(self):
    	import safmeds.signals