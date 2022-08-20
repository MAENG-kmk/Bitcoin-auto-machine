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

#선물 잔고 조회
balance = binance.fetch_balance(params={"type": "future"})
print(balance['USDT'])

#수량계산 함수
def cal_amount(usdt_balance, cur_price, leverage):
    portion = 0.99
    usdt_trade = usdt_balance * portion
    amount1 = math.floor((usdt_trade * 1000000)/cur_price) * leverage / 1000000
    return amount1

#포지션 진입 함수
def enter_position(exchange, symbol, cur_price, position, usdt):
    global enter_price
    amount1 = cal_amount(usdt, cur_price, leverage)
    if flow == "up":         #rsi가 40 이하
        position['type'] = 'long'
        position['amount'] = amount1
        exchange.create_market_buy_order(symbol=symbol, amount=amount1)
        enter_price = cur_price
        text = "드가자~ 잔액:{}, 포지션: long".format(usdt)
        send_message(text)
            
    elif flow == "down":      #rsi가 60 이상
        position['type'] = 'short'
        position['amount'] = amount1
        exchange.create_market_sell_order(symbol=symbol, amount=amount1)
        enter_price = cur_price
        text = "드가자~ 잔액:{}, 포지션: short".format(usdt)
        send_message(text)

#포지션 종료 함수
def exit_position(exchange, symbol, position, cur_price, enter_price):
    global target, sell_long, sell_short
    if position['type'] == 'long':
        if target == 0:
            target = enter_price * (1 + 0.008)
        
        if cur_price < enter_price * (1 - 0.004):
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None
            text = "손절합니다.. "
            send_message(text)
        if cur_price > target:
            sell_long = target
            target += enter_price * (0.002)
        if cur_price < sell_long - enter_price * (0.001): 
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! "
            send_message(text)
    elif position['type'] == 'short':
        if target == 0:    
            target = enter_price * (1 - 0.008)

        if cur_price > enter_price * (1 + 0.004):
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "손절합니다.. "
            send_message(text)
        if cur_price < target:
            sell_short = target
            target -= enter_price * (0.002)
        if cur_price > sell_short + enter_price * (0.001):
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None 
            text = "개꿀따라시! "
            send_message(text)

#포지션 종료함수 2
def exit_position2(exchange, symbol, position, candle_shape):
    global half
    amount2 = math.floor(position["amount"] / 2 * 1000) / 1000
    if position['type'] == 'long':
        if candle_shape == "night star" or candle_shape == "hanging" or candle_shape == "meteor" or candle_shape == "down grap":
            exchange.create_market_sell_order(symbol=symbol, amount=amount2)
            position['amount'] -= amount2
            text = "반만뺄게요.. 캔들:{}".format(candle_shape)
            half = 0
            send_message(text)   
    elif position['type'] == 'short':
        if candle_shape == "morning star" or candle_shape == "hammer" or candle_shape == "reverse hammer" or candle_shape == "up grap":
            exchange.create_market_buy_order(symbol=symbol, amount=amount2)
            position['amount'] -= amount2
            text = "반만뺄게요.. 캔들:{}".format(candle_shape)
            half = 0
            send_message(text)
    
#레버리지 설정
markets = binance.load_markets()
symbol = "BTC/USDT"
market = binance.market(symbol)
leverage = 10

resp = binance.fapiPrivate_post_leverage({
    'symbol': market['id'],
    'leverage': leverage
})
        
symbol = "BTC/USDT"
balance = binance.fetch_balance()
usdt = balance['free']['USDT']
position = {
    "type": None,
    "amount": 0
} 
enter_price = 0

target = 0
sell_long = 0
sell_short = 1000000
second_chance = 1
third_chance = 1
half = 1

#동작
while True: 
    try:
        balance = binance.fetch_balance()
        usdt = balance['free']['USDT']

        #현재 가격 가져오고 수량 정하기
        ticker = binance.fetch_ticker(symbol)
        cur_price = ticker['last']
        
        #시장 흐름 파악
        flow = tools.ma(binance, symbol)
        candle_shape = tools.candle(binance, symbol)
        
        #포지션 진입
        if position['type'] == None:
            enter_position(binance, symbol, cur_price, position, usdt)
        
        #포지션 정리
        else:    
            exit_position(binance, symbol, position, cur_price, enter_price)
            if position['type'] is None:
                target = 0
                sell_long = 0
                sell_short = 1000000
                position['amount'] = 0
                balance = binance.fetch_balance()
                usdt = balance['free']['USDT']
                half = 1
                send_message("잔액:{}".format(usdt))
         
        #반갈        
        if half == 1:
            exit_position2(binance, symbol, position, candle_shape)
            
        time.sleep(0.5)
        print(flow, candle_shape)
    except Exception as e:
        print(e)
