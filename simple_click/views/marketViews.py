from simple_click.models import Market, Game, Player, Payment, PaymentHistory, Bet, UserProfile
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from django.db.models import F
from django.http import JsonResponse
import pandas as pd
from datetime import datetime, timedelta


def is_time_expired(time_object):
    flag = False
    now = datetime.now() + timedelta(hours=5, minutes=30)
    if now.time() > time_object:
        flag = True
    return flag


def get_market_type_name(t):
    if t == 1:
        return 'Open'
    else:
        return 'Close'


def get_market_list_view(request):
    context_data = dict()
    queryset = Market.objects.all().values(
        'id', 'market_name', 'market_type', 'market_time'
    )
    print(list(queryset))
    data_frame = pd.DataFrame(list(queryset))
    data_frame['market_type_name'] = data_frame['market_type'].apply(lambda x: get_market_type_name(x))
    data_frame['is_expired'] = data_frame['market_time'].apply(lambda x: is_time_expired(x))
    data_frame['market_time'] = data_frame['market_time'].apply(lambda x: x.strftime('%I:%M %p'))
    context_data['result'] = data_frame.to_dict(orient='records')
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny, ))
def submit_game_view(request):
    context_data = dict()
    error = False
    msg = ''
    game_type = request.data.get('game_type')
    market_id = request.data.get('market_id')
    bet_list = request.data.get('bet_list')
    if not error and not game_type:
        error = True
        msg = 'Please select the game type'

    if not error and not market_id:
        error = True
        msg = 'Please select the market id'

    if not error and not bet_list:
        error = True
        msg = 'Please select the betting list'

    user_profile = None
    game_amount = 0
    if not error:
        try:
            for b in bet_list:
                game_amount += b.get('bet_amount', 0)
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.account_balance < game_amount:
                error = True
                msg = 'Insufficient account balance. Please add balance into your account. Your balance is Rs %.2f'
                msg = msg % round(user_profile.account_balance, 2)
        except Exception as e:
            error = True
            msg = 'Error: ' + str(e)

    market_object = None
    if not error:
        market_object = Market.objects.get(id=market_id)
        now = datetime.now() + timedelta(hours=5, minutes=30)
        if now.time() > market_object.market_time:
            error = True
            msg = 'Sorry, Market is closed. Please select different market.'

    if not error:
        try:
            with transaction.atomic():
                game_object = Game.objects.get(game_type=game_type)
                player_object = Player.objects.create(
                    user=user_profile.user,
                    game=game_object,
                    market=market_object
                )
                for bet in bet_list:
                    if bet.get('bet_amount') >= 10:
                        bet_object = Bet.objects.create(
                            player=player_object,
                            bet_number=bet.get('bet_number'),
                            bet_amount=bet.get('bet_amount')
                        )
                        user_profile.account_balance = user_profile.account_balance - bet_object.bet_amount
                        user_profile.save()
                        PaymentHistory.objects.create(
                            user=user_profile.user,
                            player=player_object,
                            bet=bet_object,
                            payment_type=4,
                            transaction_type=1,
                            transaction_amount=bet_object.bet_amount,
                            balance_amount=user_profile.account_balance
                        )
            error = False
            msg = 'Game submitted successfully'
        except Exception as e:
            error = True
            msg = 'Error: ' + str(e)

    context_data['error'] = error
    context_data['message'] = msg
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((AllowAny, ))
def get_payment_history(request):
    context_data = dict()
    error = False
    msg = ''
    try:
        queryset = PaymentHistory.objects.filter(
            user_id=request.user, payment_type__in=[3, 4]
        ).order_by('-transaction_date').annotate(
            transaction_id=F('id'),
            player_game=F('player__game__name')
        ).values(
            'transaction_id', 'transaction_date', 'transaction_amount', 'transaction_type', 'balance_amount',
            'payment_type', 'user_id', 'player_id', 'bet_id', 'player_game'
        )
        context_data['result'] = list(queryset)
        error = False
        msg = ''
    except Exception as e:
        error = True
        msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return JsonResponse(context_data, status=200)
