import pyupbit
import datetime
import numpy as np
import time

# 주문불가 key : 모든 IP 사용 가능
#con_key = "..."
#sec_key = "..."

# 주문 가능 key : upbit API key 획득 후 customize
# con_key = "..."
# sec_key = "..."

upbit = pyupbit.Upbit(con_key, sec_key)

'''
for ticker in pyupbit.get_tickers():
    if ticker.split('-')[0]=="KRW":
        balance = upbit.get_balance('-'+ticker.split('-')[1])
        if balance > 0:
            print(ticker, ": ", balance)
            time.sleep(0.1)

'''

'''
order = upbit.buy_limit_order(COI,50,10000)
print(order)

time.sleep(3)
cancel = upbit.cancel_order(order['uuid'])
print(cancel)
'''

def get_ror(ticker, k, itv, period):
    df = pyupbit.get_ohlcv(ticker, itv, period)
    df['ma5'] = df['close'].rolling(window=5).mean().shift(1)
    df['range'] = (df['high']-df['low'])*k
    df['range_shif1'] = df['range'].shift(1)
    df['target'] = df['open'] + df['range'].shift(1)
    df['bull'] = df['open'] > df['ma5']

    fee = 0.0011

    df['ror'] = np.where((df['high']>df['target']) & df['bull'],df['close']/df['target']-fee,1)
    df['benchmark'] = df['close']/df['open']
    df['benchmark_cum']=df['benchmark'].cumprod()
    df['hpr']=df['ror'].cumprod()
    df['dd'] = (df['hpr'].cummax()-df['hpr'])/df['hpr'].cummax()*100
    df['hodl_dd'] = (df['benchmark_cum'].cummax()-df['benchmark_cum'])/df['benchmark_cum'].cummax()*100

    rc = df['ror'].cumprod()[-2]
    benchmark = df['benchmark_cum'][-2]
    df.to_excel("larry_ma.xlsx")
    return rc, df['dd'].max(), benchmark, df['hodl_dd'].max()

def get_max_hpr(ticker, itv, period):
    max_ror_cum = 0
    k_max = 0
    MDD_max =0
    for k in np.arange(0, 1, 0.01):
        ror_cum, dd, bm, hodl_dd = get_ror(ticker, k, itv, period)
        print("%s, k값: %f, 수익률: %f MDD: %f" % (ticker, k, ror_cum, dd))
        if ror_cum > max_ror_cum:
            max_ror_cum = ror_cum
            k_max = k
            MDD_max = dd
        time.sleep(0.01)
    print(period, "기간 대상 %s, 최고수익률: %f 최적 k값: %f MDD: %f, HODL시: %f, HODL시 MDD: %f" % (ticker, max_ror_cum, k_max, MDD_max, bm, hodl_dd))
    return max_ror_cum, k_max, MDD_max

def get_target_price(ticker, k_para, itv):
    df=pyupbit.get_ohlcv(ticker, itv)
    yesterday = df.iloc[-2]
    today_open = yesterday['close']
    yesterday_high = yesterday['high']
    yesterday_low = yesterday['low']
    target = today_open + (yesterday_high - yesterday_low) * k_para
    print("시작가: ", today_open, "변동폭: ", yesterday_high-yesterday_low, "k: ", k_para, "목표가: ", target)
    return(target)

def get_exit_price(ticker, k_para, itv):
    df=pyupbit.get_ohlcv(ticker, itv)
    yesterday = df.iloc[-2]
    today_open = yesterday['close']
    yesterday_high = yesterday['high']
    yesterday_low = yesterday['low']
    ex_price = today_open - (yesterday_high - yesterday_low) * k_para
    return(ex_price)

def buy_crypto_currency(ticker):
    krw = upbit.get_balance("KRW")
    orderbook=pyupbit.get_orderbook(ticker)
    highest_bid = orderbook[0]['orderbook_units'][0]['bid_price']
    #unit = krw/float(sell_price)
    print("매수 함수 실행!")
    # 매수 목표가보다 바로 아래 가격에 리밋 매수주문
    buy_UID = upbit.buy_limit_order(ticker, highest_bid, (krw / highest_bid) - 100)
    # 시장가에 즉시 매수
    # buy_UID = upbit.buy_market_order(ticker, krw-50000)
    print(buy_UID)
    return highest_bid


