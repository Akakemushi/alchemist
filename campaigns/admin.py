from django.contrib import admin
from .models import Campaign, CampaignMembership, Expedition

admin.site.register(Campaign)
admin.site.register(CampaignMembership)
admin.site.register(Expedition)
