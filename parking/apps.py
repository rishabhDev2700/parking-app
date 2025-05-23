from django.apps import AppConfig


class ParkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parking'
    def ready(self):
            from parking.signals import create_parking_spaces
