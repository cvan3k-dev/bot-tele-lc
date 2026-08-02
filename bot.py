#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════
#   CAO FPS - SIÊU BOT DỰ ĐOÁN TÀI XỈU
#   Version: 3.1 | 35 Thuật Toán + AI Học Tăng Cường
#   Phân Tích 30-30 Phiên | Render Optimized
#   HQuanz Studio
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import json
import time
import uuid
import threading
import ssl
import urllib.request
import math
import random
from datetime import datetime, timedelta
from collections import Counter, deque
from math import log2, sqrt

# ─── KIỂM TRA SINGLE INSTANCE ──────────────────────────────────
try:
    import fcntl
    LOCK_FILE = "caofps.lock"
    fp = open(LOCK_FILE, 'w')
    fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except:
    print("⚠️ CAO FPS đã chạy ở instance khác! Thoát...")
    sys.exit(0)

# ─── TELEGRAM ──────────────────────────────────────────────────
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ═══════════════════════════════════════════════════════════════════
#  CẤU HÌNH CAO CẤP
# ═══════════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "8774993011:AAHM3uCpCqlaOTRdOIL1mDU-JGDkdLT78sA")
ADMIN_IDS = [5888859004]
API_URL = "https://wtxmd52.tele68.com/v1/txmd5/sessions"
SYNC_SEC = 5
TAI, XIU = "T", "X"
DATA_FILE = "caofps_data.json"

# Cấu hình AI
LEARNING_RATE = 0.01
MEMORY_SIZE = 100
DEEP_ANALYSIS = 30

# ═══════════════════════════════════════════════════════════════════
#  DATABASE THÔNG MINH (JSON)
# ═══════════════════════════════════════════════════════════════════
class SmartDB:
    def __init__(self):
        self._data = self._load()
    
    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "keys": {},
            "users": {},
            "stats": {"total": 0, "win": 0, "loss": 0, "streak": 0, "best": 0},
            "ai_memory": [],
            "pattern_db": {}
        }
    
    def _save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def get_keys(self):
        return self._data.get("keys", {})
    
    def get_users(self):
        return self._data.get("users", {})
    
    def get_stats(self):
        return self._data.get("stats", {"total": 0, "win": 0, "loss": 0, "streak": 0, "best": 0})
    
    def get_ai_memory(self):
        return self._data.get("ai_memory", [])
    
    def get_pattern_db(self):
        return self._data.get("pattern_db", {})
    
    def save_key(self, k, v):
        self._data["keys"][k] = v
        self._save()
    
    def save_user(self, uid, v):
        self._data["users"][str(uid)] = v
        self._save()
    
    def save_stats(self, s):
        self._data["stats"] = s
        self._save()
    
    def save_ai_memory(self, mem):
        self._data["ai_memory"] = mem[-MEMORY_SIZE:]
        self._save()
    
    def save_pattern(self, key, value):
        self._data["pattern_db"][key] = value
        self._save()

db = SmartDB()

# ═══════════════════════════════════════════════════════════════════
#  HỆ THỐNG KEY
# ═══════════════════════════════════════════════════════════════════
def gen_key(days):
    key = "FPS-" + uuid.uuid4().hex[:12].upper()
    db.save_key(key, {
        "expire": (datetime.now() + timedelta(days=days)).isoformat(),
        "used_by": None,
        "created": datetime.now().isoformat()
    })
    return key

def activate_key(uid, key):
    keys = db.get_keys()
    if key not in keys:
        return "❌ Key không tồn tại"
    k = keys[key]
    if datetime.fromisoformat(k["expire"]) < datetime.now():
        return "❌ Key đã hết hạn"
    if k["used_by"] and k["used_by"] != uid:
        return "❌ Key đã dùng bởi người khác"
    k["used_by"] = uid
    db.save_key(key, k)
    db.save_user(uid, {
        "key": key,
        "expire": k["expire"],
        "activated": datetime.now().isoformat()
    })
    exp = datetime.fromisoformat(k["expire"]).strftime("%d/%m/%Y %H:%M")
    return f"✅ Kích hoạt thành công!\n⏰ Hết hạn: {exp}"

def is_valid(uid):
    if uid in ADMIN_IDS:
        return True
    u = db.get_users().get(str(uid))
    return u and datetime.fromisoformat(u["expire"]) > datetime.now()

def expire_str(uid):
    if uid in ADMIN_IDS:
        return "∞ Admin"
    u = db.get_users().get(str(uid))
    if not u:
        return "Chưa kích hoạt"
    exp = datetime.fromisoformat(u["expire"])
    days_left = (exp - datetime.now()).days
    return f"{exp.strftime('%d/%m/%Y')} (còn {days_left} ngày)"

# ═══════════════════════════════════════════════════════════════════
#  FETCH API
# ═══════════════════════════════════════════════════════════════════
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def fetch_history():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
            d = json.loads(r.read().decode())
            if d.get("list"):
                hist = [{"session": int(i["id"]),
                         "result": "T" if i.get("resultTruyenThong") == "TAI" else "X"}
                        for i in d["list"]]
                hist.reverse()
                return hist
    except Exception as e:
        print(f"⚠️ Lỗi fetch API: {e}")
    return []

