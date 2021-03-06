from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q, F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
)
from rest_framework.response import Response
from simple_click.models import UserProfile, Payment, PaymentHistory
from simple_click.helper import generateOTP, send_sms, get_today_range


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def login(request):
    context_data = dict()
    username = request.data.get("username")
    password = request.data.get("password")
    if username is None or password is None:
        return Response({'error': True, 'message': 'Please provide both username and password'},
                        status=HTTP_401_UNAUTHORIZED)
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': True, 'message': 'Invalid Credentials'},
                        status=HTTP_200_OK)
    token, _ = Token.objects.get_or_create(user=user)
    context_data['token'] = token.key
    context_data['error'] = False
    context_data['message'] = 'Login successfully'
    context_data['user'] = {
        'id': user.id,
        'username': user.username,
        'is_active': user.is_active,
        'email': user.email,
        'is_superuser': user.is_superuser
    }
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, ))
def logout(request):
    try:
        token= Token.objects.get(user=request.user)
        token.delete()
        error = False
        msg = 'Logout Successfully.'
    except Exception as e:
        error = True
        msg = str(e)
    context_data = dict()
    context_data['error'] = error
    context_data['result'] = msg
    return JsonResponse(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def new_user(request):
    context_data = dict()
    error = False
    msg = ''
    username = request.data.get('username')
    password = request.data.get('password')
    mobile = request.data.get('mobile')
    is_agreement = request.data.get('is_agreement')
    if not username:
        error = True
        msg = 'Username is required'

    if not error and not password:
        error = True
        msg = 'password is required'

    if not error and not is_agreement:
        error = True
        msg = 'Please select term and condition checkbox'

    if not error:
        try:
            User.objects.get(username=username)
            error = True
            msg = '%s username already taken.' % username
        except Exception as e:
            error = False
            msg = ''

    if not error:
        try:
            UserProfile.objects.get(mobile=mobile)
            error = True
            msg = '%s this mobile no already registered.' % mobile
        except Exception as e:
            error = False
            msg = ''

    if not error:
        try:
            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(user=user, mobile=mobile, is_agreement=is_agreement)
            error = False
            msg = 'User created successfully.'
        except Exception as e:
            error = True
            msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny, IsAdminUser))
def add_payment(request):
    context_data = dict()
    error = False
    msg = ''
    user_id = request.data.get('user_id')
    account_no = request.data.get('account_no')
    account_holder_name = request.data.get('account_holder_name')
    bank_name = request.data.get('bank_name')
    ifsc_code = request.data.get('ifsc_code')

    if not user_id:
        error = True
        msg = 'User id is required'

    if not error and not account_no:
        error = True
        msg = 'Account No is required'

    if not error and not account_holder_name:
        error = True
        msg = 'Account holder name is required'

    if not error and not bank_name:
        error = True
        msg = 'Bank Name is required'

    if not error and not ifsc_code:
        error = True
        msg = 'IFSC Code is required'

    if not error:
        try:
            UserProfile.objects.get(user_id=user_id)
            error = False
            msg = ''
        except Exception as e:
            error = True
            msg = 'User is not valid'

    if not error:
        try:
            payment = Payment.objects.filter(user_id=user_id).first()
            if payment:
                payment.account_no = account_no
                payment.account_holder_name = account_holder_name
                payment.bank_name = bank_name
                payment.ifsc_code = ifsc_code
                payment.save()
            else:
                Payment.objects.create(
                    user_id=user_id,
                    account_no=account_no,
                    account_holder_name=account_holder_name,
                    bank_name=bank_name,
                    ifsc_code=ifsc_code
                )
            error = False
            msg = 'Payment account added successfully.'
        except Exception as e:
            error = True
            msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["GET"])
@permission_classes((AllowAny, ))
def get_payment(request, pk):
    context_data = dict()
    error = False
    msg = ''
    result = {}

    if not error:
        try:
            payment = Payment.objects.get(user_id=pk)
            result = {
                'user_id': payment.user.id,
                'username': payment.user.username,
                'account_no': payment.account_no,
                'account_holder_name': payment.account_holder_name,
                'bank_name': payment.bank_name,
                'ifsc_code': payment.ifsc_code

            }
        except Exception as e:
            result = {}
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = result
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def send_forgot_password_otp(request):
    error = False
    msg = ''
    data = request.data
    try:
        user = User.objects.get(username=data.get('username'))
        u = UserProfile.objects.get(user=user)
        u.otp = generateOTP()
        u.save()
        send_sms(u.mobile, u.otp)
        error = False
        msg = 'OTP has been send successfully.'
    except User.DoesNotExist:
        error = True
        msg = 'User does not exist.'
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, ))
def change_password(request):
    context_data = dict()
    error = False
    msg = ''
    user_id = request.data.get('user_id')
    password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')

    if not user_id:
        error = True
        msg = 'User id is required'

    if not error and not password:
        error = True
        msg = 'New password is required.'

    if not error and not confirm_password:
        error = True
        msg = 'Confirm Password is required'

    if not error and password and confirm_password:
        if password != confirm_password:
            error = True
            msg = 'Password does not matched.'

    if not error:
        try:
            user = User.objects.get(id=user_id)
            user.set_password(confirm_password)
            user.save()
            error = False
            msg = 'Password changed successfully.'
        except Exception as e:
            error = True
            msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, ))
