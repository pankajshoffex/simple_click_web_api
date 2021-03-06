from simple_click.models import (
    Market, Game, Player, Payment, PaymentHistory, Bet, UserProfile, GameResult, SystemPreferences
)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import F
from django.http import JsonResponse
import pandas as pd
from datetime import datetime, timedelta
from simple_click.helper import get_today_range
from django.db.models import Sum
from simple_click import constants


# 1 = 9.5

def is_time_expired(time_object):
    flag = False
    now = datetime.now() + timedelta(hours=5, minutes=30)
    if now.weekday() == 5:  # Saturday
        if time_object['id'] in [11, 12, 13, 14, 15, 16, 17, 18]:
            flag = True
    elif now.weekday() == 6:  # Sunday
        if time_object['id'] in [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]:
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
                            payment_type=constants.PAYMENT_TYPE_PLAY,
                            transaction_type=constants.TRANSACTION_TYPE_DEBIT,
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


def can_play_cancel(pay_dict):
    flag = False
    condition1 = pay_dict['transaction_date'].date() == datetime.now().date()
    condition2 = pay_dict['payment_type'] == constants.PAYMENT_TYPE_PLAY
    if condition1 and condition2:
        now = datetime.now()
        if now.time() > pay_dict['market_time']:
            flag = False
        else:
            flag = True
    return flag


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
            payment_type__in=[
                constants.PAYMENT_TYPE_WIN,
                constants.PAYMENT_TYPE_PLAY,
                constants.PAYMENT_TYPE_LOSS,
                constants.PAYMENT_TYPE_CANCELLED
            ],
        ).order_by('-transaction_date').annotate(
            transaction_id=F('id'),
            player_game=F('player__game__name'),
            player_game_type=F('player__game__game_type'),
            market_name=F('player__market__market_name'),
            market_type=F('player__market__market_type'),
            market_time=F('player__market__market_time'),
            bet_number=F('bet__bet_number'),
            bet_amount=F('bet__bet_amount'),
            win_amount=F('bet__win_amount'),
            result_status=F('bet__result_status')
        ).values(
            'transaction_id', 'transaction_date', 'transaction_amount', 'transaction_type', 'balance_amount',
            'payment_type', 'user_id', 'player_id', 'bet_id', 'player_game', 'player_game_type', 'market_name',
            'market_type', 'bet_number', 'bet_amount', 'win_amount',
            'result_status', 'market_time'
        )
        if market_id:
            queryset = queryset.filter(
                player__market_id=market_id,
                transaction_date__range=get_today_range(False, True)
            )

        data_frame = pd.DataFrame(list(queryset))
        data_frame['can_cancel'] = False
        # data_frame['can_cancel'] = data_frame.apply(
        #     lambda x: can_play_cancel(x), axis=1)

        context_data['result'] = data_frame.to_dict(orient='records')
        # context_data['result'] = list(queryset)
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
        payment_type = constants.PAYMENT_TYPE_DEPOSIT

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
def cancel_game(request, pk):
    context_data = dict()
    error = False
    msg = 'Sorry you can not cancel the Game.'
    pay_dict = PaymentHistory.objects.filter(
        id=pk
    ).annotate(
        transaction_id=F('id'),
        player_game=F('player__game__name'),
        player_game_type=F('player__game__game_type'),
        market_name=F('player__market__market_name'),
        market_type=F('player__market__market_type'),
        market_time=F('player__market__market_time'),
        bet_number=F('bet__bet_number'),
        bet_amount=F('bet__bet_amount'),
        win_amount=F('bet__win_amount'),
        result_status=F('bet__result_status')
    ).values(
        'transaction_id', 'transaction_date', 'transaction_amount', 'transaction_type', 'balance_amount',
        'payment_type', 'user_id', 'player_id', 'bet_id', 'player_game', 'player_game_type', 'market_name',
        'market_type', 'bet_number', 'bet_amount', 'win_amount',
        'result_status', 'market_time'
    ).first()
    payment_history = PaymentHistory.objects.get(id=pk)
    if payment_history.user.id == request.user.id or request.user.is_superuser:
        can_cancel = can_play_cancel(pay_dict)
        if can_cancel:
            user = UserProfile.objects.get(user=payment_history.user)
            payment_history.payment_type = constants.PAYMENT_TYPE_CANCELLED
            payment_history.transaction_type = constants.TRANSACTION_TYPE_CREDIT
            payment_history.bet.result_status = constants.RESULT_STATUS_CANCELLED
            payment_history.balance_amount += payment_history.bet.bet_amount
            user.account_balance += payment_history.bet.bet_amount
            user.save()
            payment_history.bet.save()
            payment_history.save()
            error = False
            msg = 'Game cancelled successfully.'
    context_data['error'] = error
    context_data['message'] = msg
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, IsAdminUser))
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
                    payment_type=constants.PAYMENT_TYPE_PLAY
                )
                for obj in payment_history:
                    u = UserProfile.objects.get(user=obj.player.user)
                    if game_result.market.id == obj.player.market.id:  # OPEN
                        if int(obj.player.game.game_type) == constants.GAME_TYPE_SINGLE:
                            #
                            # single
                            if int(obj.bet.bet_number) == int(game_result.single):
                                obj.bet.win_amount = obj.bet.bet_amount * \
                                                     constants.GAME_SINGLE_RATE
                                obj.bet.result_status = \
                                    constants.RESULT_STATUS_WIN
                                u.account_balance += obj.bet.win_amount
                                u.save()
                                obj.bet.save()
                                obj.payment_type = constants.PAYMENT_TYPE_WIN
                                obj.transaction_type = \
                                    constants.TRANSACTION_TYPE_CREDIT
                                obj.balance_amount += u.account_balance
                                obj.save()
                            else:
                                obj.bet.result_status = \
                                    constants.RESULT_STATUS_LOSS
                                obj.bet.save()
                                obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                obj.transaction_type = \
                                    constants.TRANSACTION_TYPE_DEBIT
                                obj.save()
                        if int(game_result.panel_type) == constants.PANEL_TYPE_SINGLE:
                            if int(obj.player.game.game_type) == \
                                    constants.GAME_TYPE_SINGLE_PANEL:
                                if int(obj.bet.bet_number) == int(game_result.panel):
                                    obj.bet.win_amount = obj.bet.bet_amount *\
                                                         constants.GAME_SINGLE_PANEL_RATE
                                    obj.bet.result_status = constants.RESULT_STATUS_WIN
                                    u.account_balance += obj.bet.win_amount
                                    u.save()
                                    obj.bet.save()
                                    obj.payment_type = constants.PAYMENT_TYPE_WIN
                                    obj.transaction_type = constants.TRANSACTION_TYPE_CREDIT
                                    obj.balance_amount += u.account_balance
                                    obj.save()
                                else:
                                    obj.bet.result_status = constants.RESULT_STATUS_LOSS
                                    obj.bet.save()
                                    obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                    obj.transaction_type = constants.TRANSACTION_TYPE_DEBIT
                                    obj.save()
                            elif int(obj.player.game.game_type) == \
                                    constants.GAME_TYPE_DOUBLE_PANEL:
                                obj.bet.result_status = constants.RESULT_STATUS_LOSS
                                obj.bet.save()
                                obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                obj.transaction_type = constants.TRANSACTION_TYPE_DEBIT
                                obj.save()
                        elif int(game_result.panel_type) == constants.PANEL_TYPE_DOUBLE:
                            if int(obj.player.game.game_type) == constants.GAME_TYPE_DOUBLE_PANEL:
                                if int(obj.bet.bet_number) == int(game_result.panel):
                                    obj.bet.win_amount = obj.bet.bet_amount *\
                                                         constants.GAME_DOUBLE_PANEL_RATE
                                    obj.bet.result_status = constants.RESULT_STATUS_WIN
                                    u.account_balance += obj.bet.win_amount
                                    u.save()
                                    obj.bet.save()
                                    obj.payment_type = constants.PAYMENT_TYPE_WIN
                                    obj.transaction_type = constants.TRANSACTION_TYPE_CREDIT
                                    obj.balance_amount += u.account_balance
                                    obj.save()
                                else:
                                    obj.bet.result_status = constants.RESULT_STATUS_LOSS
                                    obj.bet.save()
                                    obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                    obj.transaction_type = constants.TRANSACTION_TYPE_DEBIT
                                    obj.save()
                            elif int(obj.player.game.game_type) == \
                                    constants.GAME_TYPE_SINGLE_PANEL:
                                obj.bet.result_status = constants.RESULT_STATUS_LOSS
                                obj.bet.save()
                                obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                obj.transaction_type = constants.TRANSACTION_TYPE_DEBIT
                                obj.save()

                    if game_result.market.id == obj.player.market.id + 1:
                        if int(game_result.market.market_type) == constants.MARKET_TYPE_CLOSE:
                            calculate_market_id = int(game_result.market_id) - 1
                            g_result = GameResult.objects.filter(
                                market_id=calculate_market_id,
                                result_date__range=date_range
                            ).order_by('-id').first()

                            if g_result:
                                if int(obj.player.game.game_type) == \
                                        constants.GAME_TYPE_JODI:
                                    if obj.bet.result_status == constants.RESULT_STATUS_PENDING:
                                        b = str(obj.bet.bet_number)
                                        if len(b) == 1:
                                            b = '0' + b
                                        if b == str(g_result.single) + str(game_result.single):
                                            obj.bet.win_amount = \
                                                obj.bet.bet_amount * \
                                                constants.GAME_JODI_RATE
                                            obj.bet.result_status = \
                                                constants.RESULT_STATUS_WIN
                                            u.account_balance += obj.bet.win_amount
                                            u.save()
                                            obj.bet.save()
                                            obj.payment_type = constants.PAYMENT_TYPE_WIN
                                            obj.transaction_type = constants.TRANSACTION_TYPE_CREDIT
                                            obj.balance_amount += u.account_balance
                                            obj.save()
                                        else:
                                            obj.bet.result_status = \
                                                constants.RESULT_STATUS_LOSS
                                            obj.bet.save()
                                            obj.payment_type = constants.PAYMENT_TYPE_LOSS
                                            obj.transaction_type = \
                                                constants.TRANSACTION_TYPE_DEBIT
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
@permission_classes((IsAuthenticated, IsAdminUser))
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