# ═══════════════════════════════════════════════════════════════════
#  35 THUẬT TOÁN
# ═══════════════════════════════════════════════════════════════════
def opp(r):
    return XIU if r == TAI else TAI

def a1_basic(hist):
    if len(hist) < 5:
        return hist[-1]["result"] if hist else TAI, 60
    r = [h["result"] for h in hist[-10:]]
    if len(r) >= 4 and r[-1] != r[-2] and r[-2] != r[-3] and r[-3] != r[-4]:
        return opp(r[-1]), 72
    if len(r) >= 4 and r[-1] == r[-2] and r[-3] == r[-4] and r[-2] != r[-3]:
        return opp(r[-1]), 75
    if len(r) >= 3 and r[-1] == r[-2] == r[-3]:
        return r[-1], 78
    c = Counter(r[-5:])
    return (TAI if c[TAI] > c[XIU] else XIU), 62

def a2_trend(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    def trend(n):
        s = r[-n:]
        c = s.count(TAI)
        return (TAI if c > n-c else XIU, abs(c-(n-c))/n)
    s_t, s_s = trend(5)
    m_t, m_s = trend(10)
    l_t, l_s = trend(20)
    deep_t, deep_s = trend(30)
    sc = {TAI: 0.0, XIU: 0.0}
    for p, q, w in [(s_t, s_s, 0.4), (m_t, m_s, 0.3), (l_t, l_s, 0.2), (deep_t, deep_s, 0.1)]:
        sc[p] += q * w
    w = TAI if sc[TAI] >= sc[XIU] else XIU
    return w, min(92, int(60 + min(sc[w], 0.4) * 80))

def a3_imbalance(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    t = r.count(TAI)
    x = 20-t
    if abs(t-x) >= 6:
        return (XIU if t > x else TAI), int(65 + (abs(t-x)-6)*3)
    return hist[-1]["result"], 55

def a4_short(hist):
    if len(hist) < 8:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-8:]]
    l3 = r[-3:]
    if all(v == TAI for v in l3):
        return TAI, 76
    if all(v == XIU for v in l3):
        return XIU, 76
    if l3[0] == l3[1] and l3[1] != l3[2]:
        return l3[1], 70
    if l3[1] == l3[2] and l3[0] != l3[1]:
        return opp(l3[2]), 68
    t = r.count(TAI)
    return (TAI if t > 4 else XIU), 62

def a5_weight(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-30:]]
    t = r.count(TAI)
    x = 30-t
    if abs(t-x) >= 10:
        return (XIU if t > x else TAI), int(65 + (abs(t-x)-10)*2)
    return hist[-1]["result"], 55

def a6_break(hist):
    if len(hist) < 10:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]
    streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last:
            streak += 1
        else:
            break
    if streak >= 8:
        return opp(last), 85
    if streak >= 6:
        return opp(last), 78
    if streak >= 4:
        return opp(last), 70
    if streak >= 3:
        return last, 72
    return last, 62

def a7_rebalance(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    t = r.count(TAI)
    x = 20-t
    ratio = max(t, x)/20
    if ratio > 0.70:
        return (XIU if t > x else TAI), int(65 + ratio*25)
    return hist[-1]["result"], 55

def a8_random(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    rate = chg/14
    if rate > 0.70:
        return hist[-1]["result"], 50
    return Counter(r).most_common(1)[0][0], int(68 - rate*30)

def a9_fib(hist):
    if len(hist) < 10:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-10:]]
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55][:len(r)]
    tw = sum(fib[i] for i, v in enumerate(r) if v == TAI)
    xw = sum(fib[i] for i, v in enumerate(r) if v == XIU)
    w = TAI if tw >= xw else XIU
    return w, min(88, int(60 + (abs(tw-xw)/(tw+xw))*40 if tw+xw > 0 else 60))

def a10_prob(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]
    streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last:
            streak += 1
        else:
            break
    brk = 0
    total = 0
    for i in range(len(r)-1):
        run = 1
        for j in range(i-1, -1, -1):
            if r[j] == r[i]:
                run += 1
            else:
                break
        if run == streak and i+1 < len(r):
            total += 1
            if r[i+1] != r[i]:
                brk += 1
    prob = brk/total if total > 0 else 0.5
    return (opp(last) if prob > 0.55 else last), int(55 + prob*35)

def a11_volatility(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-20:]]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    vol = chg/19
    if vol < 0.3:
        return Counter(r).most_common(1)[0][0], int(72 + (0.3-vol)*70)
    if vol > 0.70:
        return opp(r[-1]), 62
    c = Counter(r[-6:])
    return (TAI if c[TAI] > c[XIU] else XIU), 62

