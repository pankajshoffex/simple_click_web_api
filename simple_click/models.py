from django.db import models
from django.contrib.auth.models import User


GAME_STATUS = (
    (1, 'Pending'),
    (2, 'Approved')
)

RESULT_STATUS = (
    (1, 'Win'),
    (2, 'Loss'),
    (3, 'Pending')
)

PAYMENT_TYPE = (
    (1, 'Deposit'),
    (2, 'Withdraw'),
    (3, 'Win'),
    (4, 'Play'),
    (5, 'Loss'),
)

TRANSACTION_TYPE = (
    (1, 'Debit'),
    (2, 'Credit')
)

PANEL_TYPE = (
    (1, 'Single'),
    (2, 'Double'),
)


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    mobile = models.CharField(max_length=10)
    is_agreement = models.BooleanField(default=False)
    account_balance = models.FloatField(default=0.0)
    otp = models.IntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return self.user.username


class Payment(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    account_no = models.CharField(max_length=16)
    account_holder_name = models.CharField(max_length=120)
    bank_name = models.TextField()
    ifsc_code = models.CharField(max_length=50)

    def __str__(self):
        return self.bank_name


class Game(models.Model):
    name = models.CharField(max_length=120)
    game_type = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Market(models.Model):
    TYPE = (
        (1, 'Open'),
        (2, 'Close'),
    )
    market_name = models.TextField()
    market_type = models.IntegerField(choices=TYPE, default=1)
    market_time = models.TimeField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.market_name


class Player(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=GAME_STATUS, default=1)

    def __str__(self):
        return self.game.name


class Bet(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    bet_number = models.IntegerField(default=0)
    bet_amount = models.FloatField(default=0.0)
    result_status = models.IntegerField(choices=RESULT_STATUS, default=3)
    win_amount = models.FloatField(default=0.0)

    def __str__(self):
        return self.player.game.name


class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, null=True, on_delete=models.CASCADE)
    bet = models.ForeignKey(Bet, null=True, on_delete=models.CASCADE)
    payment_type = models.IntegerField(choices=PAYMENT_TYPE, default=0)
    transaction_type = models.IntegerField(choices=TRANSACTION_TYPE, default=0)
    transaction_amount = models.FloatField(default=0.0)
    balance_amount = models.FloatField(default=0.0)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class GameResult(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    single = models.IntegerField()
    panel = models.IntegerField()
    panel_type = models.IntegerField(choices=PANEL_TYPE, default=1)
    result_date = models.DateTimeField(auto_now_add=True)


class SystemPreferences(models.Model):
    key = models.CharField(max_length=250, unique=True)
    value = models.TextField()

    def __str__(self):
        return self.key