def sell_crypto_currency(ticker):
    bal = upbit.get_balance(ticker.split('-')[1])
    orderbook=pyupbit.get_orderbook(ticker)
    lowest_ask = orderbook[0]['orderbook_units'][0]['ask_price']
    # unit = 100
    print("매도 함수 실행!")
    sell_UID = upbit.sell_limit_order(ticker, lowest_ask, bal - 100)
    print(sell_UID)
    # print(upbit.sell_market_order(ticker, bal-300))
    return lowest_ask

def get_yesterday_ma5(ticker, itv):
    df = pyupbit.get_ohlcv(ticker, itv)
    close = df['close']
    ma = close.rolling(window=5).mean()
    return ma[-2]

#대상 코인 및 시간간격

COI = "KRW-LTC"
interval = "day"

int_interval = 0
if interval == "minute10":
    int_interval = 10
elif interval == "minute60":
    int_interval = 60
elif interval == "day":
    int_interval = 60 * 24

# 초기화

k=0
max_hpr = 0
max_dd = 0
max_hpr, k, max_dd = get_max_hpr(COI, interval, 300)

target_price = get_target_price(COI, k, interval)
exit_price = get_exit_price(COI, k, interval)
ma5 = get_yesterday_ma5(COI, interval)
itv_high = 0

position = False
vol_rst_counter = 0

sell_balance = upbit.get_balance("KRW")
buy_balance = upbit.get_balance("KRW")
sell_UID = ""
buy_UID = ""
profit = 0

now = datetime.datetime.now()
reset_time = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) + datetime.timedelta(minutes=int_interval)
tolerance = 0
overpace_breakout = False
overpace_breakdown = False
bid_price =0
krw_balance =0
cancel_balance = 0