def get_account_balance(request):
    context_data = dict()
    error = False
    msg = ''
    balance = 0
    try:
        user = UserProfile.objects.get(user=request.user)
        balance = round(user.account_balance, 2)
    except Exception as e:
        error = True
        msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    context_data['balance'] = balance
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def change_otp_password(request):
    context_data = dict()
    error = False
    msg = ''
    user_id = request.data.get('username')
    otp = request.data.get('code')
    password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')

    if not user_id:
        error = True
        msg = 'User id is required'

    if not error and not password:
        error = True
        msg = 'New password is required.'

    if not error and not confirm_password:
        error = True
        msg = 'Confirm Password is required'

    if not error and password and confirm_password:
        if password != confirm_password:
            error = True
            msg = 'Password does not matched.'

    if not error:
        try:
            user = User.objects.get(username=user_id)
            u = UserProfile.objects.get(user=user)
            if u.otp == otp:
                user.set_password(confirm_password)
                user.save()
                error = False
                msg = 'Password changed successfully.'
            else:
                error = True
                msg = 'invalid otp'
        except Exception as e:
            error = True
            msg = str(e)
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny, ))
def verify_otp(request):
    context_data = dict()
    error = False
    msg = ''
    user_id = request.data.get('username')
    otp = request.data.get('code')

    if not user_id:
        error = True
        msg = 'User id is required'

    if not error and not otp:
        error = True
        msg = 'Please enter OTP'

    if not error:
        try:
            user = User.objects.get(username=user_id)
            u = UserProfile.objects.get(user=user)
            if u.otp == otp:
                error = False
                msg = 'Ok'
        except Exception as e:
            error = True
            msg = 'Invalid OTP'
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, IsAdminUser))
def customer_list(request):
    error = False
    msg = ''
    search = request.GET.get('q')
    queryset = UserProfile.objects.order_by('id')
    if search:
        queryset = queryset.filter(
            Q(user__id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(mobile__icontains=search)
        )
    queryset = queryset.filter(user__is_active=True, user__is_superuser=False).annotate(
        username=F('user__username'),
        id=F('user__id')
    ).values(
        'id', 'mobile', 'account_balance', 'username'
    )
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = queryset
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, IsAdminUser))
def delete_user(request):
    context_data = dict()
    user_id = request.data.get('user_id')
    try:
        User.objects.get(id=user_id).delete()
        context_data['error'] = False
        context_data['message'] = 'User deleted successfully'
    except Exception as e:
        context_data['error'] = True
        context_data['message'] = str(e)
    return JsonResponse(context_data, status=200)


@csrf_exempt
@api_view(["POST"])
@permission_classes((IsAuthenticated, IsAdminUser))
def update_customer_balance(request):
    error = False
    msg = ''
    user_id = request.data.get('user_id')
    pay_method = request.data.get('method')
    amount = request.data.get('amount')
    if not user_id:
        error = True
        msg = 'User id is required'

    if not error and not pay_method:
        error = True
        msg = 'Payment method is required'
    else:
        try:
            pay_method = int(pay_method)
        except ValueError:
            pay_method = 0
            error = True
            msg = 'Payment method is required'

    if not error and not amount:
        error = True
        msg = 'Amount is required'
    else:
        try:
            amount = float(amount)
        except ValueError:
            amount = 0.0

    if not error:
        if not request.user.is_superuser:
            error = True
            msg = 'You are not the admin user'

    if not error:
        try:
            transaction_type = 1
            user = User.objects.get(id=user_id)
            u = UserProfile.objects.get(user=user)
            if pay_method == 1:  # Deposit
                u.account_balance += amount
                transaction_type = 2
            elif pay_method == 2:  # Withdraw
                if u.account_balance >= amount:
                    u.account_balance -= amount
                    transaction_type = 1
                else:
                    error = True
                    msg = 'Insufficient account balance Rs %s' % (str(amount),)
            if not error:
                u.save()
                PaymentHistory.objects.create(
                    user=u.user,
                    payment_type=pay_method,
                    transaction_type=transaction_type,
                    transaction_amount=amount,
                    balance_amount=u.account_balance
                )
                error = False
                msg = 'Payment Done'
        except Exception as e:
            error = True
            msg = 'Invalid OTP'
    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    return Response(context_data, status=HTTP_200_OK)


@csrf_exempt
@api_view(["GET"])
@permission_classes((IsAuthenticated, IsAdminUser))
def daily_transactions(request):
    error = False
    msg = ''
    search = request.GET.get('q')
    # Default payment type is withdrawal i.e. 2
    payment_type = request.GET.get('transaction_type', 2)
    try:
        payment_type = int(payment_type)
    except Exception as e:
        payment_type = 2
    queryset = PaymentHistory.objects.filter(
        transaction_date__range=get_today_range(),
        payment_type=payment_type
    ).values(
        'transaction_date', 'payment_type', 'transaction_amount', 'balance_amount',
        username=F('user__username'), user_id=F('user__id'),
    )

    if search:
        queryset = queryset.filter(
            Q(user__id__icontains=search) |
            Q(user__username__icontains=search)
        )

    context_data = dict()
    context_data['error'] = error
    context_data['message'] = msg
    context_data['result'] = list(queryset)
    return Response(context_data, status=HTTP_200_OK)
