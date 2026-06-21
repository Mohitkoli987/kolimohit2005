
# ========== SIGNAL GENERATION — v7 (FULL INDICATOR SUITE) ==========

import random
from datetime import datetime


def _ema(prices, period):
    if len(prices) < period: return None
    k = 2.0 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]: val = p * k + val * (1 - k)
    return val

def _sma(prices, period):
    if len(prices) < period: return None
    return sum(prices[-period:]) / period

def _rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains) / period; al = sum(losses) / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
    if al == 0: return 100.0
    return 100 - (100 / (1 + ag / al))

def _macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal: return None, None, None
    ef = _ema(closes, fast); es = _ema(closes, slow)
    if ef is None or es is None: return None, None, None
    ml = ef - es
    series = []
    for i in range(slow - 1, len(closes)):
        ef2 = _ema(closes[:i+1], fast); es2 = _ema(closes[:i+1], slow)
        if ef2 and es2: series.append(ef2 - es2)
    if len(series) < signal: return ml, None, None
    sl_ = _ema(series, signal)
    return ml, sl_, (ml - sl_) if sl_ else None

def _bollinger(closes, period=20, std_dev=2.0):
    if len(closes) < period: return None, None, None
    recent = closes[-period:]; mid = sum(recent) / period
    std = (sum((x - mid) ** 2 for x in recent) / period) ** 0.5
    return mid + std_dev * std, mid, mid - std_dev * std

def _atr(candles, period=14):
    if len(candles) < period + 1: return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]['high']; l = candles[i]['low']; pc = candles[i-1]['close']
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    if len(trs) < period: return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]: atr = (atr * (period - 1) + tr) / period
    return atr

def _candle_strength(candles, lookback=5):
    if len(candles) < lookback: return 0
    recent = candles[-lookback:]
    bull = sum(1 for c in recent if c['close'] > c['open'])
    bear = sum(1 for c in recent if c['close'] < c['open'])
    last = candles[-1]; rng = last['high'] - last['low']
    body = abs(last['close'] - last['open'])
    bp = (body / rng) if rng > 0 else 0
    if bull >= 3 and bp > 0.5 and last['close'] > last['open']: return 1
    if bear >= 3 and bp > 0.5 and last['close'] < last['open']: return -1
    return 0

def _wma(prices, period):
    if len(prices) < period: return None
    w = list(range(1, period + 1))
    return sum(wi * p for wi, p in zip(w, prices[-period:])) / sum(w)

