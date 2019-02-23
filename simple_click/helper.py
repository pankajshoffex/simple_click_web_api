import requests


def send_sms():
    url = 'https://www.fast2sms.com/dev/bulk'
    payload = {
        'sender_id': 'FSTSMS',
        'message': 'hello',
        'language': 'english',
        'route': 'qt',
        'numbers': '9850436692',
        # 'flash': '1'
    }
    headers = {'authorization': 'ZJcnFtUN6SzAlDrdR1WkP7GgyOi8hwqb9spT20x5XYQICaumjLLbqn47VhJ3tMx0ICZdoNUgPkziwElX'}
    try:
        r = requests.post(url, data=payload, headers=headers)
        print(r.json())
    except Exception as e:
        print(str(e))