def a12_pattern(hist):
    if len(hist) < 5:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    patterns = {
        ("T", "X", "T", "X"): TAI, ("X", "T", "X", "T"): XIU,
        ("T", "T", "X", "X"): TAI, ("X", "X", "T", "T"): XIU,
        ("T", "X", "X", "T"): XIU, ("X", "T", "T", "X"): TAI,
        ("T", "T", "T", "X"): XIU, ("X", "X", "X", "T"): TAI,
        ("T", "X", "T", "T"): XIU, ("X", "T", "X", "X"): TAI,
        ("T", "T", "X", "T"): TAI, ("X", "X", "T", "X"): XIU,
    }
    patterns3 = {
        ("T", "X", "T"): TAI, ("X", "T", "X"): XIU,
        ("T", "T", "X"): XIU, ("X", "X", "T"): TAI,
        ("T", "X", "X"): XIU, ("X", "T", "T"): TAI,
    }
    if len(r) >= 5 and tuple(r[-5:]) in patterns:
        return patterns[tuple(r[-5:])], 75
    if len(r) >= 4 and tuple(r[-4:]) in patterns:
        return patterns[tuple(r[-4:])], 70
    if len(r) >= 3 and tuple(r[-3:]) in patterns3:
        return patterns3[tuple(r[-3:])], 65
    return r[-1], 55

def a13_performance(hist):
    return a2_trend(hist)

def a14_trendbreak(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-25:]]
    dom = Counter(r).most_common(1)[0][0]
    ratio = r.count(dom)/25
    if ratio > 0.60:
        return opp(dom), int(55 + ratio*25)
    return hist[-1]["result"], 58

def a15_follow(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    t15 = r[-15:]
    t = t15.count(TAI)
    x = 15-t
    if abs(t-x)/15 > 0.45:
        return (TAI if t > x else XIU), int(65 + abs(t-x)/15*35)
    c = Counter(r[-6:])
    return c.most_common(1)[0][0], 62

def a16_compbreak(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]
    streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last:
            streak += 1
        else:
            break
    sc = {opp(last): 0.0, last: 0.0}
    if streak >= 5:
        sc[opp(last)] += 0.45
    elif streak >= 3:
        sc[opp(last)] += 0.25
    else:
        sc[last] += 0.2
    dom = Counter(r[-12:]).most_common(1)[0][0]
    if dom == last:
        sc[last] += 0.3
    else:
        sc[opp(last)] += 0.3
    c = Counter(r[-30:])
    n = len(c.elements())
    ent = -sum((v/n)*log2(v/n) for v in c.values() if v > 0) if n > 0 else 1
    if ent > 0.90:
        sc[opp(last)] += 0.25
    else:
        sc[last] += 0.2
    w = max(sc, key=sc.get)
    return w, min(92, int(60 + sc[w]*42))

def a17_adaptive(hist):
    return a15_follow(hist)

def a18_shorttrend(hist):
    if len(hist) < 8:
        return hist[-1]["result"] if hist else TAI, 58
    s = [h["result"] for h in hist[-8:]]
    t = s.count(TAI)
    x = 8-t
    if t > x*2.5:
        return TAI, int(74 + (t-x)*2)
    if x > t*2.5:
        return XIU, int(74 + (x-t)*2)
    return (TAI if t > x else XIU), int(62 + abs(t-x)*5)

def a19_popular(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-35:]]
    pn = {}
    pc = {}
    for i in range(len(r)-4):
        k = tuple(r[i:i+4])
        nxt = r[i+4] if i+4 < len(r) else None
        if nxt:
            pc[k] = pc.get(k, 0) + 1
            if k not in pn:
                pn[k] = {TAI: 0, XIU: 0}
            pn[k][nxt] += 1
    l4 = tuple(r[-4:])
    if l4 in pn:
        p = pn[l4]
        w = TAI if p[TAI] >= p[XIU] else XIU
        return w, min(90, int(60 + (p[w]/(p[TAI]+p[XIU]))*35))
    c = Counter(r[-12:])
    return c.most_common(1)[0][0], 58

def a20_ensemble(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 60
    sc = {TAI: 0.0, XIU: 0.0}
    for fn, w in [(a2_trend, 1.6), (a6_break, 1.4), (a19_popular, 1.3), (a16_compbreak, 1.2), (a23_entropy, 1.1)]:
        r, c = fn(hist)
        sc[r] += w * (c/100)
    total = sc[TAI] + sc[XIU]
    w = max(sc, key=sc.get)
    return w, min(94, int(60 + (sc[w]/total)*40 if total > 0 else 60))

def a21_global(hist):
    if len(hist) < 50:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-50:]]
    t = r.count(TAI)
    x = 50-t
    if abs(t-x)/50 > 0.2:
        return (XIU if t > x else TAI), int(63 + abs(t-x)/50*42)
    return hist[-1]["result"], 55

def a22_markov2(hist):
    if len(hist) < 25:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    tr = {}
    for i in range(len(r)-2):
        k = (r[i], r[i+1])
        nxt = r[i+2]
        if k not in tr:
            tr[k] = {TAI: 0, XIU: 0}
        tr[k][nxt] += 1
    k2 = (r[-2], r[-1])
    if k2 in tr:
        p = tr[k2]
        tot = p[TAI] + p[XIU]
        if tot > 0:
            w = TAI if p[TAI] >= p[XIU] else XIU
            return w, min(91, int(62 + (p[w]/tot)*34))
    return r[-1], 58