def get_result_from_market(market_dict, game_results):
    result = '%s-%s'
    try:
        market_id = market_dict['id']
        market_type = market_dict['market_type']
        game_obj = game_results.filter(market_id=market_id).first()
        panel = 'xxx'
        single = 'x'
        if game_obj:
            panel, single = str(game_obj.get('panel', 'xxx')), str(game_obj.get('single', 'x'))
        if market_type == 1:
            result = result % (panel, single)
        else:
            result = result % (single, panel)
    except Exception as e:
        result = ''
    return result


@csrf_exempt
@api_view(["GET"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def daily_result(request):
    try:
        game_result = GameResult.objects.filter(result_date__range=get_today_range(False, True)).values(
            'single', 'panel', 'panel_type', 'result_date', 'id', 'market_id'
        )
        markets_queryset = Market.objects.filter(
            is_active=True
        ).order_by('id').values('id', 'market_name', 'market_type')
        market_df = pd.DataFrame(list(markets_queryset))
        market_df['game_result'] = market_df.apply(lambda x: get_result_from_market(x, game_result), axis=1)
        market_df['market_name'] = market_df['market_name'].apply(lambda x: str(x).lower())
        market_group = market_df.groupby('market_name')
        result = market_group.apply(lambda x: x[:2].to_dict(orient='records')).to_dict()
        market_name_list = []
        for i in markets_queryset.values_list('market_name', flat=True):
            market_name = str(i).lower()
            if market_name not in market_name_list:
                market_name_list.append(market_name)
        error = False
        msg = ''
    except Exception as e:
        error = True
        msg = str(e)
        result = {}
        market_name_list = []
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = result
    context_data['market_name_list'] = market_name_list
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, IsAdminUser))
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
@permission_classes((IsAuthenticated, IsAdminUser))
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
@permission_classes((IsAuthenticated, IsAdminUser))
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
@permission_classes((IsAuthenticated, IsAdminUser))
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
@permission_classes((IsAuthenticated, IsAdminUser))
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
@permission_classes((IsAuthenticated, IsAdminUser))
def get_admin_market_detail(request, pk):
    context_data = dict()
    market_object = Market.objects.filter(id=pk).values(
        'id', 'market_name', 'market_type', 'market_time', 'is_active'
    ).first()
    market_object['market_type_name'] = get_market_type_name(market_object.get('market_type'))
    market_object['market_time'] = market_object.get('market_time').strftime('%I:%M %p')
    context_data['result'] = market_object
    return JsonResponse(context_data, status=200)
