import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Persona
from .services import persona_cache_key

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Persona)
@receiver(post_delete, sender=Persona)
def invalidate_persona_cache(sender, instance, **kwargs):
    """Drop the cached persona so edits take effect immediately."""
    cache.delete(persona_cache_key(instance.slug))
    cache.delete("wit:personas:list")
    logger.debug("Invalidated persona cache for slug=%s", instance.slug)
