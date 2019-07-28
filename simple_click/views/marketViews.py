from simple_click.models import (
    Market, Game, Player, Payment, PaymentHistory, Bet, UserProfile, GameResult, SystemPreferences
)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import F
from django.http import JsonResponse
import pandas as pd
from datetime import datetime, timedelta
from simple_click.helper import get_today_range
from django.db.models import Sum


# 1 = 9.5
GAME_SINGLE_RATE = 9.5
GAME_JODI_RATE = 90
GAME_SINGLE_PANEL_RATE = 140
GAME_DOUBLE_PANEL_RATE = 280


def is_time_expired(time_object):
    flag = False
    now = datetime.now() + timedelta(hours=5, minutes=30)
    if now.weekday() == 5:  # Saturday
        if time_object['id'] in [11, 12, 13, 14]:
            flag = True
    elif now.weekday() == 6:  # Sunday
        if time_object['id'] in [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]:
            flag = True
    if now.time() > time_object['market_time']:
        flag = True
    return flag


def get_market_type_name(t):
    if t == 1:
        return 'Open'
    else:
        return 'Close'


def get_market_list_view(request):
    context_data = dict()
    queryset = Market.objects.filter(is_active=True).order_by('id').values(
        'id', 'market_name', 'market_type', 'market_time'
    )
    data_frame = pd.DataFrame(list(queryset))
    data_frame['market_type_name'] = data_frame['market_type'].apply(lambda x: get_market_type_name(x))
    data_frame['is_expired'] = data_frame.apply(lambda x: is_time_expired(x), axis=1)
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
@permission_classes((IsAuthenticated, ))
def get_payment_history(request):
    context_data = dict()
    error = False
    msg = ''
    user_id = request.GET.get('user_id', None)
    market_id = request.GET.get('market_id', None)
    user = request.user

    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except Exception as e:
            user = request.user

    try:
        queryset = PaymentHistory.objects.filter(
            user_id=user,
            payment_type__in=[3, 4, 5],
        ).order_by('-transaction_date').annotate(
            transaction_id=F('id'),
            player_game=F('player__game__name'),
            player_game_type=F('player__game__game_type'),
            market_name=F('player__market__market_name'),
            market_type=F('player__market__market_type'),
            bet_number=F('bet__bet_number'),
            bet_amount=F('bet__bet_amount'),
            win_amount=F('bet__win_amount'),
            result_status=F('bet__result_status')
        ).values(
            'transaction_id', 'transaction_date', 'transaction_amount', 'transaction_type', 'balance_amount',
            'payment_type', 'user_id', 'player_id', 'bet_id', 'player_game', 'player_game_type', 'market_name',
            'market_type', 'bet_number', 'bet_amount', 'win_amount', 'result_status'
        )
        if market_id:
            queryset = queryset.filter(
                player__market_id=market_id,
                transaction_date__range=get_today_range(False, True)
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


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def get_customer_balance_history(request):
    context_data = dict()
    error = False
    msg = ''
    payment_type = request.GET.get('payment_type')
    try:
        payment_type = int(payment_type)
    except ValueError:
        payment_type = 1

    try:
        queryset = PaymentHistory.objects.filter(
            user_id=request.user, payment_type=payment_type
        ).order_by('-transaction_date').annotate(
            transaction_id=F('id'),
            player_game=F('player__game__name')
        ).values(
            'transaction_id', 'transaction_date', 'transaction_amount', 'transaction_type', 'balance_amount',
            'payment_type'
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


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, ))
def update_market_result(request):
    error = False
    msg = ''
    market = request.data.get('market')
    single = request.data.get('single')
    panel = request.data.get('panel')
    panel_type = request.data.get('panel_type')
    if not error and not market:
        error = True
        msg = 'Please select market'

    if not error:
        try:
            single = int(single)
        except Exception as e:
            error = True
            msg = 'Please select single'

    if not error and not panel:
        error = True
        msg = 'Please select panel'

    if not error and not panel_type:
        error = True
        msg = 'Please select panel type'

    if not error:
        if not request.user.is_superuser:
            error = True
            msg = 'You are not the admin user'

    if not error:
        try:
            with transaction.atomic():
                game_result = GameResult.objects.create(
                    market_id=market,
                    single=single,
                    panel=panel,
                    panel_type=panel_type
                )
                date_range = get_today_range()
                if game_result.market_id in [13, 14]:
                    date_range = get_today_range(is_past_date=True)
                payment_history = PaymentHistory.objects.filter(
                    transaction_date__range=date_range,
                    player__isnull=False,
                    bet__isnull=False,
                    payment_type=4
                )
                for obj in payment_history:
                    u = UserProfile.objects.get(user=obj.player.user)
                    if game_result.market.id == obj.player.market.id:  # OPEN
                        if int(obj.player.game.game_type) == 1:  # single
                            if int(obj.bet.bet_number) == int(game_result.single):
                                obj.bet.win_amount = obj.bet.bet_amount * GAME_SINGLE_RATE
                                obj.bet.result_status = 1
                                u.account_balance += obj.bet.win_amount
                                u.save()
                                obj.bet.save()
                                obj.payment_type = 3
                                obj.transaction_type = 2
                                obj.balance_amount += u.account_balance
                                obj.save()
                            else:
                                obj.bet.result_status = 2
                                obj.bet.save()
                                obj.payment_type = 5
                                obj.transaction_type = 1
                                obj.save()
                        if int(game_result.panel_type) == 1:
                            if int(obj.player.game.game_type) == 3:
                                if int(obj.bet.bet_number) == int(game_result.panel):
                                    obj.bet.win_amount = obj.bet.bet_amount * GAME_SINGLE_PANEL_RATE
                                    obj.bet.result_status = 1
                                    u.account_balance += obj.bet.win_amount
                                    u.save()
                                    obj.bet.save()
                                    obj.payment_type = 3
                                    obj.transaction_type = 2
                                    obj.balance_amount += u.account_balance
                                    obj.save()
                                else:
                                    obj.bet.result_status = 2
                                    obj.bet.save()
                                    obj.payment_type = 5
                                    obj.transaction_type = 1
                                    obj.save()
                            elif int(obj.player.game.game_type) == 4:
                                obj.bet.result_status = 2
                                obj.bet.save()
                                obj.payment_type = 5
                                obj.transaction_type = 1
                                obj.save()
                        elif int(game_result.panel_type) == 2:
                            if int(obj.player.game.game_type) == 4:
                                if int(obj.bet.bet_number) == int(game_result.panel):
                                    obj.bet.win_amount = obj.bet.bet_amount * GAME_DOUBLE_PANEL_RATE
                                    obj.bet.result_status = 1
                                    u.account_balance += obj.bet.win_amount
                                    u.save()
                                    obj.bet.save()
                                    obj.payment_type = 3
                                    obj.transaction_type = 2
                                    obj.balance_amount += u.account_balance
                                    obj.save()
                                else:
                                    obj.bet.result_status = 2
                                    obj.bet.save()
                                    obj.payment_type = 5
                                    obj.transaction_type = 1
                                    obj.save()
                            elif int(obj.player.game.game_type) == 3:
                                obj.bet.result_status = 2
                                obj.bet.save()
                                obj.payment_type = 5
                                obj.transaction_type = 1
                                obj.save()

                    if game_result.market.id == obj.player.market.id + 1:
                        if int(game_result.market.market_type) == 2:
                            calculate_market_id = int(game_result.market_id) - 1
                            g_result = GameResult.objects.filter(
                                market_id=calculate_market_id,
                                result_date__range=date_range
                            ).order_by('-id').first()

                            if g_result:
                                if int(obj.player.game.game_type) == 2:
                                    if obj.bet.result_status == 3:
                                        b = str(obj.bet.bet_number)
                                        if len(b) == 1:
                                            b = '0' + b
                                        if b == str(g_result.single) + str(game_result.single):
                                            obj.bet.win_amount = obj.bet.bet_amount * GAME_JODI_RATE
                                            obj.bet.result_status = 1
                                            u.account_balance += obj.bet.win_amount
                                            u.save()
                                            obj.bet.save()
                                            obj.payment_type = 3
                                            obj.transaction_type = 2
                                            obj.balance_amount += u.account_balance
                                            obj.save()
                                        else:
                                            obj.bet.result_status = 2
                                            obj.bet.save()
                                            obj.payment_type = 5
                                            obj.transaction_type = 1
                                            obj.save()
            error = False
            msg = 'Ok'
        except Exception as e:
            error = True
            msg = str(e)
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def game_result_list(request):
    error = False
    msg = ''
    context_data = dict()
    game_result = GameResult.objects.filter(result_date__range=get_today_range()).order_by('-id').annotate(
        market_name=F('market__market_name'),
        market_type=F('market__market_type')
    ).values(
        'single', 'panel', 'panel_type', 'result_date', 'id', 'market_id', 'market_name', 'market_type'
    )
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = list(game_result)
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def daily_result(request):
    error = False
    msg = ''
    result = dict()
    game_result = GameResult.objects.filter(result_date__range=get_today_range(False, True)).values(
        'single', 'panel', 'panel_type', 'result_date', 'id', 'market_id'
    )
    time_bazaar_open = game_result.filter(market_id=1).order_by('-id').first()
    if time_bazaar_open:
        time_bazaar_open = dict(time_bazaar_open)
    time_bazaar_close = game_result.filter(market_id=2).order_by('-id').first()
    if time_bazaar_close:
        time_bazaar_close = dict(time_bazaar_close)
    milan_day_open = game_result.filter(market_id=3).order_by('-id').first()
    if milan_day_open:
        milan_day_open = dict(milan_day_open)
    milan_day_close = game_result.filter(market_id=4).order_by('-id').first()
    if milan_day_close:
        milan_day_close = dict(milan_day_close)
    rajdhani_day_open = game_result.filter(market_id=5).order_by('-id').first()
    if rajdhani_day_open:
        rajdhani_day_open = dict(rajdhani_day_open)
    rajdhani_day_close = game_result.filter(market_id=6).order_by('-id').first()
    if rajdhani_day_close:
        rajdhani_day_close = dict(rajdhani_day_close)
    kalyan_open = game_result.filter(market_id=7).order_by('-id').first()
    if kalyan_open:
        kalyan_open = dict(kalyan_open)
    kalyan_close = game_result.filter(market_id=8).order_by('-id').first()
    if kalyan_close:
        kalyan_close = dict(kalyan_close)
    milan_night_open = game_result.filter(market_id=9).order_by('-id').first()
    if milan_night_open:
        milan_night_open = dict(milan_night_open)
    milan_night_close = game_result.filter(market_id=10).order_by('-id').first()
    if milan_night_close:
        milan_night_close = dict(milan_night_close)
    rajdhani_night_open = game_result.filter(market_id=11).order_by('-id').first()
    if rajdhani_night_open:
        rajdhani_night_open = dict(rajdhani_night_open)
    rajdhani_night_close = game_result.filter(market_id=12).order_by('-id').first()
    if rajdhani_night_close:
        rajdhani_night_close = dict(rajdhani_night_close)
    main_mumbai_open = game_result.filter(market_id=13).order_by('-id').first()
    if main_mumbai_open:
        main_mumbai_open = dict(main_mumbai_open)
    main_mumbai_close = game_result.filter(market_id=14).order_by('-id').first()
    if main_mumbai_close:
        main_mumbai_close = dict(main_mumbai_close)
    result['time_bazaar_open'] = time_bazaar_open
    result['time_bazaar_close'] = time_bazaar_close
    result['milan_day_open'] = milan_day_open
    result['milan_day_close'] = milan_day_close
    result['rajdhani_day_open'] = rajdhani_day_open
    result['rajdhani_day_close'] = rajdhani_day_close
    result['kalyan_open'] = kalyan_open
    result['kalyan_close'] = kalyan_close
    result['milan_night_open'] = milan_night_open
    result['milan_night_close'] = milan_night_close
    result['rajdhani_night_open'] = rajdhani_night_open
    result['rajdhani_night_close'] = rajdhani_night_close
    result['main_mumbai_open'] = main_mumbai_open
    result['main_mumbai_close'] = main_mumbai_close
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = result
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def game_report(request):
    error = False
    msg = ''
    market = request.GET.get('market')
    context_data = dict()
    game_result = PaymentHistory.objects.filter(
        player__isnull=False, bet__isnull=False, player__market_id=market,
        transaction_date__range=get_today_range()
    )
    result = {}
    for i in game_result:
        if i.player.game_id in result:
            if i.bet.bet_number in result[i.player.game_id]:
                result[i.player.game_id][i.bet.bet_number] += i.bet.bet_amount
            else:
                result[i.player.game_id][i.bet.bet_number] = i.bet.bet_amount
        else:
            result[i.player.game_id] = {}
            if i.bet.bet_number in result[i.player.game_id]:
                result[i.player.game_id][i.bet.bet_number] += i.bet.bet_amount
            else:
                result[i.player.game_id][i.bet.bet_number] = i.bet.bet_amount
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = result
    return JsonResponse(context_data, status=200)


