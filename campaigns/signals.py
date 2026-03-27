from django.db.models.signals import pre_delete
from django.dispatch import receiver


def _resolve_slug_for_no_campaign(character):
    """
    If this character's slug would collide in the no campaign scope
    (owner, slug, campaign=null) after its campaign FK is nulled,
    rename the slug to slug-2, slug-3, … until it's unique.
    The character's display name is left untouched.
    """
    from characters.models import Character
    base = character.slug
    slug = base
    n = 1
    while (Character.objects
           .filter(owner=character.owner, slug=slug, campaign__isnull=True)
           .exclude(pk=character.pk)
           .exists()):
        slug = f"{base}-{n}"
        n += 1
    character.slug = slug


@receiver(pre_delete, sender='campaigns.Campaign')
def resolve_character_slugs_before_campaign_delete(sender, instance, **kwargs):
    """
    Before a Campaign is deleted (which will SET NULL the campaign FK on all its
    Characters), find every character whose slug would collide in the campaign-less
    scope and rename it now, while the FK is still set.
    """
    from characters.models import Character
    for character in Character.objects.filter(campaign=instance).select_related('owner'):
        _resolve_slug_for_no_campaign(character)
        character.is_locked = False
        character.save(update_fields=['slug', 'is_locked'])
