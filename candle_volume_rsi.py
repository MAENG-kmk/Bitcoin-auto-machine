import ccxt
import pprint
import time
from numpy import short
import pandas as pd
import datetime
import tools_cvr
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
def enter_position(exchange, symbol, cur_price, position, usdt, candle, rsi, volume, leverage, prev_candle):
    amount = cal_amount(usdt, cur_price, leverage)
    if volume == "go":
        if candle == "meteor":
            if rsi > 45:
                position['type'] = "short"
                position['amount'] = amount
                position['cut_price'] = cur_price * 1.01
                position['prev'] = prev_candle
                exchange.create_market_sell_order(symbol=symbol, amount=amount)
                ms = "포지션:{}, 잔액:{}".format(position['type'], usdt)
                send_message(ms)
        elif candle == "hammer":
            if rsi > 45:
                position['type'] = "long"
                position['amount'] = amount
                position['cut_price'] = cur_price * 0.99
                position['prev'] = prev_candle
                exchange.create_market_buy_order(symbol=symbol, amount=amount)
                ms = "포지션:{}, 잔액:{}".format(position['type'], usdt)
                send_message(ms)

#포지션 종료 함수
def exit_position(exchange, symbol, position, cur_price, prev_candle, usdt):
    if position['type'] == "short":
        if position['cut_price'] < cur_price:
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = "stop"
            position['amount'] = None
            position['cut_price'] = None
            ms = "긴급탈출! 잔고:{}".format(usdt)
            send_message(ms)
        if position['prev'] != prev_candle:
            exchange.create_market_buy_order(symbol=symbol, amount=position['amount'])
            position['type'] = None
            position['amount'] = None
            position['cut_price'] = None
            position['prev'] = None
            ms = "포지션 정리, 잔고:{}".format(usdt)
            send_message(ms)
    elif position['type'] == "long":
        if position['cut_price'] > cur_price:
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = "stop"
            position['amount'] = None
            position['cut_price'] = None
            ms = "긴급탈출! 잔고:{}".format(usdt)
            send_message(ms)
        if position['prev'] != prev_candle:
            exchange.create_market_sell_order(symbol=symbol, amount=position['amount'])
            position['type'] = None
            position['amount'] = None
            position['cut_price'] = None
            position['prev'] = None
            ms = "포지션 정리, 잔고:{}".format(usdt)
            send_message(ms)
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
    "amount": None,
    "cut_price": None,
    "prev": None,
} 

send_message("Start trading")

#동작
while True: 
    try:
        symbol = "BTC/USDT"
        btc = binance.fetch_ohlcv(
                symbol=symbol,
                timeframe='4h', 
                since=None, 
                limit=20
            )
        df = pd.DataFrame(data=btc, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df['body'] = abs(df['close'] - df['open'])
        df['size'] = df['close'] - df['open'] 
        df.set_index('datetime', inplace=True)

        balance = binance.fetch_balance()
        usdt = balance['free']['USDT']

        candle = tools_cvr.candle(df)   # 이전 캔들 모양
        rsi = tools_cvr.rsi(df)         # rsi지표
        volume = tools_cvr.volume(df)   # 거래량 비교
        
        #현재 가격 가져오고 수량 정하기
        ticker = binance.fetch_ticker(symbol)
        cur_price = ticker['last']
        
        prev_candle = df.iloc[-2]
        
        #포지션 진입
        if position['type'] == None:
            enter_position(binance, symbol, cur_price, position, usdt, candle, rsi, volume, leverage, prev_candle)
            time.sleep(10)
        
        elif position['type'] == "stop":
            if position['prev'] != prev_candle:
                position['type'] = None
                position['prev'] = None
            time.sleep(1)
        #포지션 정리
        else:    
            exit_position(binance, symbol, position, cur_price, prev_candle, usdt)    
            time.sleep(1)
         
    except Exception as e:
        send_message(e)
