from django.conf.urls import url
from simple_click.views import userViews, marketViews

urlpatterns = [
    url('api-token-auth/', userViews.login),
    url('new_user/', userViews.new_user),
    url('add_payment/', userViews.add_payment),
    url('get_payment/(?P<pk>\d+)/$', userViews.get_payment),
    url('change_password/', userViews.change_password),
    url('send_forgot_password_otp/', userViews.send_forgot_password_otp),
    url('change_otp_password/', userViews.change_otp_password),
    url('verify_otp/', userViews.verify_otp),
    url('customer_list/', userViews.customer_list),
    url('update_customer_balance/', userViews.update_customer_balance),
    url('get_account_balance/', userViews.get_account_balance),
    url('market_list/', marketViews.get_market_list_view),
    url('submit_game/', marketViews.submit_game_view),
    url('get_payment_history/', marketViews.get_payment_history),
    url('get_customer_balance_history/', marketViews.get_customer_balance_history),
    url('update_market_result/', marketViews.update_market_result),
    url('game_result_list/', marketViews.game_result_list),
]