def a23_entropy(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-15:]]
    n = len(r)
    c = Counter(r)
    ent = -sum((v/n)*log2(v/n) for v in c.values() if v > 0)
    if ent < 0.65:
        return c.most_common(1)[0][0], int(82 - ent*20)
    if ent > 0.90:
        return opp(r[-1]), 68
    c5 = Counter(r[-6:])
    return (TAI if c5[TAI] > c5[XIU] else XIU), 62

def a24_rolling(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-20:]]
    wins = [5, 7, 10, 12, 15, 20]
    scores = {TAI: 0.0, XIU: 0.0}
    for w in wins:
        seg = r[-w:]
        t = seg.count(TAI)
        if t > w-t:
            scores[TAI] += 1.0 * (w/20)
        else:
            scores[XIU] += 1.0 * (w/20)
    w = TAI if scores[TAI] >= scores[XIU] else XIU
    conf = int(55 + (scores[w]/(scores[TAI]+scores[XIU]))*40)
    return w, min(90, conf)

def a25_zigzag(hist):
    if len(hist) < 10:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-12:]]
    zigzag = sum(1 for i in range(2, len(r)) if r[i] != r[i-1] and r[i-1] != r[i-2])
    if zigzag >= 6:
        return opp(r[-1]), 72
    c = Counter(r[-6:])
    return c.most_common(1)[0][0], 62

def a26_deepsim(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-30:]]
    streak_info = []
    i = 0
    while i < len(r):
        j = i
        while j < len(r) and r[j] == r[i]:
            j += 1
        streak_info.append((r[i], j-i))
        i = j
    if len(streak_info) >= 3:
        last_streak = streak_info[-1]
        prev_streak = streak_info[-2] if len(streak_info) >= 2 else None
        if prev_streak and prev_streak[1] >= 4 and last_streak[1] >= 4:
            return opp(last_streak[0]), 78
        if last_streak[1] >= 5:
            return opp(last_streak[0]), 75
    c = Counter(r[-10:])
    return c.most_common(1)[0][0], 62

def a27_momentum(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-20:]]
    momentum = 0
    for i in range(1, len(r)):
        if r[i] == TAI:
            momentum += 1
        else:
            momentum -= 1
    if abs(momentum) >= 6:
        return (TAI if momentum > 0 else XIU), int(65 + abs(momentum)*2)
    return hist[-1]["result"], 58

def a28_meanrev(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-30:]]
    t = r.count(TAI)
    if t/30 > 0.65:
        return XIU, int(60 + (t/30 - 0.65)*100)
    if t/30 < 0.35:
        return TAI, int(60 + (0.35 - t/30)*100)
    return hist[-1]["result"], 55

def a29_rsi(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-15:]]
    gains = sum(1 for i in range(1, len(r)) if r[i] == TAI and r[i-1] == XIU)
    losses = sum(1 for i in range(1, len(r)) if r[i] == XIU and r[i-1] == TAI)
    if gains + losses == 0:
        return r[-1], 55
    rsi = gains / (gains + losses) * 100
    if rsi > 70:
        return XIU, int(65 + (rsi-70)*0.5)
    if rsi < 30:
        return TAI, int(65 + (30-rsi)*0.5)
    return r[-1], 58