def _hma(prices, period=9):
    half = max(period // 2, 1); sq = max(int(period ** 0.5), 1)
    if len(prices) < period: return None
    raw = []
    for i in range(max(period, half), len(prices) + 1):
        wh = _wma(prices[:i], half); wf = _wma(prices[:i], period)
        if wh and wf: raw.append(2 * wh - wf)
    return _wma(raw, sq) if len(raw) >= sq else None

def _ultimate_oscillator(candles, p1=7, p2=14, p3=28):
    if len(candles) < p3 + 1: return None
    def _avg(sl):
        bps, trs = [], []
        for i in range(1, len(sl)):
            pc = sl[i-1]['close']; h = sl[i]['high']; l = sl[i]['low']; c = sl[i]['close']
            bps.append(c - min(l, pc)); trs.append(max(h, pc) - min(l, pc))
        return sum(bps)/sum(trs) if sum(trs) else 0
    return 100 * (4*_avg(candles[-(p1+1):]) + 2*_avg(candles[-(p2+1):]) + _avg(candles[-(p3+1):])) / 7

def _adx(candles, period=14):
    if len(candles) < period * 2 + 1: return None, None, None
    trs, pdms, mdms = [], [], []
    for i in range(1, len(candles)):
        h=candles[i]['high']; l=candles[i]['low']; ph=candles[i-1]['high']
        pl=candles[i-1]['low']; pc=candles[i-1]['close']
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        pdms.append(max(h-ph, 0) if (h-ph) > (pl-l) else 0)
        mdms.append(max(pl-l, 0) if (pl-l) > (h-ph) else 0)
    def _sm(v, p):
        s = sum(v[:p]); r = [s]
        for x in v[p:]: s = s - s/p + x; r.append(s)
        return r
    st=_sm(trs,period); sp=_sm(pdms,period); sm=_sm(mdms,period)
    if not st or st[-1]==0: return None, None, None
    pdi=100*sp[-1]/st[-1]; mdi=100*sm[-1]/st[-1]
    dx = [100*abs(100*p/t - 100*m/t)/(100*p/t + 100*m/t)
          for p,m,t in zip(sp,sm,st) if t and (100*p/t + 100*m/t)]
    return (sum(dx[-period:])/period if len(dx)>=period else None), pdi, mdi

def _bull_bear_power(candles, period=13):
    if len(candles) < period: return None, None
    ev = _ema([c['close'] for c in candles], period)
    if ev is None: return None, None
    return candles[-1]['high'] - ev, candles[-1]['low'] - ev

def _momentum(closes, period=20):
    if len(closes) < period + 1: return None
    return closes[-1] - closes[-(period+1)]

def _ppo(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal: return None, None, None
    ef=_ema(closes,fast); es=_ema(closes,slow)
    if not ef or not es or es==0: return None, None, None
    ppo = ((ef-es)/es)*100
    series = [((ef2-es2)/es2)*100 for i in range(slow-1, len(closes))
              for ef2,es2 in [(_ema(closes[:i+1],fast), _ema(closes[:i+1],slow))]
              if ef2 and es2 and es2!=0]
    if len(series) < signal: return ppo, None, None
    sig = _ema(series, signal)
    return ppo, sig, (ppo-sig) if sig else None

def _stoch_rsi(closes, period=14, sk=3, sd=3):
    if len(closes) < period*2+sk+sd: return None, None
    rs = [_rsi(closes[:i], period) for i in range(period, len(closes)+1)]
    if len(rs) < period: return None, None
    st = []
    for i in range(period-1, len(rs)):
        w=rs[i-period+1:i+1]; mn=min(w); mx=max(w)
        st.append(((rs[i]-mn)/(mx-mn)*100) if (mx-mn) else 50.0)
    if len(st) < sk+sd: return None, None
    ks = [sum(st[i-sk+1:i+1])/sk for i in range(sk-1, len(st))]
    return (ks[-1], sum(ks[-sd:])/sd) if len(ks)>=sd else (None, None)

def _ichimoku(candles, t=9, k=26, sb=52):
    if len(candles) < sb: return None
    def _m(sl): return (max(c['high'] for c in sl)+min(c['low'] for c in sl))/2
    tn=_m(candles[-t:]); kj=_m(candles[-k:])
    return {'tenkan':tn,'kijun':kj,'senkou_a':(tn+kj)/2,'senkou_b':_m(candles[-sb:]),
            'chikou':candles[-1]['close'],
            'price_ago':candles[-k]['close'] if len(candles)>=k else None}

def _cci(candles, period=20):
    if len(candles) < period: return None
    rc=candles[-period:]; tp=[(c['high']+c['low']+c['close'])/3 for c in rc]
    sma=sum(tp)/period; md=sum(abs(t-sma) for t in tp)/period
    return 0 if md==0 else (tp[-1]-sma)/(0.015*md)

def _awesome_oscillator(candles, fast=5, slow=34):
    if len(candles) < slow: return None
    mids=[(c['high']+c['low'])/2 for c in candles]
    sf=_sma(mids,fast); ss=_sma(mids,slow)
    return (sf-ss) if (sf and ss) else None

def _williams_r(candles, period=14):
    if len(candles) < period: return None
    rc=candles[-period:]; hh=max(c['high'] for c in rc); ll=min(c['low'] for c in rc)
    close=candles[-1]['close']
    return -50.0 if hh==ll else ((hh-close)/(hh-ll))*-100

def _ma_suite_score(closes, label=""):
    sb, ss, det = 0, 0, []
    price = closes[-1]
    for p in [5, 10, 20, 50, 100, 200]:
        for fn, nm in [(_sma, 'SMA'), (_ema, 'EMA')]:
            v = fn(closes, p)
            if v:
                if price > v: sb+=1; det.append(f"[{label}] Price>{nm}{p} → BUY +1")
                else:         ss+=1; det.append(f"[{label}] Price<{nm}{p} → SELL +1")
    return sb, ss, det


def _score_timeframe(candles, label=""):
    if len(candles) < 30:
        return {'bias':'NEUTRAL','score':0,'details':[],'score_buy':0,'score_sell':0,'net':0,
                'rsi':50,'ema9':None,'ema21':None,'ema50':None,'adx':None,'cci':None,
                'ao':None,'williams_r':None,'uo':None,'ppo':None,'stoch_k':None,'hma':None}

    closes=[c['close'] for c in candles]; sb=0; ss=0; det=[]

    e9=_ema(closes,9); e21=_ema(closes,21)
    if e9 and e21:
        if e9>e21: sb+=2; det.append(f"[{label}] EMA9>EMA21 → BUY +2")
        else:      ss+=2; det.append(f"[{label}] EMA9<EMA21 → SELL +2")

    e50=_ema(closes,50) if len(closes)>=50 else None
    if e21 and e50:
        if e21>e50: sb+=1; det.append(f"[{label}] EMA21>EMA50 → BUY +1")
        else:       ss+=1; det.append(f"[{label}] EMA21<EMA50 → SELL +1")

    rsi=_rsi(closes,14)
    if   rsi<30: sb+=3; det.append(f"[{label}] RSI={rsi:.1f} OVERSOLD → BUY +3")
    elif rsi>70: ss+=3; det.append(f"[{label}] RSI={rsi:.1f} OVERBOUGHT → SELL +3")
    elif rsi<45: sb+=1; det.append(f"[{label}] RSI={rsi:.1f} <45 → BUY +1")
    elif rsi>55: ss+=1; det.append(f"[{label}] RSI={rsi:.1f} >55 → SELL +1")

    ml,sl_,hist=_macd(closes)
    if hist is not None and ml and sl_:
        thr=abs(closes[-1])*0.00005
        if   abs(hist)>thr and hist>0 and ml>sl_: sb+=3; det.append(f"[{label}] MACD strong BUY → +3")
        elif abs(hist)>thr and hist<0 and ml<sl_: ss+=3; det.append(f"[{label}] MACD strong SELL → +3")
        elif ml>sl_: sb+=1; det.append(f"[{label}] MACD>signal → BUY +1")
        elif ml<sl_: ss+=1; det.append(f"[{label}] MACD<signal → SELL +1")

    bbu,_,bbl=_bollinger(closes)
    if bbu and bbl:
        rng=bbu-bbl
        if rng>0:
            pos=(closes[-1]-bbl)/rng
            if   pos<0.15: sb+=2; det.append(f"[{label}] BB lower extreme → BUY +2")
            elif pos>0.85: ss+=2; det.append(f"[{label}] BB upper extreme → SELL +2")

    cs=_candle_strength(candles,5)
    if cs==1:  sb+=1; det.append(f"[{label}] Bullish candles → BUY +1")
    elif cs==-1:ss+=1; det.append(f"[{label}] Bearish candles → SELL +1")

    hma=_hma(closes,9)
    if hma:
        if closes[-1]>hma: sb+=1; det.append(f"[{label}] Price>HMA9 → BUY +1")
        else:               ss+=1; det.append(f"[{label}] Price<HMA9 → SELL +1")

    uo=_ultimate_oscillator(candles,7,14,28)
    if uo:
        if   uo<30: sb+=2; det.append(f"[{label}] UO={uo:.1f} OVERSOLD → BUY +2")
        elif uo>70: ss+=2; det.append(f"[{label}] UO={uo:.1f} OVERBOUGHT → SELL +2")
        elif uo>50: sb+=1; det.append(f"[{label}] UO={uo:.1f} >50 → BUY +1")
        else:       ss+=1; det.append(f"[{label}] UO={uo:.1f} <50 → SELL +1")

    adx,pdi,mdi=_adx(candles,14)
    if adx and pdi and mdi and adx>25:
        if pdi>mdi: sb+=2; det.append(f"[{label}] ADX={adx:.1f} DI+ → BUY +2")
        else:       ss+=2; det.append(f"[{label}] ADX={adx:.1f} DI- → SELL +2")

    bp,brp=_bull_bear_power(candles,13)
    if bp is not None and brp is not None:
        if   bp>0 and brp>0: sb+=2; det.append(f"[{label}] Both powers>0 → BUY +2")
        elif bp<0 and brp<0: ss+=2; det.append(f"[{label}] Both powers<0 → SELL +2")
        elif bp>0:            sb+=1; det.append(f"[{label}] Bull power>0 → BUY +1")
        elif brp<0:           ss+=1; det.append(f"[{label}] Bear power<0 → SELL +1")

    mom=_momentum(closes,20)
    if mom is not None:
        if mom>0: sb+=1; det.append(f"[{label}] Momentum+ → BUY +1")
        else:     ss+=1; det.append(f"[{label}] Momentum- → SELL +1")

    ppo,psig,phist=_ppo(closes,12,26,9)
    if ppo is not None:
        if ppo>0:   sb+=1; det.append(f"[{label}] PPO>0 → BUY +1")
        else:       ss+=1; det.append(f"[{label}] PPO<0 → SELL +1")
        if phist:
            if phist>0: sb+=1; det.append(f"[{label}] PPO hist+ → BUY +1")
            else:       ss+=1; det.append(f"[{label}] PPO hist- → SELL +1")

    sk_v,sd_v=_stoch_rsi(closes,14)
    if sk_v is not None:
        if   sk_v<20: sb+=2; det.append(f"[{label}] StochRSI OVERSOLD → BUY +2")
        elif sk_v>80: ss+=2; det.append(f"[{label}] StochRSI OVERBOUGHT → SELL +2")
        elif sd_v and sk_v>sd_v: sb+=1; det.append(f"[{label}] StochRSI K>D → BUY +1")
        elif sd_v and sk_v<sd_v: ss+=1; det.append(f"[{label}] StochRSI K<D → SELL +1")

    ichi=_ichimoku(candles,9,26,52)
    if ichi:
        price=closes[-1]; ct=max(ichi['senkou_a'],ichi['senkou_b']); cb=min(ichi['senkou_a'],ichi['senkou_b'])
        if   price>ct: sb+=2; det.append(f"[{label}] Ichimoku above cloud → BUY +2")
        elif price<cb: ss+=2; det.append(f"[{label}] Ichimoku below cloud → SELL +2")
        if ichi['tenkan']>ichi['kijun']: sb+=1; det.append(f"[{label}] Tenkan>Kijun → BUY +1")
        else:                             ss+=1; det.append(f"[{label}] Tenkan<Kijun → SELL +1")
        if ichi['price_ago']:
            if ichi['chikou']>ichi['price_ago']: sb+=1; det.append(f"[{label}] Chikou above → BUY +1")
            else:                                 ss+=1; det.append(f"[{label}] Chikou below → SELL +1")

    cci=_cci(candles,20)
    if cci is not None:
        if   cci<-100: sb+=2; det.append(f"[{label}] CCI OVERSOLD → BUY +2")
        elif cci>100:  ss+=2; det.append(f"[{label}] CCI OVERBOUGHT → SELL +2")
        elif cci>0:    sb+=1; det.append(f"[{label}] CCI>0 → BUY +1")
        else:          ss+=1; det.append(f"[{label}] CCI<0 → SELL +1")

    ao=_awesome_oscillator(candles,5,34)
    if ao is not None:
        if ao>0: sb+=1; det.append(f"[{label}] AO>0 → BUY +1")
        else:    ss+=1; det.append(f"[{label}] AO<0 → SELL +1")

    wr=_williams_r(candles,14)
    if wr is not None:
        if   wr<-80: sb+=2; det.append(f"[{label}] W%R OVERSOLD → BUY +2")
        elif wr>-20: ss+=2; det.append(f"[{label}] W%R OVERBOUGHT → SELL +2")
        elif wr<-50: ss+=1; det.append(f"[{label}] W%R bearish → SELL +1")
        else:        sb+=1; det.append(f"[{label}] W%R bullish → BUY +1")

    mb,ms,md=_ma_suite_score(closes,label)
    sb+=mb; ss+=ms; det+=md

    net=sb-ss
    if   net>0: bias,score='BUY',sb
    elif net<0: bias,score='SELL',ss
    else:       bias,score='NEUTRAL',0

    return {'bias':bias,'score':score,'score_buy':sb,'score_sell':ss,'net':net,
            'rsi':rsi,'ema9':e9,'ema21':e21,'ema50':e50,'details':det,
            'adx':adx,'cci':cci,'ao':ao,'williams_r':wr,'uo':uo,'ppo':ppo,'stoch_k':sk_v,'hma':hma}


def _fetch_candles(symbol, resolution, num_candles):
    try:
        sec={'1m':60,'3m':180,'5m':300,'15m':900,'30m':1800,'1h':3600,'4h':14400,'1d':86400}.get(resolution,300)
        end=int(_time.time()); start=end-(num_candles*sec)
        resp=make_api_request('GET',f'/history/candles?resolution={resolution}&symbol={symbol}&start={start}&end={end}')
        if not resp or not resp.get('result'): print(f"⚠️ No candles {symbol}@{resolution}"); return []
        parsed=[{'open':float(c.get('open',0)),'high':float(c.get('high',0)),
                 'low':float(c.get('low',0)),'close':float(c.get('close',0)),'time':c.get('time',0)}
                for c in resp['result'] if c]
        parsed.sort(key=lambda x:x['time'])
        print(f"📊 {symbol} @ {resolution}: {len(parsed)} candles fetched")
        return parsed
    except Exception as e:
        print(f"❌ Error {resolution}: {e}"); return []

def _is_market_tradeable(candles_15m):
    if len(candles_15m) < 15: return True
    atr_val=_atr(candles_15m,14); price=candles_15m[-1]['close']
    if not atr_val or price<=0: return True
    pct=(atr_val/price)*100
    if pct<0.02: print(f"⚠️ Too flat ATR={pct:.4f}%"); return False
    print(f"✅ ATR OK: {pct:.4f}%"); return True


def generate_smart_signal(reason="trade_decision"):
    """
    SIGNAL ENGINE v7

    RULES:
    ┌─────────────────────────────────────────────────┐
    │  4H = MASTER DIRECTION                          │
    │  15M must agree with 4H + net >= 4              │
    │  1H = confidence only (not a blocker)           │
    │                                                 │
    │  4H SELL + 15M SELL + net>=4  →  SELL ✅        │
    │  4H BUY  + 15M BUY  + net>=4  →  BUY  ✅        │
    │  4H SELL + 15M BUY            →  WAIT ⏳        │
    │  4H BUY  + 15M SELL           →  WAIT ⏳        │
    │  4H NEUTRAL: need 1H+15M agree + net>=5         │
    └─────────────────────────────────────────────────┘
    """

    symbol = BOT_STATE.get('symbol', 'ETHUSD')
    print(f"\n{'='*60}")
    print(f"🧠 SIGNAL ENGINE v7 — {symbol} — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    candles_4h  = _fetch_candles(symbol, '4h',  120)
    candles_1h  = _fetch_candles(symbol, '1h',  120)
    candles_15m = _fetch_candles(symbol, '15m', 120)

    if len(candles_4h) < 20:  candles_4h = None
    if len(candles_1h) < 20 or len(candles_15m) < 20:
        d = random.choice(['BUY','SELL'])
        return _make_signal(d, 50, 'RANDOM_FALLBACK', 0, reason, {}, {}, {}, candles_15m or [])

    if not _is_market_tradeable(candles_15m):
        return _make_wait_signal(reason, "Market too flat")

    r4h  = _score_timeframe(candles_4h,  '4H') if candles_4h else None
    r1h  = _score_timeframe(candles_1h,  '1H')
    r15m = _score_timeframe(candles_15m, '15M')

    b4h  = r4h['bias']  if r4h  else 'NEUTRAL'
    b1h  = r1h['bias']
    b15m = r15m['bias']

    print(f"\n📊 SCORES:")
    if r4h:
        print(f"   4H  → {b4h:7s} | BUY={r4h['score_buy']:2d} SELL={r4h['score_sell']:2d} Net={r4h['net']:+3d}  ← MASTER")
    print(f"   1H  → {b1h:7s} | BUY={r1h['score_buy']:2d} SELL={r1h['score_sell']:2d} Net={r1h['net']:+3d}  (confidence only)")
    print(f"   15M → {b15m:7s} | BUY={r15m['score_buy']:2d} SELL={r15m['score_sell']:2d} Net={r15m['net']:+3d}  ← ENTRY")

    MIN_15M_NET = 4

    if b4h in ('BUY', 'SELL'):
        master = b4h

        if b15m != master:
            print(f"⏳ 15M={b15m} not aligned with 4H={master} — wait for 15M entry")
            return _make_wait_signal(reason, f"Waiting for 15M to align with 4H {master}")

        if abs(r15m['net']) < MIN_15M_NET:
            print(f"⏳ 15M net={r15m['net']} too weak (need >={MIN_15M_NET})")
            return _make_wait_signal(reason, f"15M weak: net={r15m['net']} need >={MIN_15M_NET}")

        direction = master
        print(f"\n✅ 4H {master} + 15M {b15m} aligned — SIGNAL: {direction}")

    else:
        print(f"⚖️ 4H NEUTRAL — checking 1H+15M")
        if b1h == 'NEUTRAL' or b15m == 'NEUTRAL' or b1h != b15m:
            return _make_wait_signal(reason, f"4H neutral, 1H={b1h} 15M={b15m} not aligned")
        if abs(r1h['net']) < 5 or abs(r15m['net']) < 5:
            return _make_wait_signal(reason, f"4H neutral, signals too weak 1H={r1h['net']} 15M={r15m['net']}")
        direction = b15m
        print(f"\n✅ 4H neutral but 1H+15M both {direction} — SIGNAL: {direction}")

    MAX_SCORE = 75.0
    w_4h = 0.35 if r4h else 0.0
    w_1h = 0.30
    w_15 = 0.35

    score_4h = r4h['score'] if r4h else 0
    conf_raw = (score_4h * w_4h + r1h['score'] * w_1h + r15m['score'] * w_15) / MAX_SCORE

    if b1h == direction:
        conf_raw = min(conf_raw * 1.15, 1.0)
        print(f"   ✅ 1H also agrees ({b1h}) — confidence boosted")
    else:
        conf_raw = conf_raw * 0.90
        print(f"   ⚠️ 1H disagrees ({b1h}) — slight confidence reduction")

    confidence = int(min(50 + conf_raw * 50, 95))

    net15 = abs(r15m['net'])
    if   net15 >= 15: layer = 'STRONG_BUY'   if direction=='BUY' else 'STRONG_SELL'
    elif net15 >= 8:  layer = 'MODERATE_BUY' if direction=='BUY' else 'MODERATE_SELL'
    else:             layer = 'WEAK_BUY'      if direction=='BUY' else 'WEAK_SELL'

    print(f"   Confidence={confidence}%  Layer={layer}")
    # Reverse final signal
    if direction == "BUY":
        direction = "SELL"
    elif direction == "SELL":
        direction = "BUY"

    return _make_signal(direction, confidence, layer,
                        r15m['net'], reason, r4h or {}, r1h, r15m, candles_15m)


def _make_signal(direction, confidence, layer, net_score, reason,
                 r4h, r1h, r15m, candles_15m):
    price=candles_15m[-1]['close'] if candles_15m else 0
    atr_val=_atr(candles_15m,14) if candles_15m else None
    if atr_val and price:
        ref_sl=round(price-(1.5*atr_val),4) if direction=='BUY' else round(price+(1.5*atr_val),4)
        ref_tp=round(price+(3.0*atr_val),4) if direction=='BUY' else round(price-(3.0*atr_val),4)
    else: ref_sl=ref_tp=None
    print(f"   📍 Entry={price} SL={ref_sl} TP={ref_tp}")
    return {
        'signal':direction,'timestamp':datetime.now().isoformat(),
        'confidence':confidence,'layer':layer,'score':net_score,
        'score_buy':r15m.get('score_buy',0),'score_sell':r15m.get('score_sell',0),
        'source':'smart_signal_v7','entry_price':price,'ref_sl':ref_sl,'ref_tp':ref_tp,
        'reason':f"4H={r4h.get('bias','?')} 1H={r1h.get('bias','?')} 15M={r15m.get('bias','?')} Net={net_score}",
        'decision_ready':True,'decision_confidence':confidence/100,'wait':False,
        'position_analysis':{'has_position':False},
        'backtest_results':{
            'ema9':r15m.get('ema9'),'ema21':r15m.get('ema21'),'ema50':r15m.get('ema50'),
            'rsi':r15m.get('rsi'),'adx':r15m.get('adx'),'cci':r15m.get('cci'),
            'ao':r15m.get('ao'),'williams_r':r15m.get('williams_r'),'uo':r15m.get('uo'),
            'ppo':r15m.get('ppo'),'stoch_k':r15m.get('stoch_k'),'hma':r15m.get('hma'),
            'price':price,'ref_sl':ref_sl,'ref_tp':ref_tp,'factors':r15m.get('details',[]),
            '4h_bias':r4h.get('bias','?'),'1h_bias':r1h.get('bias','?'),'15m_bias':r15m.get('bias','?'),
        },
        'last_trade_result':reason,
    }

def _make_wait_signal(reason, why):
    print(f"⏸️ WAIT: {why}")
    return {
        'signal':'WAIT','timestamp':datetime.now().isoformat(),
        'confidence':0,'layer':'WAIT','score':0,'score_buy':0,'score_sell':0,
        'source':'smart_signal_v7','reason':why,'entry_price':None,'ref_sl':None,'ref_tp':None,
        'decision_ready':False,'decision_confidence':0,'wait':True,
        'position_analysis':{'has_position':False},'backtest_results':{},'last_trade_result':reason,
    }
