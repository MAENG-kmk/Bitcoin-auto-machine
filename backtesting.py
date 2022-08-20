import ccxt
import numpy as np
import pandas as pd


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
symbol = "BTC/USDT"
btc = binance.fetch_ohlcv(
        symbol=symbol,
        timeframe='1h', 
        since=None, 
        limit=24*30
    )
df = pd.DataFrame(data=btc, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
df['body'] = abs(df['close'] - df['open'])
df['size'] = df['close'] - df['open'] 
df.set_index('datetime', inplace=True)

# rsi 지표
def rsi(df): 
    au = 0
    u = 0
    ad = 0
    d = 0
    # cur = cur_price - df.iloc[-1]['open']
    for i in df.iloc[:14]['size']:
        if i >= 0:
            au += i
            u += 1
        else:
            ad += -i
            d += 1
    au /= u
    ad /= d
    # if cur >= 0:
    #     au += cur / 14
    # else:
    #     ad += cur / 14 * (-1)
    rs = au / ad
    rsi = rs / ( 1 + rs) * 100
    
    return rsi

# 캔들 모양
def candle(df):
    market_trend = rsi(df)

    if df.iloc[-2]['high'] - max(df.iloc[-2]['open'], df.iloc[-2]['close']) > df.iloc[-2]['body']:
        if df.iloc[-2]['high'] - max(df.iloc[-2]['open'], df.iloc[-2]['close']) > 200:
            return "meteor" # 유성형
    
    if min(df.iloc[-2]['open'], df.iloc[-2]['close']) - df.iloc[-2]['low'] > df.iloc[-2]['body']:
        if min(df.iloc[-2]['open'], df.iloc[-2]['close']) - df.iloc[-2]['low'] > 200:
            return "hammer" # 망치형

# 거래량 비교
def volume(df):
    volume1 = df.iloc[-2]['volume']
    volume2 = df.iloc[-3]['volume']
    if volume1 > volume2 * 1.5:
        return "go"
    else:
        return "stop"

#백테스팅 코드
class candle_volume_rsi:
    def __init__(self, data, balance):
        self.data = data        # 4h 차트 데이터
        self.balance = balance  # 잔고
        self.fee = 0.008        # 매수 매도 총 수수료
        #포지션
        self.position = None
        # 수익률
        self.ror= 1
        # 승리 횟수
        self.win = 0
        # 패배 횟수
        self.lose = 0
        #체결가
        self.price = 0
        #이익 판매가
        self.win_price = 0
        #손해 판매가
        self.lose_price = 0
    
    def excute(self):
        for i in range(20, len(self.data)):
            df = self.data[i - 16:i + 1]
            if self.position == None:
                if rsi(df) > 45:
                    # if volume(df) == "go":
                        if candle(df) == "meteor":
                            self.position = "short"
                            self.price = self.data.iloc[i]['open']
                            self.win_price = self.price * 0.99
                            self.lose_price = self.price * 1.005
                elif rsi(df) < 45:
                    # if volume(df) == "go":
                        if candle(df) == "hammer":
                            self.position = "long"
                            self.price = self.data.iloc[i]['open']
                            self.win_price = self.price * 1.01
                            self.lose_price = self.price * 0.995
            elif self.position == "short":
                if self.data.iloc[i]['high'] >= self.win_price and self.data.iloc[i]['low'] <= self.win_price:
                    self.ror *= (1.1 - self.fee)
                    self.position = None
                    self.price, self.win_price, self.lose_price = 0, 0, 0
                    self.win += 1
                elif self.data.iloc[i]['high'] >= self.win_price and self.data.iloc[i]['low'] <= self.lose_price:
                    self.ror *= (0.95 - self.fee)
                    self.position = None
                    self.price, self.win_price, self.lose_price = 0, 0, 0
                    self.lose += 1
            else:
                if self.data.iloc[i]['high'] >= self.win_price and self.data.iloc[i]['low'] <= self.win_price:
                    self.ror *= (1.1 - self.fee)
                    self.position = None
                    self.price, self.win_price, self.lose_price = 0, 0, 0
                    self.win += 1
                elif self.data.iloc[i]['high'] >= self.win_price and self.data.iloc[i]['low'] <= self.lose_price:
                    self.ror *= (0.95 - self.fee)
                    self.position = None
                    self.price, self.win_price, self.lose_price = 0, 0, 0
                    self.lose += 1
    def result(self):
        print(self.ror)
        print(self.win)
        print(self.lose)
            
            
backtest = candle_volume_rsi(df, 10000)
backtest.excute()
backtest.result()