def a30_macd(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    def sma(data, n):
        return sum(data[-n:]) / n
    ema12 = sma(r, 12)
    ema26 = sma(r, 26)
    macd = ema12 - ema26
    if macd > 0.2:
        return TAI, int(65 + macd*20)
    if macd < -0.2:
        return XIU, int(65 + abs(macd)*20)
    return ("T" if r[-1] > 0 else "X"), 58

def a31_bollinger(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    mean = sum(r) / len(r)
    std = sqrt(sum((x - mean)**2 for x in r) / len(r))
    last = r[-1]
    if last > mean + std:
        return XIU, int(65 + (last - mean - std)*20)
    if last < mean - std:
        return TAI, int(65 + (mean - std - last)*20)
    return ("T" if last > 0 else "X"), 58

def a32_support(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 58
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    highs = []
    lows = []
    for i in range(2, len(r)-2):
        if r[i] > r[i-1] and r[i] > r[i-2] and r[i] > r[i+1] and r[i] > r[i+2]:
            highs.append(r[i])
        if r[i] < r[i-1] and r[i] < r[i-2] and r[i] < r[i+1] and r[i] < r[i+2]:
            lows.append(r[i])
    if highs and r[-1] >= max(highs):
        return XIU, 68
    if lows and r[-1] <= min(lows):
        return TAI, 68
    return ("T" if r[-1] > 0 else "X"), 58

def a33_fibretrace(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [1 if h["result"] == TAI else -1 for h in hist[-30:]]
    high = max(r)
    low = min(r)
    diff = high - low
    if diff == 0:
        return ("T" if r[-1] > 0 else "X"), 55
    current = r[-1]
    fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    for level in fib_levels:
        price = high - diff * level
        if abs(current - price) / diff < 0.05:
            if current > 0:
                return TAI, 72
            else:
                return XIU, 72
    return ("T" if current > 0 else "X"), 58

def a34_mlsim(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-30:]]
    pattern = r[-5:]
    best_match = None
    best_score = 0
    for i in range(len(r) - 10):
        candidate = r[i:i+5]
        score = sum(1 for j in range(5) if candidate[j] == pattern[j])
        if score > best_score:
            best_score = score
            best_match = r[i+5] if i+5 < len(r) else None
    if best_match and best_score >= 4:
        return best_match, int(70 + best_score*5)
    c = Counter(r[-10:])
    return c.most_common(1)[0][0], 60

def a35_nnsim(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 58
    r = [1 if h["result"] == TAI else -1 for h in hist[-30:]]
    weights = [0.5, 0.3, 0.2, 0.1, -0.1, -0.2, -0.3, -0.5]
    weighted_sum = 0
    for i in range(min(len(weights), len(r))):
        weighted_sum += r[-(i+1)] * weights[i]
    if weighted_sum > 0.3:
        return TAI, int(65 + weighted_sum*20)
    if weighted_sum < -0.3:
        return XIU, int(65 + abs(weighted_sum)*20)
    return ("T" if r[-1] > 0 else "X"), 58

# ─── DANH SÁCH THUẬT TOÁN ───────────────────────────────────────
ALGOS = [
    ("Basic", a1_basic), ("Trend", a2_trend), ("Imbalance", a3_imbalance),
    ("Short", a4_short), ("Weight", a5_weight), ("Break", a6_break),
    ("Rebalance", a7_rebalance), ("Random", a8_random), ("Fibonacci", a9_fib),
    ("ProbBreak", a10_prob), ("Volatility", a11_volatility), ("Pattern", a12_pattern),
    ("Perf", a13_performance), ("TrendBrk", a14_trendbreak), ("Follow", a15_follow),
    ("CompBreak", a16_compbreak), ("Adaptive", a17_adaptive), ("ShortTrend", a18_shorttrend),
    ("Popular", a19_popular), ("Ensemble", a20_ensemble), ("Global", a21_global),
    ("Markov2", a22_markov2), ("Entropy", a23_entropy), ("Rolling", a24_rolling),
    ("Zigzag", a25_zigzag), ("DeepSim", a26_deepsim), ("Momentum", a27_momentum),
    ("MeanRev", a28_meanrev), ("RSI", a29_rsi), ("MACD", a30_macd),
    ("Bollinger", a31_bollinger), ("Support", a32_support), ("FibRetrace", a33_fibretrace),
    ("MLSim", a34_mlsim), ("NNSim", a35_nnsim),
]

# ═══════════════════════════════════════════════════════════════════
#  AI ENGINE - HỌC TỪ DỰ ĐOÁN (ĐÃ FIX LỖI MEMORY)
# ═══════════════════════════════════════════════════════════════════
class AIEngine:
    def __init__(self):
        self.history = []
        self.weights = {n: 1.0 for n, _ in ALGOS}
        self.stats = db.get_stats()
        self.memory = db.get_ai_memory()
        self.pattern_db = db.get_pattern_db()
        self.last = None
        self.learning_rate = LEARNING_RATE
        self.prediction_count = 0
        self._learned_sessions = set()  # Lưu các session đã học

    def update(self, hist):
        if not hist:
            return
        old_last = self.history[-1]["session"] if self.history else None
        self.history = hist

        if self.last and old_last and hist[-1]["session"] == self.last.get("session"):
            actual = hist[-1]["result"]
            self._learn(actual)

            self.stats["total"] += 1
            hit = self.last["result"] == actual
            if hit:
                self.stats["win"] += 1
                self.stats["streak"] += 1
                self.stats["best"] = max(self.stats["best"], self.stats["streak"])
            else:
                self.stats["loss"] += 1
                self.stats["streak"] = 0
            db.save_stats(self.stats)

    def _learn(self, actual):
        """AI học từ kết quả thực tế - ĐÃ FIX"""
        if not self.last:
            return

        # KIỂM TRA: đã học phiên này chưa?
        session_id = self.last.get("session")
        if session_id in self._learned_sessions:
            return  # Đã học rồi, bỏ qua

        # Đánh dấu đã học
        self._learned_sessions.add(session_id)

        self.prediction_count += 1

        # Cập nhật trọng số thuật toán
        for name, pred in self.last.get("details", {}).items():
            if name in self.weights:
                if pred == actual:
                    self.weights[name] = min(2.5, self.weights[name] * (1 + self.learning_rate))
                else:
                    self.weights[name] = max(0.2, self.weights[name] * (1 - self.learning_rate * 0.8))

        # Lưu vào bộ nhớ AI
        self.memory.append({
            "session": session_id,
            "predicted": self.last["result"],
            "actual": actual,
            "confidence": self.last.get("confidence", 50),
            "timestamp": datetime.now().isoformat()
        })
        db.save_ai_memory(self.memory)

        # Học pattern mới
        if len(self.history) >= 5:
            pattern_key = "".join([h["result"] for h in self.history[-5:]])
            if pattern_key not in self.pattern_db:
                self.pattern_db[pattern_key] = {TAI: 0, XIU: 0}
            self.pattern_db[pattern_key][actual] += 1
            db.save_pattern(pattern_key, self.pattern_db[pattern_key])

    def predict(self):
        if not self.history:
            return None

        votes = {TAI: 0.0, XIU: 0.0}
        details = {}
        per_algo = []

        for name, fn in ALGOS:
            try:
                res, conf = fn(self.history)
                weight = self.weights.get(name, 1.0)
                votes[res] += weight * (conf / 100)
                details[name] = res
                per_algo.append((name, res, conf))
            except Exception as e:
                per_algo.append((name, "ERR", 0))

        if len(self.memory) >= 10:
            memory_boost = self._get_memory_boost()
            for res, boost in memory_boost.items():
                votes[res] += boost

        if len(self.history) >= 5:
            pattern_key = "".join([h["result"] for h in self.history[-5:]])
            if pattern_key in self.pattern_db:
                p = self.pattern_db[pattern_key]
                total = p[TAI] + p[XIU]
                if total > 0:
                    votes[TAI] += p[TAI] / total * 0.15
                    votes[XIU] += p[XIU] / total * 0.15

        total_votes = votes[TAI] + votes[XIU]
        if total_votes == 0:
            winner = TAI
            confidence = 50
        else:
            winner = TAI if votes[TAI] >= votes[XIU] else XIU
            confidence = int((votes[winner] / total_votes) * 100)

        confidence = min(97, max(50, confidence))

        self.last = {
            "session": self.history[-1]["session"] + 1,
            "result": winner,
            "details": details,
            "confidence": confidence
        }

        return {
            "winner": winner,
            "conf": confidence,
            "next_id": self.last["session"],
            "last": self.history[-1],
            "per_algo": per_algo,
            "tai_pct": int(votes[TAI] / total_votes * 100) if total_votes > 0 else 50,
            "xiu_pct": int(votes[XIU] / total_votes * 100) if total_votes > 0 else 50,
            "algo_count": len([a for a in per_algo if a[1] != "ERR"]),
            "memory_size": len(self.memory)
        }

    def _get_memory_boost(self):
        boost = {TAI: 0.0, XIU: 0.0}
        recent = self.memory[-20:] if len(self.memory) >= 20 else self.memory
        correct = sum(1 for m in recent if m["predicted"] == m["actual"])
        if len(recent) > 0:
            accuracy = correct / len(recent)
            if accuracy > 0.6:
                last_pred = recent[-1]["predicted"] if recent else None
                if last_pred:
                    boost[last_pred] += 0.1 * (accuracy - 0.5)
        return boost

    @property
    def wr(self):
        return round(self.stats["win"] / self.stats["total"] * 100, 1) if self.stats["total"] else 0

engine = AIEngine()

# ═══════════════════════════════════════════════════════════════════
#  BACKGROUND SYNC
# ═══════════════════════════════════════════════════════════════════
def bg_sync():
    while True:
        try:
            hist = fetch_history()
            if hist:
                engine.update(hist)
                print(f"📡 CAO FPS Sync: {len(hist)} phiên | AI Memory: {len(engine.memory)}")
        except Exception as e:
            print(f"⚠️ Sync error: {e}")
        time.sleep(SYNC_SEC)

threading.Thread(target=bg_sync, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
#  GIAO DIỆN ĐẸP
# ═══════════════════════════════════════════════════════════════════
def bar(p, w=16):
    f = int(p / 100 * w)
    return "█" * f + "░" * (w - f)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 DỰ ĐOÁN NGAY", callback_data="pred"),
         InlineKeyboardButton("📊 THỐNG KÊ", callback_data="stats")],
        [InlineKeyboardButton("🧠 AI CHI TIẾT", callback_data="algo"),
         InlineKeyboardButton("📋 LỊCH SỬ", callback_data="hist")],
        [InlineKeyboardButton("👤 TÀI KHOẢN", callback_data="account"),
         InlineKeyboardButton("⚡ TRẠNG THÁI", callback_data="status")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 KEY 7D", callback_data="mk7"),
         InlineKeyboardButton("🔑 KEY 30D", callback_data="mk30")],
        [InlineKeyboardButton("🔑 KEY 90D", callback_data="mk90"),
         InlineKeyboardButton("📋 LIST KEY", callback_data="listkeys")],
        [InlineKeyboardButton("👥 LIST USER", callback_data="listusers"),
         InlineKeyboardButton("🧠 AI MEMORY", callback_data="aimemory")],
        [InlineKeyboardButton("🔙 HOME", callback_data="home")],
    ])

def home_msg(uid):
    return (
        "╔═══════════════════════════════╗\n"
        "║   ⚡ CAO FPS PREDICTOR ⚡    ║\n"
        "║   AI 35 Thuật Toán + Học    ║\n"
        "║   Phân Tích 30-30 Phiên     ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"👤 ID: `{uid}`\n"
        f"⏰ Hết hạn: `{expire_str(uid)}`\n"
        f"🧠 Bộ nhớ AI: {len(engine.memory)} dự đoán\n"
        f"📊 Win Rate: {engine.wr}%\n\n"
        "⬇️ Chọn chức năng bên dưới:"
    )

# ═══════════════════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        home_msg(uid),
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin")
        return
    await update.message.reply_text(
        "🛡️ **CAO FPS ADMIN PANEL**\n\nChọn thao tác:",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text("🔑 Dùng: `/key FPS-XXXXXXXXXX`", parse_mode=ParseMode.MARKDOWN)
        return
    result = activate_key(uid, ctx.args[0].upper())
    await update.message.reply_text(result)

async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data in ("mk7", "mk30", "mk90"):
        if uid not in ADMIN_IDS:
            await q.edit_message_text("❌ Không có quyền")
            return
        days = {"mk7": 7, "mk30": 30, "mk90": 90}[data]
        key = gen_key(days)
        await q.edit_message_text(
            f"✅ Đã tạo key {days} ngày:\n\n`{key}`\n\nGửi user dùng: `/key {key}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "listkeys":
        if uid not in ADMIN_IDS:
            return
        lines = ["📋 **DANH SÁCH KEY**\n"]
        for k, v in list(db.get_keys().items())[-20:]:
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            used = f"✅@{v['used_by']}" if v["used_by"] else "⭕ Chưa dùng"
            lines.append(f"`{k}` — {exp} — {used}")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có key nào",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "listusers":
        if uid not in ADMIN_IDS:
            return
        lines = ["👥 **DANH SÁCH USER**\n"]
        for u, v in db.get_users().items():
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            lines.append(f"ID `{u}` — hết hạn {exp}")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có user nào",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "aimemory":
        if uid not in ADMIN_IDS:
            return
        mem = engine.memory[-20:] if engine.memory else []
        lines = ["🧠 **AI MEMORY (20 gần nhất)**\n"]
        for m in reversed(mem):
            status = "✅" if m["predicted"] == m["actual"] else "❌"
            lines.append(f"{status} #{m['session']} Dự đoán: {m['predicted']} → Thực tế: {m['actual']} | {m['confidence']}%")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có dữ liệu",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "home":
        await q.edit_message_text(
            home_msg(uid),
            reply_markup=main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not is_valid(uid):
        await q.edit_message_text(
            "🔒 **CHƯA KÍCH HOẠT / HẾT HẠN**\n\n"
            "Dùng lệnh:\n`/key FPS-XXXXXXXXXX`\n\n"
            "Liên hệ admin để mua key.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "pred":
        pred = engine.predict()
        if not pred:
            await q.edit_message_text(
                "⏳ Đang tải dữ liệu...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Thử lại", callback_data="pred")]
                ])
            )
            return

        winner_emoji = "🔴" if pred["winner"] == TAI else "🔵"
        winner_name = "TÀI" if pred["winner"] == TAI else "XỈU"

        txt = (
            f"╔══════════════════════════════╗\n"
            f"║    🎯 KẾT QUẢ DỰ ĐOÁN 🎯    ║\n"
            f"║      CAO FPS AI v3.1        ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"📌 Phiên trước : `{pred['last']['session']}` → "
            f"{'🔴 TÀI' if pred['last']['result'] == TAI else '🔵 XỈU'}\n"
            f"🎯 Phiên sau   : **{pred['next_id']}**\n\n"
            f"{'─'*30}\n"
            f"  {winner_emoji} **{winner_name}**\n"
            f"  📊 Độ tin cậy: **{pred['conf']}%**\n"
            f"{'─'*30}\n"
            f"🔴 TÀI {bar(pred['tai_pct'])} {pred['tai_pct']}%\n"
            f"🔵 XỈU {bar(pred['xiu_pct'])} {pred['xiu_pct']}%\n\n"
            f"📊 Win Rate: **{engine.wr}%** | Streak: **{engine.stats['streak']}**\n"
            f"🧠 AI Memory: **{pred['memory_size']}** dự đoán\n"
            f"⚡ Số Algo: **{pred['algo_count']}**/35\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )

        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 CẬP NHẬT", callback_data="pred"),
                 InlineKeyboardButton("🧠 CHI TIẾT", callback_data="algo")],
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "stats":
        s = engine.stats
        txt = (
            f"📊 **THỐNG KÊ CAO FPS**\n\n"
            f"✅ Thắng   : **{s['win']}**\n"
            f"❌ Thua    : **{s['loss']}**\n"
            f"📈 Tổng    : **{s['total']}**\n"
            f"🎯 Win Rate: **{engine.wr}%**\n"
            f"⚡ Streak  : **{s['streak']}**\n"
            f"🏆 Best    : **{s['best']}**\n\n"
            f"🧠 AI Memory: **{len(engine.memory)}**\n"
            f"📡 Dữ liệu  : **{len(engine.history)}** phiên\n"
            f"🤖 Số Algo  : **35**"
        )
        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="stats"),
                 InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "algo":
        pred = engine.predict()
        if not pred:
            await q.edit_message_text(
                "⏳ Chưa có dữ liệu",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return

        lines = ["🧠 **35 THUẬT TOÁN CHI TIẾT**\n"]
        lines.append(f"{'ALGO':<10} {'KQ':<6} {'CONF':>5} {'W':>4}")
        lines.append("─" * 28)

        for name, res, conf in pred["per_algo"][:20]:
            r_str = "🔴T" if res == TAI else ("🔵X" if res == XIU else "💤")
            w = engine.weights.get(name, 1.0)
            lines.append(f"{name:<10} {r_str}  {conf:>3}% {w:>4.1f}")

        lines.append("\n" + "─" * 28)
        lines.append(f"📊 Ensemble: {pred['winner']} | {pred['conf']}%")
        lines.append(f"🧠 AI Memory: {pred['memory_size']}")

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 DỰ ĐOÁN", callback_data="pred"),
                 InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "hist":
        hist = engine.history[-15:] if engine.history else []
        if not hist:
            await q.edit_message_text(
                "⏳ Chưa có lịch sử",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return

        lines = ["📋 **15 PHIÊN GẦN NHẤT**\n"]
        for h in reversed(hist):
            r = "🔴 TÀI" if h["result"] == TAI else "🔵 XỈU"
            lines.append(f"#{h['session']}  {r}")

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="hist"),
                 InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "account":
        u = db.get_users().get(str(uid))
        if uid in ADMIN_IDS:
            txt = f"🛡️ **ADMIN**\n\n📛 ID: `{uid}`\n⏰ Hết hạn: ∞"
        elif u:
            exp = datetime.fromisoformat(u["expire"])
            days_left = (exp - datetime.now()).days
            txt = (
                f"✅ **TÀI KHOẢN ACTIVE**\n\n"
                f"📛 ID: `{uid}`\n"
                f"🔑 Key: `{u['key']}`\n"
                f"⏰ Hết hạn: `{exp.strftime('%d/%m/%Y %H:%M')}`\n"
                f"📅 Còn lại: `{days_left} ngày`"
            )
        else:
            txt = (
                f"❌ **CHƯA KÍCH HOẠT**\n\n"
                f"📛 ID: `{uid}`\n\n"
                f"Dùng: `/key FPS-XXXXXXXXXX`"
            )
        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    if data == "status":
        txt = (
            f"⚡ **CAO FPS STATUS**\n\n"
            f"📡 Dữ liệu: {len(engine.history)} phiên\n"
            f"🧠 AI Memory: {len(engine.memory)} dự đoán\n"
            f"🤖 Thuật toán: 35 active\n"
            f"📊 Win Rate: {engine.wr}%\n"
            f"⚡ Streak: {engine.stats['streak']}\n"
            f"🔄 Sync: {SYNC_SEC}s\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="status"),
                 InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

async def message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.upper().startswith("FPS-"):
        await update.message.reply_text(activate_key(update.effective_user.id, txt.upper()))
    else:
        await update.message.reply_text(
            "⚡ **CAO FPS BOT**\n\n"
            "Dùng `/start` để bắt đầu\n"
            "Dùng `/key FPS-XXXX` để kích hoạt",
            parse_mode=ParseMode.MARKDOWN
        )

# ═══════════════════════════════════════════════════════════════════
#  WEB SERVER CHO RENDER
# ═══════════════════════════════════════════════════════════════════
import http.server
import socketserver

PORT = int(os.environ.get('PORT', 10000))

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"CAO FPS Bot is running!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), HealthCheckHandler) as httpd:
            print(f"🌐 Web server đang chạy trên cổng {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ Lỗi web server: {e}")

# ═══════════════════════════════════════════════════════════════════
#  MAIN - KHỞI CHẠY
# ═══════════════════════════════════════════════════════════════════
def main():
    print("═" * 50)
    print("  ⚡ CAO FPS PREDICTOR v3.1 ⚡")
    print("  35 Thuật Toán | AI Học Tăng Cường")
    print("  Web Server + Polling | Render Optimized")
    print("  HQuanz Studio")
    print("═" * 50)

    # Khởi động Web Server
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"  🌐 Web server thread đã khởi động (port {PORT})")

    # Load dữ liệu
    hist = fetch_history()
    if hist:
        engine.update(hist)
        print(f"  ✅ Loaded {len(hist)} phiên lịch sử")
        print(f"  🧠 AI Memory: {len(engine.memory)}")
        print(f"  📊 Win Rate: {engine.wr}%")

    # Khởi tạo bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("key", key))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    print("  🚀 Bot Telegram đang chạy...")

    try:
        app.run_polling()
    except Exception as e:
        print(f"❌ Lỗi bot: {e}")

if __name__ == "__main__":
    main()
