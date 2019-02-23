import requests
# import library
import math, random


def send_sms(mobile, code):
    url = 'https://www.fast2sms.com/dev/bulk'
    payload = {
        'sender_id': 'IMATKA',
        'message': 'iMatka Verification Code %s' % (code, ),
        'language': 'english',
        'route': 'p',
        'numbers': mobile,
        # 'flash': '1'
    }
    headers = {'authorization': 'ZJcnFtUN6SzAlDrdR1WkP7GgyOi8hwqb9spT20x5XYQICaumjLLbqn47VhJ3tMx0ICZdoNUgPkziwElX'}
    try:
        r = requests.post(url, data=payload, headers=headers)
        print(r.json())
    except Exception as e:
        print(str(e))


# function to generate OTP
def generateOTP():
    # Declare a digits variable
    # which stores all digits
    digits = "0123456789"
    OTP = ""
    # length of password can be chaged
    # by changing value in range
    for i in range(6):
        OTP += digits[math.floor(random.random() * 10)]

    return OTP

