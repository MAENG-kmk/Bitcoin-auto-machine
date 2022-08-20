import ccxt
import pprint
import time
from numpy import short
import pandas as pd
import datetime
import tools
import math
import requests
import telegram
import schedule

#바이낸스 객체 생성
api_key = "mF7PJ1yW3YtETZi4uxjDpf5NQGJO2bKedAEMnzBagdux37s5vA8IKnAwhq5CPHZy"
secret = "rsffphg33Pu3CQ1ZUwbiWOYRKKzKGf7hK5YAo9gvjWjYeNYlesTtD170nLE2S84i"

binance = ccxt.binance(config={
    'apiKey': api_key, 
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

#메세지
def send_message(text):
    tele_token = "5210226721:AAG95BNFRPXRME5MU_ytI_JIx7wgiW1XASU"
    chat_id = 5135122806
    bot = telegram.Bot(token = tele_token)
    bot.sendMessage(chat_id = chat_id, text = text)

#상태 확인 메세지
def check_condition():
    global flow, flow_1, position, usdt
    tele_token = "5210226721:AAG95BNFRPXRME5MU_ytI_JIx7wgiW1XASU"
    chat_id = 5135122806
    bot = telegram.Bot(token = tele_token)
    text = "현재 flow:{}, flow_1:{}, 포지션:{}, 잔고:{}".format(flow, flow_1, position['type'], usdt)
    bot.sendMessage(chat_id = chat_id, text = text)
    
schedule.every(30).minutes.do(check_condition)

#수량계산 함수
def cal_amount(usdt_balance, cur_price, leverage):
    portion = 0.99
    usdt_trade = usdt_balance * portion
    amount1 = math.floor((usdt_trade * 1000000)/cur_price) * leverage / 1000000
    return amount1

#포지션 진입 함수
def enter_position(exchange, symbol, cur_price, position, usdt):
    global enter_price, first_time_long, first_time_short, last_price, buy_price, sell_price, flow, flow_1, leverage
    amount1 = cal_amount(usdt, cur_price, leverage)
    if flow == "up" and flow_1 == "up":         #이동평균 > 0
        first_time_short = 1
        if first_time_long == 1:
            buy_price = cur_price + 20
            last_price = cur_price
            first_time_long = 0
        
        else:          
            if cur_price < last_price:
                buy_price = cur_price + 20
                last_price = cur_price
                
            elif cur_price >= buy_price:
                position['type'] = 'long'
                position['amount'] = amount1
                exchange.create_market_buy_order(symbol=symbol, amount=amount1)
                enter_price = cur_price
                text = "드가자~ 현재가:{}, 잔액:{}, 포지션: long".format(cur_price, usdt)
                send_message(text)
                   
    elif flow == "down" and flow_1 == "down":      #이동평균 < 0
        first_time_long = 1
        if first_time_short == 1:
            sell_price = cur_price - 20
            last_price = cur_price
            first_time_short = 0
        else:
            if cur_price > last_price:
                sell_price = cur_price - 20
                last_price = cur_price
                
            elif cur_price <= sell_price:
                position['type'] = 'short'
                position['amount'] = amount1
                exchange.create_market_sell_order(symbol=symbol, amount=amount1)
                enter_price = cur_price
                text = "드가자~ 현재가:{}, 잔액:{}, 포지션: short".format(cur_price, usdt)
                send_message(text)
        
        

#포지션 종료 함수
def exit_position(exchange, symbol, position, cur_price, enter_price):
    global target, close_long, close_short
    if position['type'] == 'long':
        if target == 0:
            target = enter_price * (1 + 0.004)
        
        if cur_price < enter_price * (1 - 0.002):
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None
            text = "손절합니다.. 현재가:{}".format(cur_price)
            send_message(text)
        if cur_price > target:
            close_long = target
            target += 80
        if cur_price < close_long - 30: 
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! 현재가:{}".format(cur_price)
            send_message(text)
            
    elif position['type'] == 'short':
        if target == 0:    
            target = enter_price * (1 - 0.004)

        if cur_price > enter_price * (1 + 0.002):
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "손절합니다.. 현재가:{}".format(cur_price)
            send_message(text)
        if cur_price < target:
            close_short = target
            target -= 80
        if cur_price > close_short + 30:
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! 현재가:{}".format(cur_price)
            send_message(text)
            
#스페셜 포지션 진입
def special_enter_position(exchange, symbol, position, cur_price, usdt):
    global enter_price, leverage
    set_leverage(5, binance)
    leverage = 5
    amount1 = cal_amount(usdt, cur_price, leverage)
    if tools.rsi(exchange, symbol) == "down":
        if tools.candle(exchange, symbol) == "meteor":
            position['type'] = 'special short'
            position['amount'] = amount1
            exchange.create_market_sell_order(symbol=symbol, amount=amount1)
            enter_price = cur_price
            text = "스페셜 포지션 드가자~ 현재가:{}, 잔액:{}, 포지션: short".format(cur_price, usdt)
            send_message(text)
    elif tools.rsi(exchange, symbol) == "up":
        if tools.candle(exchange, symbol) == "hammer":
            position['type'] = 'special long'
            position['amount'] = amount1
            exchange.create_market_buy_order(symbol=symbol, amount=amount1)
            enter_price = cur_price
            text = "스페셜 포지션 드가자~ 현재가:{}, 잔액:{}, 포지션: long".format(cur_price, usdt)
#스페셜 포지션 정리
def special_exit_position(exchange, symbol, position, cur_price, enter_price):
    global target, close_long, close_short
    if position['type'] == 'special long':
        if target == 0:
            target = enter_price * (1 + 0.008)
        
        if cur_price < enter_price * (1 - 0.004):
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None
            text = "손절합니다.. 현재가:{}".format(cur_price)
            send_message(text)
        if cur_price > target:
            close_long = target
            target = cur_price
        if cur_price < close_long - 40: 
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! 현재가:{}".format(cur_price)
            send_message(text)
            
    elif position['type'] == 'special short':
        if target == 0:    
            target = enter_price * (1 - 0.008)

        if cur_price > enter_price * (1 + 0.004):
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "손절합니다.. 현재가:{}".format(cur_price)
            send_message(text)
        if cur_price < target:
            close_short = target
            target -= cur_price
        if cur_price > close_short + 40:
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! 현재가:{}".format(cur_price)
            send_message(text)

#포지션 강제 종료
def super_exit_position(exchange, symbol, position, cur_price):
    if position['type'] == 'long':
        exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
        position['type'] = None
        text = "일단 빼.. 현재가:{}".format(cur_price)
        send_message(text)
    elif position['type'] == 'short':
        exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
        position['type'] = None
        text = "일단 빼.. 현재가:{}".format(cur_price)
        send_message(text)

#레버리지 설정
markets = binance.load_markets()
symbol = "BTC/USDT"
market = binance.market(symbol)
leverage = 1

resp = binance.fapiPrivate_post_leverage({
    'symbol': market['id'],
    'leverage': leverage
})

def set_leverage(leverage, binance):
    symbol = "BTC/USDT"
    market = binance.market(symbol)

    resp = binance.fapiPrivate_post_leverage({
        'symbol': market['id'],
        'leverage': leverage
    })
        
#동작
symbol = "BTC/USDT"
balance = binance.fetch_balance()
usdt = balance['free']['USDT']
position = {
    "type": None,
    "amount": 0
} 
enter_price = 0

target = 0
close_long = 0
close_short = 1000000
first_time_long = 1
first_time_short = 1

send_message("Start trading")
print("Start trading")
while True: 
    try:
        schedule.run_pending()
        
        balance = binance.fetch_balance()
        usdt = balance['free']['USDT']

        #현재 가격 가져오고 수량 정하기
        ticker = binance.fetch_ticker(symbol)
        cur_price = ticker['last']
        
        #시장 흐름 파악
        flow = tools.ma(binance, symbol)
        flow_1 = tools.ma_1(binance, symbol)
        
        #포지션 진입
        if position['type'] == None:
            enter_position(binance, symbol, cur_price, position, usdt)
        
        #포지션 정리
        else:    
            exit_position(binance, symbol, position, cur_price, enter_price)
            if position['type'] is None:
                target = 0
                close_long = 0
                close_short = 1000000
                first_time_short, first_time_long = 1, 1
                position['amount'] = 0
                balance = binance.fetch_balance()
                usdt = balance['free']['USDT']
                send_message("잔액:{}".format(usdt))
        time.sleep(0.5)
        
        #스페셜 포지션 진입
        if position['type'] != "special long" and position['type'] != "special short":
            if tools.rsi(binance, symbol) == "down":
                if tools.candle(binance, symbol) == "meteor":
                    if position['type'] != None:
                        super_exit_position(binance, symbol, position, cur_price)
                    special_enter_position(binance, symbol, position, cur_price, usdt)
                        
            elif tools.rsi(binance, symbol) == "up":
                if tools.candle(binance, symbol) == "hammer":
                    if position['type'] != None:
                        super_exit_position(binance, symbol, position, cur_price)
                    special_enter_position(binance, symbol, position, cur_price, usdt)
        
        #스페셜 포지션 정리
        elif position['type'] == "special long" or position['type'] == "special short":
            special_exit_position(binance, symbol, position, cur_price, enter_price)
            if position['type'] == None:
                set_leverage(1, binance)
                target = 0
                close_long = 0
                close_short = 1000000
                position['amount'] = 0
                balance = binance.fetch_balance()
                usdt = balance['free']['USDT']
                send_message("잔액:{}".format(usdt))
    except Exception as e:
        print(e)
