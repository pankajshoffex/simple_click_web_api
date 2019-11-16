from django.db import models
from django.contrib.auth.models import User
from simple_click import constants


GAME_STATUS = (
    (constants.GAME_STATUS_PENDING, 'Pending'),
    (constants.GAME_STATUS_APPROVED, 'Approved')
)

RESULT_STATUS = (
    (constants.RESULT_STATUS_WIN, 'Win'),
    (constants.RESULT_STATUS_LOSS, 'Loss'),
    (constants.RESULT_STATUS_PENDING, 'Pending'),
    (constants.RESULT_STATUS_CANCELLED, 'Cancelled')
)

PAYMENT_TYPE = (
    (constants.PAYMENT_TYPE_DEPOSIT, 'Deposit'),
    (constants.PAYMENT_TYPE_WITHDRAW, 'Withdraw'),
    (constants.PAYMENT_TYPE_WIN, 'Win'),
    (constants.PAYMENT_TYPE_PLAY, 'Play'),
    (constants.PAYMENT_TYPE_LOSS, 'Loss'),
    (constants.PAYMENT_TYPE_CANCELLED, 'Cancelled'),
)

TRANSACTION_TYPE = (
    (constants.TRANSACTION_TYPE_DEBIT, 'Debit'),
    (constants.TRANSACTION_TYPE_CREDIT, 'Credit')
)

PANEL_TYPE = (
    (constants.PANEL_TYPE_SINGLE, 'Single'),
    (constants.PANEL_TYPE_DOUBLE, 'Double'),
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
        (constants.MARKET_TYPE_OPEN, 'Open'),
        (constants.MARKET_TYPE_CLOSE, 'Close'),
    )
    market_name = models.TextField()
    market_type = models.IntegerField(
        choices=TYPE, default=constants.MARKET_TYPE_OPEN
    )
    market_time = models.TimeField()
    created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.market_name


class Player(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(
        choices=GAME_STATUS, default=constants.GAME_STATUS_PENDING
    )

    def __str__(self):
        return self.game.name


class Bet(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    bet_number = models.IntegerField(default=0)
    bet_amount = models.FloatField(default=0.0)
    result_status = models.IntegerField(
        choices=RESULT_STATUS, default=constants.RESULT_STATUS_PENDING
    )
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
    panel_type = models.IntegerField(
        choices=PANEL_TYPE, default=constants.PANEL_TYPE_SINGLE
    )
    result_date = models.DateTimeField(auto_now_add=True)


class SystemPreferences(models.Model):
    key = models.CharField(max_length=250, unique=True)
    value = models.TextField()

    def __str__(self):
        return self.key
