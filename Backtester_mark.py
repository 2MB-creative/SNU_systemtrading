import pyupbit
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt

# 주문 가능 key : 172.30.1.15 만 가능
con_key = ""
sec_key = ""

upbit = pyupbit.Upbit(con_key, sec_key)

def get_ror(ticker, k, itv, cnt):
    df = get_historic_data(ticker, itv, cnt)
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
    df.to_excel("VB_backtest_k-"+str(k)+".xlsx")

    return rc, df['dd'].max(), benchmark, df['hodl_dd'].max()

def get_max_hpr(ticker, itv, period):
    max_ror_cum = 0
    k_max = 0
    MDD_max =0
    rows = []
    for k in np.arange(0, 1, 0.01):
        ror_cum, dd, bm, hodl_dd = get_ror(ticker, k, itv, period)
        rows.append([dd, ror_cum])
        print("%s, k값: %f, 수익률: %f MDD: %f" % (ticker, k, ror_cum, dd))
        if ror_cum > max_ror_cum:
            max_ror_cum = ror_cum
            k_max = k
            MDD_max = dd
        time.sleep(0.01)
    df = pd.DataFrame(rows, columns = ['MDD', 'ROR'], index = np.arange(0,1,0.01))
    df['Benchmark_MDD']=hodl_dd
    df['Benchmark']=bm
    df.to_excel(str(ticker)+" "+str(period)+" x " +str(interval)+"_ROR-MDD_overview.xlsx")
    print(period, "기간 대상 %s, 최고수익률: %f 최적 k값: %f MDD: %f, HODL시: %f, HODL시 MDD: %f" % (ticker, max_ror_cum, k_max, MDD_max, bm, hodl_dd))
    plt.plot(df['MDD'], df['ROR'], 'b', label='MDD vs ROR')
    plt.grid(True)
    plt.ylabel('RoR')
    plt.xlabel('MDD')
    plt.show()
    return max_ror_cum, k_max, MDD_max

def get_historic_data(ticker, itv, cnt):
    date = None
    dfs = []
    for i in range(int(cnt/200)):
        df = pyupbit.get_ohlcv(ticker=ticker, interval=itv, to=date)
        dfs.append(df)

        date = df.index[0]
        time.sleep(0.1)

    dfs.append(pyupbit.get_ohlcv(ticker=ticker, interval=itv, cnt=(cnt%200), to = date))
    df = pd.concat(dfs).sort_index()
    return df

COI = "KRW-XRP"
interval = "minute60"
period = 4*6*7

max_hpr, k, max_dd = get_max_hpr(COI, interval, period)
