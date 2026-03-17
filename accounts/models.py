from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Codes(models.TextChoices):
    FREE = ("free", "Free Plan")
    SILVER = ("silver", "Silver Plan")
    GOLD = ("gold", "Gold Plan")


# Map these to Stripe subscription statuses when you wire it up.
# Stripe has statuses like: 'incomplete', 'trialing', 'active', 'past_due',
# 'canceled', 'unpaid'. You can either store Stripe's values directly,
# or map them into this smaller set.
class StatusChoices(models.TextChoices):
    INACTIVE = ("inactive", "Inactive")
    TRIALING = ("trialing", "Trialing")
    ACTIVE = ("active", "Active")
    PAST_DUE = ("past_due", "Past Due")
    CANCELED = ("canceled", "Canceled")

# Come back and adjust the stripe_product_id as necessary later.
# Plan should create static instances. The "one source of truth".

class Plan(models.Model):
    # Stripe integration notes:
    # - You'll likely create one Stripe Product per Plan, and (commonly) one Stripe Price per billing interval.
    # - `stripe_product_id` stores the Stripe Product id (e.g., 'prod_...').
    # - You will probably add:
    #     - stripe_price_monthly_id (CharField, nullable)
    #     - stripe_price_yearly_id (CharField, nullable)
    #   OR a separate PlanPrice model if you want multiple currencies / intervals cleanly.
    code = models.CharField(max_length=50, unique=True, choices=Codes.choices)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    max_campaigns = models.PositiveSmallIntegerField()
    max_users = models.PositiveSmallIntegerField()
    max_characters_per_user_per_campaign = models.PositiveSmallIntegerField()
    allow_multi_gms = models.BooleanField(default=False)
    allow_party_items = models.BooleanField(default=False)
    # Stripe Product ID (e.g., 'prod_ABC123...'). Optional until Stripe is integrated.
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    # Slug is generated once and stays stable even if Plan name changes later.
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# Subscription = billing state for a single billing owner (user).
class Subscription(models.Model):

    #Stripe integration notes:
    #- Stripe will become the *source of truth* for these fields:
    #    - status
    #    - current_period_end (and possibly current_period_start)
    #    - stripe_customer_id
    #    - stripe_subscription_id
    #- You will update these via Stripe webhooks, not via client-side calls.
    #  (Client creates checkout session; webhooks confirm payment + update DB.)
    #- During development (pre-Stripe), it's OK to set status manually in admin.

    #Likely additions when integrating Stripe:
    #- cancel_at_period_end (bool)
    #- canceled_at (datetime)
    #- trial_end (datetime)
    #- current_period_start (datetime)
    #- stripe_price_id (CharField) or a relation to the chosen price
    #- last_stripe_event_id (for idempotency / replay safety)
    
    billing_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")

    # Keep PROTECT: you should never delete a plan that existing subscriptions refer to.
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")

    # Stripe integration note:
    # - This value should be updated from Stripe webhook events.
    # - Pre-Stripe, you can manually change it to simulate paid/free states.
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.INACTIVE, db_index=True)

    # Stripe integration note:
    # - Customer ID looks like 'cus_...'
    # - Set when you first create/attach a Stripe Customer for this user.
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    # Stripe integration note:
    # - Subscription ID looks like 'sub_...'
    # - Set when Stripe creates the subscription (often through Checkout).
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    # Stripe integration note:
    # - This should mirror Stripe's 'current_period_end' (unix timestamp converted to datetime).
    # - Use timezone-aware datetimes (Django's default when USE_TZ=True).
    current_period_end = models.DateTimeField(blank=True, null=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.billing_owner} - {self.plan.name}"
    
    @property
    def is_active(self) -> bool:
        # Convenience method for feature gating.
        # Stripe integration note: you might decide to treat 'trialing' as active.
        return self.status in (StatusChoices.ACTIVE, StatusChoices.TRIALING)

    class Meta:
        constraints = [
            # Prevent a user from having more than one active or trialing subscription at a time.
            models.UniqueConstraint(
                fields=["billing_owner"],
                condition=models.Q(status=StatusChoices.ACTIVE),
                name="unique_active_subscription_per_user",
            ),
            models.UniqueConstraint(
                fields=["billing_owner"],
                condition=models.Q(status=StatusChoices.TRIALING),
                name="unique_trialing_subscription_per_user",
            ),
        ]