while True:
    try:
        # 매 초마다 현재가 및 현재 상태 확인
        now = datetime.datetime.now()
        current_price = pyupbit.get_current_price(COI)

        if upbit.get_balance("KRW") < 100000:
            position = True
        else:
            position = False

        # 1시간마다 300기간 k값 재설정
        if vol_rst_counter > 6 :
            max_hpr, k, max_dd = get_max_hpr(COI, interval, 300)
            vol_rst_counter = 0

        # 1기간마다 포지션 정리, HODL여부 결정, 목표가 및 리셋시간 재설정
        if reset_time < now < reset_time + datetime.timedelta(seconds=10):

            #30기간 내 HODL과의 수익률 비교 및 HODL 또는 stay away 여부 결정을 위한 장세 파악
            '''
            print("30기간 VB_ror, VD_MDD, HODL_ror, HODL_ror:", get_ror(COI, k, interval, 30))
            if max(get_ror(COI,k, interval, 30)[0], get_ror(COI, k, interval, 30)[2]) < 1:
                print(upbit.sell_market_order(COI, int(upbit.get_balance(COI.split('-')[1]))))
                print("HODL과 VB 전략 모두 수익이 나지 않아 전량 청산 후 10분 간 실행 중지")
                time.sleep(540)
                vol_rst_counter = vol_rst_counter + 1
                reset_time = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) + datetime.timedelta(minutes=int_interval)
                continue

            elif get_ror(COI, k, interval, 30)[0] < get_ror(COI, k, interval, 30)[2]:
                print(upbit.buy_market_order(COI, int(upbit.get_balance("KRW"))*0.99))
                print("HODL시 수익률이 더 높아 전액 매수 후 10분 간 실행 중지")
                time.sleep(540)
                vol_rst_counter = vol_rst_counter + 1
                reset_time = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) + datetime.timedelta(minutes=int_interval)
                continue

            '''

            # 목표가 및 리셋시간 재설정
            target_price = get_target_price(COI, k, interval)
            itv_high = current_price
            vol_rst_counter = vol_rst_counter + 1
            reset_time = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) + datetime.timedelta(minutes=int_interval)
            ma5 = get_yesterday_ma5(COI, interval)

            # 현재가가 새로운 타깃가보다 낮은 경우에는 포지션 청산
            if current_price < target_price:
                sell_crypto_currency(COI)
                sell_balance = upbit.get_balance("KRW")
                profit = profit + sell_balance - buy_balance
                print("매입가: ", buy_balance, "청산가: ", sell_balance, "수익: ", sell_balance - buy_balance)
                position = False

        # itv_high 변수로 상승장에서 현재 기간 내 최고가 추적
        if current_price>itv_high:
            itv_high=current_price

        # 지난 주기의 캔들 높이를 이용한 tolerance 계산 및 현재 코인보유 포지션인 경우 고점 대비 tolerance 보다 더 많이 하락한 경우 청산

        df_last =pyupbit.get_ohlcv(COI, interval)
        yesterday_candle = df_last.iloc[-2]
        yesterday_candle_high = yesterday_candle['high']
        yesterday_candle_low = yesterday_candle['low']

        if k * 0.5 * (yesterday_candle_high-yesterday_candle_low) > 0.5 * (itv_high-yesterday_candle['close']):
            tolerance = k * 0.5 * (yesterday_candle_high-yesterday_candle_low)
        else:
            tolerance = 0.5 * (itv_high-yesterday_candle['close'])

        print("현재시각: ", now, ", 리셋시간:", reset_time)
        print("k:", k, ", 현재가: ", current_price,", 매수 목표가: ", target_price, ", 5기간 이동평균, ", ma5, ", 기내 최고가:", itv_high, ", 하락청산가: ", itv_high-tolerance, "vol_count:", vol_rst_counter)
        # print("현재가: ", current_price,"매수 목표가: ", target_price, "매도 기준가: ", exit_price)

        if position == True:
            if tolerance >= 3:
                if current_price <= (itv_high - tolerance) and (current_price > int(upbit.get_avg_buy_price(COI))) :
                    print("고점대비 가중치 반영 톨러런스 이상으로 가격 하락하여 청산")
                    sell_crypto_currency(COI)
                    sell_balance = upbit.get_balance("KRW")
                    profit = profit + sell_balance - buy_balance
                    print("매입가: ", buy_balance, "청산가: ", sell_balance, "수익: ", sell_balance - buy_balance)
                    position = False
            else:
                if current_price <= (itv_high - 3) and (current_price > int(upbit.get_avg_buy_price(COI))):
                    print("고점대비 톨러런스 3 이상으로 가격 하락하여 청산")
                    sell_crypto_currency(COI)
                    sell_balance = upbit.get_balance("KRW")
                    profit = profit + sell_balance - buy_balance
                    print("매입가: ", buy_balance, "청산가: ", sell_balance, "수익: ", sell_balance - buy_balance)
                    position = False

        print("Position:", position, ", 여유현금 잔액: ", upbit.get_balance("KRW"), ", 여유코인 잔액: ", upbit.get_balance(COI.split('-')[1]), "누적이익: ", profit)

        # 현재가가 타깃가를 초과하고, 5기간 이동평균을 초과하는 경우 경우 즉시 limit 매수
        if (current_price >= target_price) and (position == False) and (current_price > ma5) :
            position = True
            itv_high = target_price
            buy_balance = upbit.get_balance("KRW")
            print("현재가가 타깃가를 초월하여 매수실행")
            print("매입 총액: ", buy_balance)
            bid_price = buy_crypto_currency(COI)

        # overpace breakthrough/breakdown 여부 파악
        if upbit.get_order(COI):

            # limit 매수주문을 했으나 시세 상승이 너무 빨라 체결되지 않은 경우 해당 limit 주문을 취소하고 즉시 시장가로 추격매수
            for i in upbit.get_order(COI):
                if (i['side'] == 'bid') and (i['state'] == 'wait') and (current_price >= float(i['price']) + 2):
                    upbit.cancel_order(i['uuid'])
                    overpace_breakout = True

            if overpace_breakout == True :
                print("급격한 가격상승으로 시장가 매수")
                upbit.buy_market_order(COI, upbit.get_balance("KRW"))
                overpace_breakout = False

            # limit 매도주문을 했으나 시세 하락이 너무 빨라 체결되지 않은 경우 해당 limit 주문을 취소하고 즉시 시장가로 추격매도
            for i in upbit.get_order(COI):
                if (i['side'] == "ask") and (i['state'] == "wait") and (current_price <= float(i['price']) - 2):
                    upbit.cancel_order(i['uuid'])
                    overpace_breakdown = True

            if overpace_breakdown == True :
                print("급격한 가력하락으로 시장가 매도")
                upbit.sell_market_order(COI, upbit.get_balance(COI.split('-')[1]))
                overpace_breakdown = False

    except:
        print("에러발생")

    time.sleep(0.5)
