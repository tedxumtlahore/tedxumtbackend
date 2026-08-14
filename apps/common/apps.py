from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = 'Common'

    def ready(self):
        # Import here, not at module level: `ready()` is the first point at
        # which every model is loaded and can be inspected for file fields.
        from .cleanup import register_media_cleanup

        register_media_cleanup()