@csrf_exempt
def get_news(request):
    context_data = dict()
    try:
        obj = SystemPreferences.objects.get(key='news')
        context_data['message'] = obj.value
    except Exception as e:
        context_data['message'] = ''
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, ))
def add_news(request):
    context_data = dict()
    title = request.data.get('title', '')
    status = request.data.get('status', True)
    obj, created = SystemPreferences.objects.get_or_create(key='news')
    obj.value = title
    obj.save()
    obj2, created = SystemPreferences.objects.get_or_create(key='system_status')
    if status:
        obj2.value = 1
    else:
        obj2.value = 0
    obj2.save()
    context_data['error'] = False
    context_data['message'] = "Updated Successfully"
    return JsonResponse(context_data, status=200)


@csrf_exempt
def get_system_info(request):
    context_data = dict()
    try:
        obj = SystemPreferences.objects.get(key='system_status')
        context_data['status'] = int(obj.value)
    except Exception as e:
        context_data['status'] = 1
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def get_user_profit_loss(request):
    context_data = dict()
    user_id = request.GET.get('user_id')
    if user_id:
        try:
            user = UserProfile.objects.get(user_id=user_id)
            queryset = PaymentHistory.objects.filter(
                user_id=user.user_id,
            ).order_by('-transaction_date').values(
                'payment_type', 'transaction_amount', 'transaction_type'
            )
            profit = queryset.filter(payment_type=3).aggregate(Sum('transaction_amount'))
            if profit:
                context_data['profit'] = profit.get('transaction_amount__sum', 0)
            loss = queryset.filter(payment_type=5).aggregate(Sum('transaction_amount'))
            if loss:
                context_data['loss'] = loss.get('transaction_amount__sum', 0)
            withdraw = queryset.filter(payment_type=2).aggregate(Sum('transaction_amount'))
            if withdraw:
                context_data['withdraw'] = withdraw.get('transaction_amount__sum', 0)
            deposit = queryset.filter(payment_type=1).aggregate(Sum('transaction_amount'))
            if deposit:
                context_data['deposit'] = deposit.get('transaction_amount__sum', 0)
            context_data['username'] = user.user.username
        except Exception as e:
            context_data['profit'] = 0
            context_data['loss'] = 0
            context_data['withdraw'] = 0
            context_data['deposit'] = 0
            context_data['username'] = ''
    else:
        context_data['profit'] = 0
        context_data['loss'] = 0
        context_data['withdraw'] = 0
        context_data['deposit'] = 0
        context_data['username'] = ''
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def get_admin_market_list(request):
    context_data = dict()
    queryset = Market.objects.all().order_by('id').values(
        'id', 'market_name', 'market_type', 'market_time', 'is_active'
    )
    data_frame = pd.DataFrame(list(queryset))
    data_frame['market_type_name'] = data_frame['market_type'].apply(lambda x: get_market_type_name(x))
    data_frame['market_time'] = data_frame['market_time'].apply(lambda x: x.strftime('%I:%M %p'))
    context_data['result'] = data_frame.to_dict(orient='records')
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, ))
def create_or_update_market(request):
    context_data = dict()
    error = False
    msg = "Update Successfully"
    market_id = request.data.get('market_id')
    market_name = request.data.get('market_name')
    market_type = request.data.get('market_type')
    market_time = request.data.get('market_time')
    is_active = request.data.get('is_active')
    if not market_name:
        error = True
        msg = 'Market Name is required'
    if not error and not market_type:
        error = True
        msg = 'Market Type is required'
    if not error and not market_time:
        error = True
        msg = 'market time is required'

    if not error:
        try:
            if market_id:
                market_object = Market.objects.get(id=market_id)
                market_object.market_name = market_name
                market_object.market_type = market_type
                market_object.market_time = market_time
                msg = "Update Successfully"
            else:
                market_object = Market.objects.create(
                    market_name=market_name,
                    market_type=market_type,
                    market_time=market_time
                )
                msg = "save Successfully"

            if is_active:
                market_object.is_active = True
            else:
                market_object.is_active = False
            market_object.save()
            error = False
        except Exception as e:
            error = True
            msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def get_admin_market_detail(request, pk):
    context_data = dict()
    market_object = Market.objects.filter(id=pk).values(
        'id', 'market_name', 'market_type', 'market_time', 'is_active'
    ).first()
    market_object['market_type_name'] = get_market_type_name(market_object.get('market_type'))
    market_object['market_time'] = market_object.get('market_time').strftime('%I:%M %p')
    context_data['result'] = market_object
    return JsonResponse(context_data, status=200)
