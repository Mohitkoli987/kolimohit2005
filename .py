
def _ema(prices, period):
    """Exponential Moving Average"""
    if len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val


def _sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _rsi(closes, period=14):
    """Wilder RSI"""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
    if al == 0:
        return 100.0
    return 100 - (100 / (1 + ag / al))


def _macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram"""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow

    macd_series = []
    for i in range(slow - 1, len(closes)):
        ef = _ema(closes[:i + 1], fast)
        es = _ema(closes[:i + 1], slow)
        if ef and es:
            macd_series.append(ef - es)

    if len(macd_series) < signal:
        return macd_line, None, None

    signal_line = _ema(macd_series, signal)
    histogram = macd_line - signal_line if signal_line else None
    return macd_line, signal_line, histogram


def _bollinger(closes, period=20, std_dev=2.0):
    """Bollinger Bands: upper, middle (SMA), lower"""
    if len(closes) < period:
        return None, None, None
    recent = closes[-period:]
    mid = sum(recent) / period
    variance = sum((x - mid) ** 2 for x in recent) / period
    std = variance ** 0.5
    return mid + std_dev * std, mid, mid - std_dev * std


def _atr(candles, period=14):
    """Average True Range"""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low  = candles[i]['low']
        prev_close = candles[i - 1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _candle_strength(candles, lookback=5):
    """
    Measures momentum strength from last N candles.
    lookback=5 (upgraded from 3 — better momentum detection)
    Returns: +1 (bullish), -1 (bearish), 0 (neutral)
    """
    if len(candles) < lookback:
        return 0
    recent = candles[-lookback:]
    bull = sum(1 for c in recent if c['close'] > c['open'])
    bear = sum(1 for c in recent if c['close'] < c['open'])
    last = candles[-1]
    rng  = last['high'] - last['low']
    body = abs(last['close'] - last['open'])
    body_pct = (body / rng) if rng > 0 else 0

    if bull >= 3 and body_pct > 0.5 and last['close'] > last['open']:
        return 1
    if bear >= 3 and body_pct > 0.5 and last['close'] < last['open']:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────
#  NEW INDICATORS
# ─────────────────────────────────────────────────────────────

def _wma(prices, period):
    """Weighted Moving Average"""
    if len(prices) < period:
        return None
    weights = list(range(1, period + 1))
    subset  = prices[-period:]
    total   = sum(w * p for w, p in zip(weights, subset))
    return total / sum(weights)


def _hma(prices, period=9):
    """
    Hull Moving Average — fast & smooth MA
    HMA(n) = WMA(2*WMA(n/2) − WMA(n), sqrt(n))
    """
    half = max(period // 2, 1)
    sqrt_p = max(int(period ** 0.5), 1)

    if len(prices) < period:
        return None

    wma_half = _wma(prices, half)
    wma_full = _wma(prices, period)
    if wma_half is None or wma_full is None:
        return None

    # Build series for final WMA
    raw_series = []
    start = max(period, half)
    for i in range(start, len(prices) + 1):
        wh = _wma(prices[:i], half)
        wf = _wma(prices[:i], period)
        if wh is not None and wf is not None:
            raw_series.append(2 * wh - wf)

    if len(raw_series) < sqrt_p:
        return None
    return _wma(raw_series, sqrt_p)


def _ultimate_oscillator(candles, p1=7, p2=14, p3=28):
    """
    Ultimate Oscillator (Larry Williams)
    UO = 100 * [(4*Avg7 + 2*Avg14 + Avg28) / 7]
    """
    if len(candles) < p3 + 1:
        return None

    def _bp_tr(candles_slice):
        bps, trs = [], []
        for i in range(1, len(candles_slice)):
            pc    = candles_slice[i - 1]['close']
            high  = candles_slice[i]['high']
            low   = candles_slice[i]['low']
            close = candles_slice[i]['close']
            bp    = close - min(low, pc)
            tr    = max(high, pc) - min(low, pc)
            bps.append(bp)
            trs.append(tr)
        return bps, trs

    def _avg(candles_slice):
        bps, trs = _bp_tr(candles_slice)
        if not trs or sum(trs) == 0:
            return 0
        return sum(bps) / sum(trs)

    avg1 = _avg(candles[-(p1 + 1):])
    avg2 = _avg(candles[-(p2 + 1):])
    avg3 = _avg(candles[-(p3 + 1):])

    uo = 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
    return uo


def _adx(candles, period=14):
    """
    ADX + DI+ + DI-
    Returns: (adx, plus_di, minus_di) or (None, None, None)
    """
    if len(candles) < period * 2 + 1:
        return None, None, None

    trs, plus_dms, minus_dms = [], [], []
    for i in range(1, len(candles)):
        high  = candles[i]['high']
        low   = candles[i]['low']
        p_high = candles[i - 1]['high']
        p_low  = candles[i - 1]['low']
        p_close = candles[i - 1]['close']

        tr = max(high - low, abs(high - p_close), abs(low - p_close))
        plus_dm  = max(high - p_high, 0) if (high - p_high) > (p_low - low) else 0
        minus_dm = max(p_low - low, 0)   if (p_low - low) > (high - p_high) else 0

        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)

    def _smooth(values, p):
        s = sum(values[:p])
        result = [s]
        for v in values[p:]:
            s = s - s / p + v
            result.append(s)
        return result

    s_tr   = _smooth(trs, period)
    s_pdm  = _smooth(plus_dms, period)
    s_mdm  = _smooth(minus_dms, period)

    if not s_tr or s_tr[-1] == 0:
        return None, None, None

    plus_di  = 100 * s_pdm[-1] / s_tr[-1]
    minus_di = 100 * s_mdm[-1] / s_tr[-1]

    dx_series = []
    for p, m, t in zip(s_pdm, s_mdm, s_tr):
        if t == 0:
            continue
        pdi = 100 * p / t
        mdi = 100 * m / t
        denom = pdi + mdi
        if denom == 0:
            continue
        dx_series.append(100 * abs(pdi - mdi) / denom)

    if len(dx_series) < period:
        return None, plus_di, minus_di

    adx = sum(dx_series[-period:]) / period
    return adx, plus_di, minus_di


def _bull_bear_power(candles, period=13):
    """
    Elder Ray Index — Bull Power & Bear Power
    Bull Power = High - EMA(period)
    Bear Power = Low  - EMA(period)
    Returns: (bull_power, bear_power) — latest values
    """
    if len(candles) < period:
        return None, None
    closes = [c['close'] for c in candles]
    ema_val = _ema(closes, period)
    if ema_val is None:
        return None, None
    last = candles[-1]
    bull_power = last['high'] - ema_val
    bear_power = last['low']  - ema_val
    return bull_power, bear_power


def _momentum(closes, period=20):
    """
    Price Momentum = Close[now] - Close[period ago]
    Positive → bullish momentum, Negative → bearish
    """
    if len(closes) < period + 1:
        return None
    return closes[-1] - closes[-(period + 1)]


def _ppo(closes, fast=12, slow=26, signal=9):
    """
    Percentage Price Oscillator
    PPO = ((EMA_fast - EMA_slow) / EMA_slow) * 100
    Signal = EMA(PPO, signal_period)
    Histogram = PPO - Signal
    Returns: (ppo_line, signal_line, histogram)
    """
    if len(closes) < slow + signal:
        return None, None, None

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if ema_fast is None or ema_slow is None or ema_slow == 0:
        return None, None, None

    ppo_line = ((ema_fast - ema_slow) / ema_slow) * 100

    # Build PPO series for signal line
    ppo_series = []
    for i in range(slow - 1, len(closes)):
        ef = _ema(closes[:i + 1], fast)
        es = _ema(closes[:i + 1], slow)
        if ef is not None and es is not None and es != 0:
            ppo_series.append(((ef - es) / es) * 100)

    if len(ppo_series) < signal:
        return ppo_line, None, None

    sig_line  = _ema(ppo_series, signal)
    histogram = (ppo_line - sig_line) if sig_line is not None else None
    return ppo_line, sig_line, histogram


def _stoch_rsi(closes, period=14, smooth_k=3, smooth_d=3):
    """
    Stochastic RSI
    StochRSI = (RSI - min_RSI) / (max_RSI - min_RSI)
    K = SMA(StochRSI, smooth_k)
    D = SMA(K, smooth_d)
    Returns: (k_val, d_val) in 0..100, or (None, None)
    """
    if len(closes) < period * 2 + smooth_k + smooth_d:
        return None, None

    rsi_series = []
    for i in range(period, len(closes) + 1):
        rsi_series.append(_rsi(closes[:i], period))

    if len(rsi_series) < period:
        return None, None

    stoch_series = []
    for i in range(period - 1, len(rsi_series)):
        window   = rsi_series[i - period + 1: i + 1]
        min_rsi  = min(window)
        max_rsi  = max(window)
        denom    = max_rsi - min_rsi
        stoch    = ((rsi_series[i] - min_rsi) / denom * 100) if denom != 0 else 50.0
        stoch_series.append(stoch)

    if len(stoch_series) < smooth_k + smooth_d:
        return None, None

    k_series = []
    for i in range(smooth_k - 1, len(stoch_series)):
        k_series.append(sum(stoch_series[i - smooth_k + 1: i + 1]) / smooth_k)

    if len(k_series) < smooth_d:
        return None, None

    d_val = sum(k_series[-smooth_d:]) / smooth_d
    return k_series[-1], d_val


def _ichimoku(candles, tenkan=9, kijun=26, senkou_b_period=52):
    """
    Ichimoku Cloud
    Tenkan-sen  = (highest high + lowest low) / 2  over tenkan  periods
    Kijun-sen   = (highest high + lowest low) / 2  over kijun   periods
    Senkou A    = (Tenkan + Kijun) / 2
    Senkou B    = (highest high + lowest low) / 2  over senkou_b periods
    Chikou Span = close shifted back kijun periods
    Returns dict with all lines, or None if not enough data
    """
    if len(candles) < senkou_b_period:
        return None

    def _mid(candles_slice):
        highs = [c['high']  for c in candles_slice]
        lows  = [c['low']   for c in candles_slice]
        return (max(highs) + min(lows)) / 2

    tenkan_sen  = _mid(candles[-tenkan:])
    kijun_sen   = _mid(candles[-kijun:])
    senkou_a    = (tenkan_sen + kijun_sen) / 2
    senkou_b    = _mid(candles[-senkou_b_period:])
    chikou_span = candles[-1]['close']   # current close (compare vs price kijun bars ago)
    price_kijun_ago = candles[-kijun]['close'] if len(candles) >= kijun else None

    return {
        'tenkan':    tenkan_sen,
        'kijun':     kijun_sen,
        'senkou_a':  senkou_a,
        'senkou_b':  senkou_b,
        'chikou':    chikou_span,
        'price_ago': price_kijun_ago,
    }


def _cci(candles, period=20):
    """
    Commodity Channel Index
    CCI = (Typical Price - SMA(TP)) / (0.015 * Mean Deviation)
    """
    if len(candles) < period:
        return None
    recent = candles[-period:]
    tp_list = [(c['high'] + c['low'] + c['close']) / 3.0 for c in recent]
    tp_sma  = sum(tp_list) / period
    mean_dev = sum(abs(tp - tp_sma) for tp in tp_list) / period
    if mean_dev == 0:
        return 0
    return (tp_list[-1] - tp_sma) / (0.015 * mean_dev)


def _awesome_oscillator(candles, fast=5, slow=34):
    """
    Awesome Oscillator = SMA(Midprice, fast) - SMA(Midprice, slow)
    Midprice = (High + Low) / 2
    """
    if len(candles) < slow:
        return None
    mids = [(c['high'] + c['low']) / 2.0 for c in candles]
    sma_fast = _sma(mids, fast)
    sma_slow = _sma(mids, slow)
    if sma_fast is None or sma_slow is None:
        return None
    return sma_fast - sma_slow


def _williams_r(candles, period=14):
    """
    Williams %R
    %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    Range: -100 (oversold) to 0 (overbought)
    """
    if len(candles) < period:
        return None
    recent = candles[-period:]
    hh = max(c['high']  for c in recent)
    ll = min(c['low']   for c in recent)
    close = candles[-1]['close']
    if hh == ll:
        return -50.0
    return ((hh - close) / (hh - ll)) * -100


def _ma_suite_score(closes, label=""):
    """
    Score SMA and EMA of periods 5,10,20,50,100,200 vs current price.
    BUY  if price > MA
    SELL if price < MA
    Returns: (score_buy, score_sell, details_list)
    """
    periods = [5, 10, 20, 50, 100, 200]
    score_buy, score_sell = 0, 0
    details = []
    price = closes[-1]

    weights = {5: 1, 10: 1, 20: 1, 50: 2, 100: 2, 200: 2}

    for p in periods:
        w = weights[p]
        sma_val = _sma(closes, p)
        ema_val = _ema(closes, p)

        if sma_val is not None:
            if price > sma_val:
                score_buy += w
                details.append(f"[{label}] Price>SMA{p} → BUY +{w}")
            else:
                score_sell += w
                details.append(f"[{label}] Price<SMA{p} → SELL +{w}")

        if ema_val is not None:
            if price > ema_val:
                score_buy += w
                details.append(f"[{label}] Price>EMA{p} → BUY +{w}")
            else:
                score_sell += w
                details.append(f"[{label}] Price<EMA{p} → SELL +{w}")

    return score_buy, score_sell, details


# ──────────────────────────────────────────────
#  TIMEFRAME BIAS SCORER — v4 (ALL INDICATORS)
# ──────────────────────────────────────────────

def _score_timeframe(candles, label=""):
    """
    Score a single timeframe for directional bias.
    v4: Added HMA, UO, ADX, Bull/Bear Power, Momentum,
        PPO, StochRSI, Ichimoku, CCI, AO, Williams %R, MA Suite
    Returns dict with bias, score, details.
    """
    if len(candles) < 30:
        return {'bias': 'NEUTRAL', 'score': 0, 'details': ['Not enough candles']}

    closes = [c['close'] for c in candles]
    score_buy  = 0
    score_sell = 0
    details    = []

    # ── EMA 9 vs 21 (short trend)
    ema9  = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    if ema9 and ema21:
        if ema9 > ema21:
            score_buy += 2
            details.append(f"[{label}] EMA9>EMA21 → BUY +2")
        else:
            score_sell += 2
            details.append(f"[{label}] EMA9<EMA21 → SELL +2")

    # ── EMA 21 vs 50 (medium trend)
    ema50 = _ema(closes, 50) if len(closes) >= 50 else None
    if ema21 and ema50:
        if ema21 > ema50:
            score_buy += 1
            details.append(f"[{label}] EMA21>EMA50 → BUY +1")
        else:
            score_sell += 1
            details.append(f"[{label}] EMA21<EMA50 → SELL +1")

    # ── RSI filter
    rsi = _rsi(closes, 14)
    if rsi < 35:
        score_buy += 2
        details.append(f"[{label}] RSI={rsi:.1f} OVERSOLD → BUY +2")
    elif rsi > 65:
        score_sell += 2
        details.append(f"[{label}] RSI={rsi:.1f} OVERBOUGHT → SELL +2")
    elif rsi < 50:
        score_buy += 1
        details.append(f"[{label}] RSI={rsi:.1f} below 50 → BUY +1")
    else:
        score_sell += 1
        details.append(f"[{label}] RSI={rsi:.1f} above 50 → SELL +1")

    # ── MACD histogram direction
    macd_line, signal_line, histogram = _macd(closes)
    if histogram is not None:
        histogram_threshold = abs(closes[-1]) * 0.00005
        if abs(histogram) > histogram_threshold:
            if histogram > 0:
                score_buy += 2
                details.append(f"[{label}] MACD histogram positive → BUY +2")
            else:
                score_sell += 2
                details.append(f"[{label}] MACD histogram negative → SELL +2")
        else:
            details.append(f"[{label}] MACD histogram too weak — SKIP")

        if macd_line and signal_line:
            if macd_line > signal_line:
                score_buy += 1
                details.append(f"[{label}] MACD above signal → BUY +1")
            else:
                score_sell += 1
                details.append(f"[{label}] MACD below signal → SELL +1")

    # ── Bollinger Bands position
    bb_upper, bb_mid, bb_lower = _bollinger(closes)
    if bb_upper and bb_lower:
        price = closes[-1]
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            bb_pos = (price - bb_lower) / bb_range
            if bb_pos < 0.25:
                score_buy += 1
                details.append(f"[{label}] Price near BB lower → BUY +1")
            elif bb_pos > 0.75:
                score_sell += 1
                details.append(f"[{label}] Price near BB upper → SELL +1")

    # ── Candle momentum (lookback=5)
    pattern = _candle_strength(candles, lookback=5)
    if pattern == 1:
        score_buy += 1
        details.append(f"[{label}] Bullish candle momentum → BUY +1")
    elif pattern == -1:
        score_sell += 1
        details.append(f"[{label}] Bearish candle momentum → SELL +1")

    # ════════════════════════════════════════════
    #  NEW INDICATORS — v4
    # ════════════════════════════════════════════

    # ── HMA(5,9): price vs HMA — fast trend filter
    hma_val = _hma(closes, 9)
    if hma_val is not None:
        price = closes[-1]
        if price > hma_val:
            score_buy += 1
            details.append(f"[{label}] Price>HMA9 → BUY +1")
        else:
            score_sell += 1
            details.append(f"[{label}] Price<HMA9 → SELL +1")

    # ── Ultimate Oscillator (7,14,28)
    uo = _ultimate_oscillator(candles, 7, 14, 28)
    if uo is not None:
        if uo < 30:
            score_buy += 2
            details.append(f"[{label}] UO={uo:.1f} OVERSOLD → BUY +2")
        elif uo > 70:
            score_sell += 2
            details.append(f"[{label}] UO={uo:.1f} OVERBOUGHT → SELL +2")
        elif uo < 50:
            score_sell += 1
            details.append(f"[{label}] UO={uo:.1f} below 50 → SELL +1")
        else:
            score_buy += 1
            details.append(f"[{label}] UO={uo:.1f} above 50 → BUY +1")

    # ── ADX(14): trend strength + direction
    adx_val, plus_di, minus_di = _adx(candles, 14)
    if adx_val is not None and plus_di is not None and minus_di is not None:
        if adx_val > 25:  # trending market
            if plus_di > minus_di:
                score_buy += 2
                details.append(f"[{label}] ADX={adx_val:.1f} DI+>{minus_di:.1f} → BUY +2")
            else:
                score_sell += 2
                details.append(f"[{label}] ADX={adx_val:.1f} DI->{plus_di:.1f} → SELL +2")
        else:
            details.append(f"[{label}] ADX={adx_val:.1f} weak trend (<25) — SKIP")

    # ── Bull Bear Power (Elder Ray, 13)
    bull_pwr, bear_pwr = _bull_bear_power(candles, 13)
    if bull_pwr is not None and bear_pwr is not None:
        if bull_pwr > 0 and bear_pwr > 0:
            score_buy += 2
            details.append(f"[{label}] Bull={bull_pwr:.2f} Bear={bear_pwr:.2f} both>0 → BUY +2")
        elif bull_pwr < 0 and bear_pwr < 0:
            score_sell += 2
            details.append(f"[{label}] Bull={bull_pwr:.2f} Bear={bear_pwr:.2f} both<0 → SELL +2")
        elif bull_pwr > 0:
            score_buy += 1
            details.append(f"[{label}] Bull Power>0 ({bull_pwr:.2f}) → BUY +1")
        elif bear_pwr < 0:
            score_sell += 1
            details.append(f"[{label}] Bear Power<0 ({bear_pwr:.2f}) → SELL +1")

    # ── Momentum(20)
    mom = _momentum(closes, 20)
    if mom is not None:
        if mom > 0:
            score_buy += 1
            details.append(f"[{label}] Momentum={mom:.2f} positive → BUY +1")
        elif mom < 0:
            score_sell += 1
            details.append(f"[{label}] Momentum={mom:.2f} negative → SELL +1")

    # ── PPO(12,26,9)
    ppo_line, ppo_signal, ppo_hist = _ppo(closes, 12, 26, 9)
    if ppo_line is not None:
        if ppo_line > 0:
            score_buy += 1
            details.append(f"[{label}] PPO={ppo_line:.3f} positive → BUY +1")
        else:
            score_sell += 1
            details.append(f"[{label}] PPO={ppo_line:.3f} negative → SELL +1")
        if ppo_hist is not None:
            if ppo_hist > 0:
                score_buy += 1
                details.append(f"[{label}] PPO histogram positive → BUY +1")
            else:
                score_sell += 1
                details.append(f"[{label}] PPO histogram negative → SELL +1")

    # ── Stochastic RSI(14)
    stoch_k, stoch_d = _stoch_rsi(closes, 14)
    if stoch_k is not None:
        if stoch_k < 20:
            score_buy += 2
            details.append(f"[{label}] StochRSI K={stoch_k:.1f} OVERSOLD → BUY +2")
        elif stoch_k > 80:
            score_sell += 2
            details.append(f"[{label}] StochRSI K={stoch_k:.1f} OVERBOUGHT → SELL +2")
        else:
            if stoch_d is not None and stoch_k > stoch_d:
                score_buy += 1
                details.append(f"[{label}] StochRSI K>D ({stoch_k:.1f}>{stoch_d:.1f}) → BUY +1")
            elif stoch_d is not None and stoch_k < stoch_d:
                score_sell += 1
                details.append(f"[{label}] StochRSI K<D ({stoch_k:.1f}<{stoch_d:.1f}) → SELL +1")

    # ── Ichimoku Cloud(9,26,52)
    ichi = _ichimoku(candles, 9, 26, 52)
    if ichi is not None:
        price = closes[-1]
        cloud_top    = max(ichi['senkou_a'], ichi['senkou_b'])
        cloud_bottom = min(ichi['senkou_a'], ichi['senkou_b'])
        ichi_score_b = 0
        ichi_score_s = 0

        # Price vs Cloud
        if price > cloud_top:
            ichi_score_b += 2
            details.append(f"[{label}] Ichimoku: Price above cloud → BUY +2")
        elif price < cloud_bottom:
            ichi_score_s += 2
            details.append(f"[{label}] Ichimoku: Price below cloud → SELL +2")
        else:
            details.append(f"[{label}] Ichimoku: Price inside cloud — NEUTRAL")

        # Tenkan vs Kijun
        if ichi['tenkan'] > ichi['kijun']:
            ichi_score_b += 1
            details.append(f"[{label}] Ichimoku: Tenkan>Kijun → BUY +1")
        else:
            ichi_score_s += 1
            details.append(f"[{label}] Ichimoku: Tenkan<Kijun → SELL +1")

        # Chikou vs past price
        if ichi['price_ago'] is not None:
            if ichi['chikou'] > ichi['price_ago']:
                ichi_score_b += 1
                details.append(f"[{label}] Ichimoku: Chikou above past price → BUY +1")
            else:
                ichi_score_s += 1
                details.append(f"[{label}] Ichimoku: Chikou below past price → SELL +1")

        score_buy  += ichi_score_b
        score_sell += ichi_score_s

    # ── CCI(20)
    cci_val = _cci(candles, 20)
    if cci_val is not None:
        if cci_val < -100:
            score_buy += 2
            details.append(f"[{label}] CCI={cci_val:.1f} OVERSOLD (<-100) → BUY +2")
        elif cci_val > 100:
            score_sell += 2
            details.append(f"[{label}] CCI={cci_val:.1f} OVERBOUGHT (>100) → SELL +2")
        elif cci_val > 0:
            score_buy += 1
            details.append(f"[{label}] CCI={cci_val:.1f} positive → BUY +1")
        else:
            score_sell += 1
            details.append(f"[{label}] CCI={cci_val:.1f} negative → SELL +1")

    # ── Awesome Oscillator(5,34)
    ao_val = _awesome_oscillator(candles, 5, 34)
    if ao_val is not None:
        if ao_val > 0:
            score_buy += 1
            details.append(f"[{label}] AO={ao_val:.2f} positive → BUY +1")
        else:
            score_sell += 1
            details.append(f"[{label}] AO={ao_val:.2f} negative → SELL +1")

    # ── Williams %R(14)
    wr_val = _williams_r(candles, 14)
    if wr_val is not None:
        if wr_val < -80:
            score_buy += 2
            details.append(f"[{label}] Williams %R={wr_val:.1f} OVERSOLD → BUY +2")
        elif wr_val > -20:
            score_sell += 2
            details.append(f"[{label}] Williams %R={wr_val:.1f} OVERBOUGHT → SELL +2")
        elif wr_val < -50:
            score_buy += 1
            details.append(f"[{label}] Williams %R={wr_val:.1f} bearish zone → SELL +1")
        else:
            score_sell += 1
            details.append(f"[{label}] Williams %R={wr_val:.1f} bullish zone → BUY +1")

    # ── MA Suite: SMA & EMA 5/10/20/50/100/200
    ma_b, ma_s, ma_det = _ma_suite_score(closes, label)
    score_buy  += ma_b
    score_sell += ma_s
    details    += ma_det

    # ════════════════════════════════════════════
    #  FINAL BIAS
    # ════════════════════════════════════════════
    net = score_buy - score_sell
    if net > 0:
        bias = 'BUY'
        score = score_buy
    elif net < 0:
        bias = 'SELL'
        score = score_sell
    else:
        bias = 'NEUTRAL'
        score = 0

    return {
        'bias':       bias,
        'score':      score,
        'score_buy':  score_buy,
        'score_sell': score_sell,
        'net':        net,
        'rsi':        rsi,
        'ema9':       ema9,
        'ema21':      ema21,
        'ema50':      ema50,
        'details':    details,
        # Extra values for logging/display
        'adx':        adx_val,
        'cci':        cci_val,
        'ao':         ao_val,
        'williams_r': wr_val,
        'uo':         uo,
        'ppo':        ppo_line,
        'stoch_k':    stoch_k,
        'hma':        hma_val,
    }


# ──────────────────────────────────────────────
#  CANDLE FETCHER  (unchanged from v3)
# ──────────────────────────────────────────────

def _fetch_candles(symbol, resolution, num_candles):
    try:
        res_seconds = {
            '1m': 60, '3m': 180, '5m': 300,
            '15m': 900, '30m': 1800,
            '1h': 3600, '4h': 14400, '1d': 86400
        }
        sec = res_seconds.get(resolution, 300)
        end_time   = int(_time.time())
        start_time = end_time - (num_candles * sec)

        response = make_api_request(
            'GET',
            f'/history/candles?resolution={resolution}&symbol={symbol}&start={start_time}&end={end_time}'
        )
        if not response or not response.get('result'):
            print(f"⚠️ No candles for {symbol} @ {resolution}")
            return []

        parsed = []
        for c in response['result']:
            try:
                parsed.append({
                    'open':  float(c.get('open', 0)),
                    'high':  float(c.get('high', 0)),
                    'low':   float(c.get('low', 0)),
                    'close': float(c.get('close', 0)),
                    'time':  c.get('time', 0)
                })
            except Exception:
                continue

        parsed.sort(key=lambda x: x['time'])
        print(f"📊 {symbol} @ {resolution}: {len(parsed)} candles fetched")
        return parsed

    except Exception as e:
        print(f"❌ Error fetching {resolution} candles: {e}")
        return []


# ──────────────────────────────────────────────
#  ATR MARKET FILTER  (unchanged from v3)
# ──────────────────────────────────────────────

def _is_market_tradeable(candles_15m):
    if len(candles_15m) < 15:
        return True

    atr_val = _atr(candles_15m, 14)
    closes  = [c['close'] for c in candles_15m]
    price   = closes[-1]

    if atr_val is None or price <= 0:
        return True

    atr_pct = (atr_val / price) * 100

    if atr_pct < 0.02:
        print(f"⚠️ Market too flat: ATR={atr_pct:.4f}% — SKIPPING signal")
        return False

    print(f"✅ Market volatility OK: ATR={atr_pct:.4f}%")
    return True


# ──────────────────────────────────────────────
#  MAIN SIGNAL FUNCTION — v4
# ──────────────────────────────────────────────

def generate_smart_signal(reason="trade_decision"):
    """
    SIGNAL ENGINE v4 — Multi-Timeframe Confluence + Full Indicator Suite

    KEY CHANGES vs v3:
    - All TradingView indicators added: HMA, UO, ADX, Bull/Bear Power,
      Momentum, PPO, StochRSI, Ichimoku, CCI, AO, Williams %R, MA Suite
    - Higher max_possible score (was 10, now dynamic — ~40+ per TF)
    - Confidence formula normalized to new max
    - MIN_15M_NET kept at 3 (fast signal generation maintained)
    - 4H still advisory, 1H+15M required

    Logic:
    1. Fetch 4h, 1h, 15m candles
    2. Score each timeframe with ALL indicators
    3. 1H + 15M MUST agree (required)
    4. 4H is bonus — if agrees, confidence boost; if neutral/conflicts, warning only
    5. 15m net score >= 3 required
    6. ATR filter (skip flat markets)
    7. Add ref_entry/ref_sl/ref_tp for display purposes only
    """

    symbol = BOT_STATE.get('symbol', 'ETHUSD')
    print(f"\n{'='*60}")
    print(f"🧠 SIGNAL ENGINE v4 — {symbol} — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    # ── Step 1: Fetch candles ────────────────────────────────
    # Need more candles now for Ichimoku(52), MA200, StochRSI etc.
    candles_4h  = _fetch_candles(symbol, '4h',  120)
    candles_1h  = _fetch_candles(symbol, '1h',  120)
    candles_15m = _fetch_candles(symbol, '15m', 120)

    if len(candles_4h) < 20:
        print(f"⚠️ Not enough 4h candles ({len(candles_4h)}) — 4H will be advisory only")
        candles_4h = None

    if len(candles_1h) < 20 or len(candles_15m) < 20:
        print(f"⚠️ Insufficient 1H/15M candle data — random fallback")
        direction = random.choice(['BUY', 'SELL'])
        return _make_signal(direction, 50, 'RANDOM_FALLBACK', 0, reason,
                            {}, {}, {}, candles_15m or [])

    # ── Step 2: ATR volatility filter ───────────────────────
    if not _is_market_tradeable(candles_15m):
        return _make_wait_signal(reason, "Market too flat (low ATR)")

    # ── Step 3: Score each timeframe ────────────────────────
    result_4h  = _score_timeframe(candles_4h,  '4H') if candles_4h else None
    result_1h  = _score_timeframe(candles_1h,  '1H')
    result_15m = _score_timeframe(candles_15m, '15M')

    print(f"\n📊 TIMEFRAME SCORES:")
    if result_4h:
        print(f"   4H  → {result_4h['bias']:7s} | BUY={result_4h['score_buy']} SELL={result_4h['score_sell']} | Net={result_4h['net']} [ADVISORY]")
    print(f"   1H  → {result_1h['bias']:7s} | BUY={result_1h['score_buy']} SELL={result_1h['score_sell']} | Net={result_1h['net']} [REQUIRED]")
    print(f"   15M → {result_15m['bias']:7s} | BUY={result_15m['score_buy']} SELL={result_15m['score_sell']} | Net={result_15m['net']} [REQUIRED]")

    bias_1h  = result_1h['bias']
    bias_15m = result_15m['bias']
    bias_4h  = result_4h['bias'] if result_4h else 'NEUTRAL'

    # ── Step 4: Core confluence — 1H + 15M MUST agree ───────
    if bias_1h == 'NEUTRAL' or bias_15m == 'NEUTRAL':
        print(f"⚖️ 1H or 15M is NEUTRAL — WAIT")
        return _make_wait_signal(reason, f"Neutral TF: 1H={bias_1h} 15M={bias_15m}")

    if bias_1h != bias_15m:
        print(f"⚡ 1H vs 15M CONFLICT — 1H={bias_1h} 15M={bias_15m} — WAIT")
        return _make_wait_signal(reason, f"1H/15M conflict: 1H={bias_1h} 15M={bias_15m}")

    # ── Step 5: Entry quality filter ────────────────────────
    MIN_15M_NET = 3

    if abs(result_15m['net']) < MIN_15M_NET:
        print(f"📉 15M signal too weak (net={result_15m['net']}, need >={MIN_15M_NET}) — WAIT")
        return _make_wait_signal(reason,
            f"15M weak signal: net={result_15m['net']} (need >={MIN_15M_NET})")

    # ── Step 6: All checks passed → CONFIRMED ───────────────
    direction = bias_15m

    # Confidence — normalize against total possible score
    # Max theoretical score per TF ≈ 40 (with all new indicators)
    MAX_SCORE = 40.0
    w1  = 0.45
    w15 = 0.55
    conf_raw = (result_1h['score'] * w1 + result_15m['score'] * w15) / MAX_SCORE

    # 4H bonus/penalty
    if result_4h:
        if bias_4h == direction:
            conf_raw = min(conf_raw * 1.15, 1.0)
            print(f"   ✅ 4H AGREES ({bias_4h}) — confidence boosted")
        elif bias_4h == 'NEUTRAL':
            conf_raw = conf_raw * 0.95
            print(f"   ⚠️ 4H NEUTRAL — slight confidence reduction")
        else:
            conf_raw = conf_raw * 0.85
            print(f"   ⚠️ 4H DISAGREES ({bias_4h} vs {direction}) — confidence reduced")

    confidence = int(min(50 + conf_raw * 50, 95))

    layer = 'STRONG_BUY' if direction == 'BUY' else 'STRONG_SELL'
    if result_15m['score'] < 20:
        layer = 'MODERATE_BUY' if direction == 'BUY' else 'MODERATE_SELL'

    if result_4h and bias_4h == direction and result_15m['score'] >= 15:
        layer = 'STRONG_BUY' if direction == 'BUY' else 'STRONG_SELL'

    print(f"\n✅ CONFIRMED SIGNAL: {direction}")
    print(f"   1H={bias_1h} 15M={bias_15m} 4H={bias_4h}(advisory)")
    print(f"   15M net score: {result_15m['net']} / max ~{int(MAX_SCORE*2)}")
    print(f"   Confidence: {confidence}%  Layer: {layer}")

    all_details = []
    if result_4h: all_details += result_4h['details']
    all_details += result_1h['details']
    all_details += result_15m['details']
    for d in all_details:
        print(f"   {d}")

    return _make_signal(
        direction, confidence, layer,
        result_15m['net'], reason,
        result_4h or {}, result_1h, result_15m,
        candles_15m
    )


# ──────────────────────────────────────────────
#  SIGNAL BUILDER HELPERS  (unchanged from v3)
# ──────────────────────────────────────────────

def _make_signal(direction, confidence, layer, net_score, reason,
                 r4h, r1h, r15m, candles_15m):
    """
    Build the standard signal dict.
    ref_entry / ref_sl / ref_tp = READING ONLY (bot uses its own SL/TP logic)
    """
    price   = candles_15m[-1]['close'] if candles_15m else 0
    atr_val = _atr(candles_15m, 14) if candles_15m else None

    if atr_val and price:
        if direction == 'BUY':
            ref_sl = round(price - 1.5 * atr_val, 4)
            ref_tp = round(price + 3.0 * atr_val, 4)
        else:
            ref_sl = round(price + 1.5 * atr_val, 4)
            ref_tp = round(price - 3.0 * atr_val, 4)
    else:
        ref_sl = None
        ref_tp = None

    print(f"   📍 Entry={price} | ref_SL={ref_sl} | ref_TP={ref_tp} (display only)")

    return {
        'signal':    direction,
        'timestamp': datetime.now().isoformat(),
        'confidence': confidence,
        'layer':     layer,
        'score':     net_score,
        'score_buy':  r15m.get('score_buy', 0),
        'score_sell': r15m.get('score_sell', 0),
        'source':    'smart_signal_v4',

        # ── Reference levels (READ ONLY — bot does NOT use these for orders) ──
        'entry_price': price,
        'ref_sl':      ref_sl,
        'ref_tp':      ref_tp,

        'reason': (
            f"MTF confluence: "
            f"4H={r4h.get('bias','?')}(advisory) "
            f"1H={r1h.get('bias','?')} "
            f"15M={r15m.get('bias','?')} | "
            f"Net15m={net_score}"
        ),
        'decision_ready':      True,
        'decision_confidence': confidence / 100,
        'wait':                False,
        'position_analysis':   {'has_position': False},
        'backtest_results': {
            'ema9':      r15m.get('ema9'),
            'ema21':     r15m.get('ema21'),
            'ema50':     r15m.get('ema50'),
            'rsi':       r15m.get('rsi'),
            'adx':       r15m.get('adx'),
            'cci':       r15m.get('cci'),
            'ao':        r15m.get('ao'),
            'williams_r':r15m.get('williams_r'),
            'uo':        r15m.get('uo'),
            'ppo':       r15m.get('ppo'),
            'stoch_k':   r15m.get('stoch_k'),
            'hma':       r15m.get('hma'),
            'price':     price,
            'ref_sl':    ref_sl,
            'ref_tp':    ref_tp,
            'factors':   r15m.get('details', []),
            '4h_bias':   r4h.get('bias', '?'),
            '1h_bias':   r1h.get('bias', '?'),
            '15m_bias':  r15m.get('bias', '?'),
        },
        'last_trade_result': reason,
    }


def _make_wait_signal(reason, why):
    """Return a WAIT signal — bot will sleep and retry"""
    print(f"⏸️ WAIT: {why}")
    return {
        'signal':      'WAIT',
        'timestamp':   datetime.now().isoformat(),
        'confidence':  0,
        'layer':       'WAIT',
        'score':       0,
        'score_buy':   0,
        'score_sell':  0,
        'source':      'smart_signal_v4',
        'reason':      why,
        'entry_price': None,
        'ref_sl':      None,
        'ref_tp':      None,
        'decision_ready':      False,
        'decision_confidence': 0,
        'wait':                True,
        'position_analysis':   {'has_position': False},
        'backtest_results':    {},
        'last_trade_result':   reason,
    }


