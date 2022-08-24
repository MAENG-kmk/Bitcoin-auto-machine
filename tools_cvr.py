import pandas as pd

# 캔들 모양
def candle(df):

    if df.iloc[-2]['high'] - max(df.iloc[-2]['open'], df.iloc[-2]['close']) > df.iloc[-2]['body']:
        if df.iloc[-2]['high'] - max(df.iloc[-2]['open'], df.iloc[-2]['close']) > 200:
            return "meteor" # 유성형
    
    if min(df.iloc[-2]['open'], df.iloc[-2]['close']) - df.iloc[-2]['low'] > df.iloc[-2]['body']:
        if min(df.iloc[-2]['open'], df.iloc[-2]['close']) - df.iloc[-2]['low'] > 200:
            return "hammer" # 망치형
        
# rsi 지표
def rsi(df): 
    au = 0
    u = 0
    ad = 0
    d = 0
    # cur = cur_price - df.iloc[-1]['open']
    for i in df.iloc[-2:-16:-1]['size']:
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

# 거래량 비교
def volume(df):
    volume1 = df.iloc[-2]['volume']
    volume2 = df.iloc[-3]['volume']
    if volume1 > volume2 * 1.5:
        return "go"
    else:
        return "stop"