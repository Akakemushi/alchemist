from django.db import migrations


def backfill_campaign_owners(apps, schema_editor):
    """
    Find any campaign that has no is_owner=True membership and give that role
    to the billing_owner, creating a membership if one doesn't exist yet.
    """
    Campaign = apps.get_model('campaigns', 'Campaign')
    CampaignMembership = apps.get_model('campaigns', 'CampaignMembership')

    for campaign in Campaign.objects.all():
        has_owner = CampaignMembership.objects.filter(
            campaign=campaign, is_owner=True
        ).exists()
        if not has_owner:
            membership, created = CampaignMembership.objects.get_or_create(
                campaign=campaign,
                user=campaign.billing_owner,
                defaults={'is_owner': True},
            )
            if not created:
                membership.is_owner = True
                membership.save()


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0006_unique_campaign_name_per_owner'),
    ]

    operations = [
        migrations.RunPython(
            backfill_campaign_owners,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
