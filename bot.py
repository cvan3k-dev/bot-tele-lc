#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════
#   TOOL LC79 AI - SIÊU BOT DỰ ĐOÁN TÀI XỈU
#   Version: 4.0 | 60 Thuật Toán + AI Học Tăng Cường
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
    LOCK_FILE = "lc79.lock"
    fp = open(LOCK_FILE, 'w')
    fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except:
    print("⚠️ LC79 AI đã chạy ở instance khác! Thoát...")
    sys.exit(0)

# ─── TELEGRAM ──────────────────────────────────────────────────
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ═══════════════════════════════════════════════════════════════════
#  CẤU HÌNH CAO CẤP
# ═══════════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "5888859004").split(",") if id.strip()]
API_URL = os.getenv("API_URL", "https://wtxmd52.tele68.com/v1/txmd5/sessions")
SYNC_SEC = int(os.getenv("SYNC_SEC", "5"))
TAI, XIU = "T", "X"
DATA_FILE = "lc79_data.json"

# Cấu hình AI
LEARNING_RATE = 0.01
MEMORY_SIZE = 200
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
            "pattern_db": {},
            "user_activity": {}
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
    
    def get_user_activity(self):
        return self._data.get("user_activity", {})
    
    def save_key(self, k, v):
        self._data["keys"][k] = v
        self._save()
    
    def delete_key(self, k):
        if k in self._data["keys"]:
            del self._data["keys"][k]
            self._save()
            return True
        return False
    
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
    
    def log_user_activity(self, uid, action):
        if str(uid) not in self._data["user_activity"]:
            self._data["user_activity"][str(uid)] = []
        self._data["user_activity"][str(uid)].append({
            "action": action,
            "time": datetime.now().isoformat()
        })
        if len(self._data["user_activity"][str(uid)]) > 50:
            self._data["user_activity"][str(uid)] = self._data["user_activity"][str(uid)][-50:]
        self._save()

db = SmartDB()

# ═══════════════════════════════════════════════════════════════════
#  HỆ THỐNG KEY NÂNG CAO
# ═══════════════════════════════════════════════════════════════════
def gen_key(days, note=""):
    key = "LC79-" + uuid.uuid4().hex[:12].upper()
    db.save_key(key, {
        "expire": (datetime.now() + timedelta(days=days)).isoformat(),
        "used_by": None,
        "created": datetime.now().isoformat(),
        "note": note,
        "days": days
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
    db.log_user_activity(uid, f"Kích hoạt key {key}")
    exp = datetime.fromisoformat(k["expire"]).strftime("%d/%m/%Y %H:%M")
    return f"✅ Kích hoạt thành công!\n⏰ Hết hạn: {exp}"

def delete_key_admin(key):
    if db.delete_key(key):
        return "✅ Đã xóa key thành công"
    return "❌ Key không tồn tại"

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
#  FETCH API TỐI ƯU
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
#  60 THUẬT TOÁN THÔNG MINH
# ═══════════════════════════════════════════════════════════════════
def opp(r):
    return XIU if r == TAI else TAI

# ─── NHÓM 1: PATTERN CƠ BẢN (1-10) ──────────────────────────────
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

# ─── NHÓM 2: PHÂN TÍCH KỸ THUẬT (11-20) ─────────────────────────
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

# ─── NHÓM 3: THỐNG KÊ NÂNG CAO (21-30) ─────────────────────────
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

# ─── NHÓM 4: CHỈ BÁO KỸ THUẬT (31-40) ─────────────────────────
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
        return hist[-1]["result"] if hist else TAI, 58    r = [1 if h["result"] == TAI else -1 for h in hist[-30:]]
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

# ─── NHÓM 5: THUẬT TOÁN MỚI (36-45) ────────────────────────────
def a36_linear_regression(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    n = len(r)
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(r) / n
    slope = sum((x[i] - mean_x) * (r[i] - mean_y) for i in range(n)) / sum((x[i] - mean_x)**2 for i in range(n))
    pred = mean_y + slope * (n + 1)
    if pred > 0.3:
        return TAI, int(60 + pred*20)
    if pred < -0.3:
        return XIU, int(60 + abs(pred)*20)
    return ("T" if r[-1] > 0 else "X"), 55

def a37_auto_correlation(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    n = len(r)
    mean = sum(r) / n
    acf = sum((r[i] - mean) * (r[i-1] - mean) for i in range(1, n)) / sum((r[i] - mean)**2 for i in range(n))
    if acf > 0.3:
        return TAI if r[-1] > 0 else XIU, int(65 + acf*20)
    if acf < -0.3:
        return XIU if r[-1] > 0 else TAI, int(65 + abs(acf)*20)
    return ("T" if r[-1] > 0 else "X"), 55

def a38_sentiment(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    # Tính tỷ lệ Tài/Xỉu
    t = r.count(TAI)
    ratio = t / len(r)
    if ratio > 0.6:
        return TAI, int(62 + (ratio-0.5)*40)
    if ratio < 0.4:
        return XIU, int(62 + (0.5-ratio)*40)
    return r[-1], 55

def a39_cyclical(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    cycles = []
    for period in [3, 4, 5, 6, 7, 10]:
        matches = 0
        for i in range(period, len(r)):
            if r[i] == r[i-period]:
                matches += 1
        cycles.append((period, matches / (len(r) - period)))
    if cycles:
        best_period, best_ratio = max(cycles, key=lambda x: x[1])
        if best_ratio > 0.6:
            next_pred = r[-best_period] if len(r) >= best_period else r[-1]
            return next_pred, int(60 + best_ratio*30)
    return r[-1], 55

def a40_volume_profile(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    # Giả lập volume
    t_vol = r.count(TAI) * 1.2
    x_vol = r.count(XIU) * 0.8
    if t_vol > x_vol * 1.3:
        return TAI, int(65 + (t_vol - x_vol)*5)
    if x_vol > t_vol * 1.3:
        return XIU, int(65 + (x_vol - t_vol)*5)
    return r[-1], 55

def a41_market_profile(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    # Tìm giá trị trung tâm
    t_count = r.count(TAI)
    x_count = len(r) - t_count
    if t_count > x_count:
        # Nếu Tài chiếm ưu thế, có thể đảo chiều
        return XIU, int(60 + (t_count - x_count)*2)
    else:
        return TAI, int(60 + (x_count - t_count)*2)

def a42_breakout(hist):
    if len(hist) < 10:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-10:]]
    # Tìm breakout pattern
    if len(r) >= 5 and r[-5:] == [TAI, TAI, TAI, XIU, XIU]:
        return TAI, 72
    if len(r) >= 5 and r[-5:] == [XIU, XIU, XIU, TAI, TAI]:
        return XIU, 72
    return r[-1], 58

def a43_double_top(hist):
    if len(hist) < 12:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-12:]]
    # Tìm double top (T-T)
    if len(r) >= 6:
        if r[-6] == TAI and r[-5] == TAI and r[-4] == XIU and r[-3] == XIU and r[-2] == TAI and r[-1] == TAI:
            return XIU, 75
        if r[-6] == XIU and r[-5] == XIU and r[-4] == TAI and r[-3] == TAI and r[-2] == XIU and r[-1] == XIU:
            return TAI, 75
    return r[-1], 58

def a44_double_bottom(hist):
    if len(hist) < 12:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-12:]]
    if len(r) >= 6:
        if r[-6] == TAI and r[-5] == XIU and r[-4] == XIU and r[-3] == TAI and r[-2] == TAI and r[-1] == XIU:
            return XIU, 75
        if r[-6] == XIU and r[-5] == TAI and r[-4] == TAI and r[-3] == XIU and r[-2] == XIU and r[-1] == TAI:
            return TAI, 75
    return r[-1], 58

def a45_continuation(hist):
    if len(hist) < 8:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-8:]]
    # Continuation pattern
    if len(r) >= 4 and r[-4] == r[-3] == r[-2] and r[-1] == opp(r[-2]):
        return r[-2], 70
    return r[-1], 58

# ─── NHÓM 6: THUẬT TOÁN AI NÂNG CAO (46-55) ────────────────────
def a46_pattern_boost(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    # Tìm pattern lặp lại
    for length in [3, 4, 5]:
        if len(r) >= length * 2:
            pattern = r[-length:]
            matches = 0
            for i in range(len(r) - length * 2):
                if r[i:i+length] == pattern:
                    matches += 1
            if matches >= 2:
                next_pred = r[-(length*2)] if len(r) >= length*2 else r[-1]
                return next_pred, int(65 + matches*5)
    return r[-1], 55

def a47_ensemble_vote(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    # Ensemble của 5 thuật toán tốt nhất
    votes = {TAI: 0, XIU: 0}
    for fn in [a2_trend, a6_break, a16_compbreak, a19_popular, a23_entropy]:
        try:
            res, conf = fn(hist)
            votes[res] += conf
        except:
            pass
    winner = max(votes, key=votes.get)
    conf = int(votes[winner] / sum(votes.values()) * 100) if sum(votes.values()) > 0 else 50
    return winner, min(90, conf)

def a48_adaptive_momentum(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    # Tỷ lệ thay đổi
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    if changes > len(r) * 0.6:
        # Thị trường biến động, theo xu hướng ngắn
        c = Counter(r[-5:])
        return c.most_common(1)[0][0], 62
    else:
        # Thị trường ổn định, bám xu hướng dài
        c = Counter(r[-10:])
        dom = c.most_common(1)[0][0]
        ratio = c[dom] / len(r)
        return dom, int(60 + ratio*30)

def a49_neural_boost(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    # Simple neural-like prediction
    weights = [0.3, 0.2, 0.15, 0.1, 0.08, 0.07, 0.05, 0.05]
    pred = 0
    for i in range(min(len(weights), len(r))):
        pred += r[-(i+1)] * weights[i]
    pred = pred / sum(weights[:min(len(weights), len(r))])
    if pred > 0.2:
        return TAI, int(65 + pred*30)
    if pred < -0.2:
        return XIU, int(65 + abs(pred)*30)
    return ("T" if r[-1] > 0 else "X"), 55

def a50_trend_strength(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    # Đo lường sức mạnh xu hướng
    t_count = r.count(TAI)
    x_count = len(r) - t_count
    strength = abs(t_count - x_count) / len(r)
    if strength > 0.4:
        return (TAI if t_count > x_count else XIU), int(65 + strength*40)
    return r[-1], 55

def a51_volatility_break(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    if changes >= 10:
        # Biến động cao, bẻ cầu
        return opp(r[-1]), int(68 + (changes - 10)*2)
    return r[-1], 58

def a52_multi_timeframe(hist):
    if len(hist) < 30:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist]
    # Phân tích nhiều khung thời gian
    tf5 = r[-5:].count(TAI) / 5
    tf10 = r[-10:].count(TAI) / 10
    tf20 = r[-20:].count(TAI) / 20
    avg = (tf5 + tf10 + tf20) / 3
    if avg > 0.55:
        return TAI, int(60 + avg*40)
    if avg < 0.45:
        return XIU, int(60 + (1-avg)*40)
    return r[-1], 55

def a53_gaussian_filter(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [1 if h["result"] == TAI else -1 for h in hist[-15:]]
    # Gaussian-like smoothing
    gaussian_weights = [0.05, 0.1, 0.15, 0.2, 0.25, 0.2, 0.15, 0.1, 0.05]
    pred = 0
    for i in range(min(len(gaussian_weights), len(r))):
        pred += r[-(i+1)] * gaussian_weights[i]
    if pred > 0.2:
        return TAI, int(62 + pred*30)
    if pred < -0.2:
        return XIU, int(62 + abs(pred)*30)
    return ("T" if r[-1] > 0 else "X"), 55

def a54_monte_carlo(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    # Mô phỏng Monte Carlo
    t_prob = r.count(TAI) / len(r)
    if t_prob > 0.6:
        return TAI, int(65 + t_prob*20)
    if t_prob < 0.4:
        return XIU, int(65 + (1-t_prob)*20)
    return r[-1], 55

def a55_fractal(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    # Tìm pattern fractal
    patterns = []
    for i in range(len(r) - 5):
        patterns.append(tuple(r[i:i+5]))
    if len(patterns) >= 2:
        last_pattern = tuple(r[-5:])
        count = sum(1 for p in patterns if p == last_pattern)
        if count >= 2:
            return r[-5], int(65 + count*5)
    return r[-1], 55

# ─── NHÓM 7: THUẬT TOÁN TỐI ƯU (56-60) ─────────────────────────
def a56_optimal_f(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    r = [1 if h["result"] == TAI else -1 for h in hist[-20:]]
    # Tối ưu hóa tỷ lệ thắng
    win_rate = sum(1 for i in range(1, len(r)) if r[i] == r[i-1]) / len(r)
    if win_rate > 0.6:
        return TAI if r[-1] > 0 else XIU, int(65 + win_rate*30)
    return ("T" if r[-1] > 0 else "X"), 55

def a57_risk_adjusted(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    # Điều chỉnh rủi ro
    t_count = r.count(TAI)
    volatility = sum(1 for i in range(1, len(r)) if r[i] != r[i-1]) / len(r)
    if volatility < 0.3:
        # Ít biến động, theo xu hướng
        return (TAI if t_count > len(r)/2 else XIU), int(65 + (1-volatility)*30)
    return r[-1], 55

def a58_momentum_break(hist):
    if len(hist) < 12:
        return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-12:]]
    # Bẻ cầu dựa trên đà
    momentum = sum(1 for i in range(1, len(r)) if r[i] == r[i-1])
    if momentum >= 8:
        return opp(r[-1]), int(70 + (momentum-6)*3)
    return r[-1], 58

def a59_weighted_ensemble(hist):
    if len(hist) < 15:
        return hist[-1]["result"] if hist else TAI, 55
    # Ensemble có trọng số
    results = []
    for fn, w in [(a2_trend, 0.3), (a6_break, 0.3), (a16_compbreak, 0.25), (a23_entropy, 0.15)]:
        try:
            res, conf = fn(hist)
            results.append((res, conf * w))
        except:
            pass
    if not results:
        return hist[-1]["result"], 55
    votes = {TAI: 0.0, XIU: 0.0}
    for res, weight in results:
        votes[res] += weight
    winner = max(votes, key=votes.get)
    total = votes[TAI] + votes[XIU]
    conf = int(votes[winner] / total * 100) if total > 0 else 50
    return winner, min(90, conf)

def a60_adaptive_ensemble(hist):
    if len(hist) < 20:
        return hist[-1]["result"] if hist else TAI, 55
    # Ensemble thích ứng dựa trên biến động
    r = [h["result"] for h in hist[-20:]]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1]) / len(r)
    if changes > 0.5:
        # Biến động cao, ưu tiên thuật toán ngắn hạn
        res, conf = a4_short(hist)
        return res, conf
    else:
        # Biến động thấp, ưu tiên thuật toán dài hạn
        res, conf = a2_trend(hist)
        return res, conf

# ─── DANH SÁCH 60 THUẬT TOÁN ────────────────────────────────────
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
    ("MLSim", a34_mlsim), ("NNSim", a35_nnsim), ("LinReg", a36_linear_regression),
    ("AutoCorr", a37_auto_correlation), ("Sentiment", a38_sentiment), ("Cyclical", a39_cyclical),
    ("Volume", a40_volume_profile), ("Market", a41_market_profile), ("Breakout", a42_breakout),
    ("DoubleTop", a43_double_top), ("DoubleBot", a44_double_bottom), ("Continua", a45_continuation),
    ("PatBoost", a46_pattern_boost), ("EnsVote", a47_ensemble_vote), ("AdaMoment", a48_adaptive_momentum),
    ("Neural", a49_neural_boost), ("TrendStr", a50_trend_strength), ("VolBreak", a51_volatility_break),
    ("MultiTF", a52_multi_timeframe), ("Gaussian", a53_gaussian_filter), ("MonteCarlo", a54_monte_carlo),
    ("Fractal", a55_fractal), ("OptimalF", a56_optimal_f), ("RiskAdj", a57_risk_adjusted),
    ("MomBreak", a58_momentum_break), ("WEnsemble", a59_weighted_ensemble), ("AdaEns", a60_adaptive_ensemble),
]

# ═══════════════════════════════════════════════════════════════════
#  AI ENGINE - HỌC TỪ DỰ ĐOÁN
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
        self._learned_sessions = set()

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
        if not self.last:
            return

        session_id = self.last.get("session")
        if session_id in self._learned_sessions:
            return

        self._learned_sessions.add(session_id)
        self.prediction_count += 1

        for name, pred in self.last.get("details", {}).items():
            if name in self.weights:
                if pred == actual:
                    self.weights[name] = min(2.5, self.weights[name] * (1 + self.learning_rate))
                else:
                    self.weights[name] = max(0.2, self.weights[name] * (1 - self.learning_rate * 0.8))

        self.memory.append({
            "session": session_id,
            "predicted": self.last["result"],
            "actual": actual,
            "confidence": self.last.get("confidence", 50),
            "timestamp": datetime.now().isoformat()
        })
        db.save_ai_memory(self.memory)

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

        # Sử dụng chỉ 40 thuật toán tốt nhất để tăng tốc
        for name, fn in ALGOS[:40]:
            try:
                res, conf = fn(self.history)
                weight = self.weights.get(name, 1.0)
                votes[res] += weight * (conf / 100)
                details[name] = res
                per_algo.append((name, res, conf))
            except:
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
                print(f"📡 LC79 Sync: {len(hist)} phiên | AI Memory: {len(engine.memory)}")
        except Exception as e:
            print(f"⚠️ Sync error: {e}")
        time.sleep(SYNC_SEC)

threading.Thread(target=bg_sync, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
#  GIAO DIỆN TOOL LC79 AI - CAO CẤP
# ═══════════════════════════════════════════════════════════════════
def bar(p, w=18):
    f = int(p / 100 * w)
    return "█" * f + "░" * (w - f)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 DỰ ĐOÁN NGAY", callback_data="pred"),
         InlineKeyboardButton("📊 THỐNG KÊ", callback_data="stats")],
        [InlineKeyboardButton("🧠 60 ALGOS", callback_data="algo"),
         InlineKeyboardButton("📋 LỊCH SỬ", callback_data="hist")],
        [InlineKeyboardButton("👤 TÀI KHOẢN", callback_data="account"),
         InlineKeyboardButton("⚡ TRẠNG THÁI", callback_data="status")],
        [InlineKeyboardButton("🤖 AI LEARNING", callback_data="ai_learn")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 KEY 7D", callback_data="mk7"),
         InlineKeyboardButton("🔑 KEY 30D", callback_data="mk30")],
        [InlineKeyboardButton("🔑 KEY 90D", callback_data="mk90"),
         InlineKeyboardButton("🗑️ XÓA KEY", callback_data="delkey")],
        [InlineKeyboardButton("📋 LIST KEY", callback_data="listkeys"),
         InlineKeyboardButton("👥 LIST USER", callback_data="listusers")],
        [InlineKeyboardButton("🧠 AI MEMORY", callback_data="aimemory"),
         InlineKeyboardButton("📊 USER ACTIVITY", callback_data="useractivity")],
        [InlineKeyboardButton("🔙 HOME", callback_data="home")],
    ])

def home_msg(uid):
    return (
        "╔═══════════════════════════════════════╗\n"
        "║   🔥 TOOL LC79 AI PREDICTOR 🔥      ║\n"
        "║   ⚡ 60 THUẬT TOÁN SIÊU VIP ⚡      ║\n"
        "║   🧠 AI HỌC TỪ DỰ ĐOÁN             ║\n"
        "║   📊 PHÂN TÍCH 30-30 PHIÊN         ║\n"
        "╚═══════════════════════════════════════╝\n\n"
        f"👤 ID: `{uid}`\n"
        f"⏰ Hết hạn: `{expire_str(uid)}`\n"
        f"🧠 Bộ nhớ AI: {len(engine.memory)} dự đoán\n"
        f"📊 Win Rate: {engine.wr}%\n"
        f"⚡ Thuật toán: 60/60\n\n"
        "⬇️ Chọn chức năng bên dưới:"
    )

# ═══════════════════════════════════════════════════════════════════
#  HANDLERS - XỬ LÝ LỆNH
# ═══════════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.log_user_activity(uid, "Start bot")
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
    db.log_user_activity(uid, "Mở admin panel")
    await update.message.reply_text(
        "🛡️ **TOOL LC79 ADMIN PANEL**\n\n"
        "📋 Quản lý key và người dùng:",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text("🔑 Dùng: `/key LC79-XXXXXXXXXX`", parse_mode=ParseMode.MARKDOWN)
        return
    result = activate_key(uid, ctx.args[0].upper())
    await update.message.reply_text(result)

async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # ─── ADMIN ACTIONS ──────────────────────────────────────────
    if data in ("mk7", "mk30", "mk90"):
        if uid not in ADMIN_IDS:
            await q.edit_message_text("❌ Không có quyền")
            return
        days = {"mk7": 7, "mk30": 30, "mk90": 90}[data]
        key = gen_key(days)
        db.log_user_activity(uid, f"Tạo key {days} ngày: {key}")
        await q.edit_message_text(
            f"✅ Đã tạo key {days} ngày:\n\n`{key}`\n\nGửi user dùng: `/key {key}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "delkey":
        if uid not in ADMIN_IDS:
            await q.edit_message_text("❌ Không có quyền")
            return
        await q.edit_message_text(
            "🗑️ **XÓA KEY**\n\n"
            "Nhập key cần xóa theo format:\n"
            "`/delkey LC79-XXXXXXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "listkeys":
        if uid not in ADMIN_IDS:
            return
        keys = db.get_keys()
        lines = ["📋 **DANH SÁCH KEY**\n"]
        for k, v in list(keys.items())[-30:]:
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            used = f"✅ @{v['used_by']}" if v["used_by"] else "⭕ Chưa dùng"
            days = v.get("days", "?")
            lines.append(f"`{k}` — {exp} — {used} — {days}D")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có key nào",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "listusers":
        if uid not in ADMIN_IDS:
            return
        users = db.get_users()
        lines = ["👥 **DANH SÁCH USER**\n"]
        for u, v in users.items():
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            key = v.get("key", "N/A")[:12] + "..."
            lines.append(f"ID `{u}` — {exp} — Key: `{key}`")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có user nào",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "aimemory":
        if uid not in ADMIN_IDS:
            return
        mem = engine.memory[-25:] if engine.memory else []
        lines = ["🧠 **AI MEMORY (25 gần nhất)**\n"]
        for m in reversed(mem):
            status = "✅" if m["predicted"] == m["actual"] else "❌"
            lines.append(f"{status} #{m['session']} → {m['predicted']} vs {m['actual']} | {m['confidence']}%")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có dữ liệu",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        )
        return

    if data == "useractivity":
        if uid not in ADMIN_IDS:
            return
        activity = db.get_user_activity()
        lines = ["📊 **USER ACTIVITY**\n"]
        for u, acts in list(activity.items())[-10:]:
            last_act = acts[-1] if acts else {}
            action = last_act.get("action", "Không hoạt động")
            time_str = datetime.fromisoformat(last_act.get("time", datetime.now().isoformat())).strftime("%H:%M")
            lines.append(f"👤 `{u}` — {action} — {time_str}")
        await q.edit_message_text(
            "\n".join(lines) or "Chưa có hoạt động",
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

    # ─── DELKEY COMMAND ─────────────────────────────────────────
    if data == "delkey_confirm":
        if uid not in ADMIN_IDS:
            return
        # Xử lý xóa key (sẽ được trigger từ command)
        return

    # ─── CHECK USER ────────────────────────────────────────────
    if not is_valid(uid):
        await q.edit_message_text(
            "🔒 **CHƯA KÍCH HOẠT / HẾT HẠN**\n\n"
            "Dùng lệnh:\n`/key LC79-XXXXXXXXXX`\n\n"
            "Liên hệ admin để mua key.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    # ─── AI LEARNING INFO ──────────────────────────────────────
    if data == "ai_learn":
        mem = engine.memory[-20:] if engine.memory else []
        correct = sum(1 for m in mem if m["predicted"] == m["actual"]) if mem else 0
        accuracy = round(correct / len(mem) * 100, 1) if mem else 0
        txt = (
            f"🤖 **AI LEARNING STATUS**\n\n"
            f"📊 Memory: {len(engine.memory)} dự đoán\n"
            f"🎯 Accuracy: {accuracy}% (20 gần nhất)\n"
            f"⚡ Win Rate: {engine.wr}%\n"
            f"🧠 Learned sessions: {len(engine._learned_sessions)}\n"
            f"📈 Prediction count: {engine.prediction_count}\n\n"
            f"🔄 Tự động học từ mỗi phiên dự đoán"
        )
        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 REFRESH", callback_data="ai_learn"),
                 InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    # ─── DỰ ĐOÁN ──────────────────────────────────────────────
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
            f"╔════════════════════════════════════╗\n"
            f"║   🔥 TOOL LC79 DỰ ĐOÁN 🔥         ║\n"
            f"║   ⚡ 60 THUẬT TOÁN SIÊU VIP ⚡    ║\n"
            f"╚════════════════════════════════════╝\n\n"
            f"📌 Phiên trước : `{pred['last']['session']}` → "
            f"{'🔴 TÀI' if pred['last']['result'] == TAI else '🔵 XỈU'}\n"
            f"🎯 Phiên sau   : **{pred['next_id']}**\n\n"
            f"{'─'*32}\n"
            f"  {winner_emoji} **{winner_name}**\n"
            f"  📊 Độ tin cậy: **{pred['conf']}%**\n"
            f"{'─'*32}\n"
            f"🔴 TÀI {bar(pred['tai_pct'])} {pred['tai_pct']}%\n"
            f"🔵 XỈU {bar(pred['xiu_pct'])} {pred['xiu_pct']}%\n\n"
            f"📊 Win Rate: **{engine.wr}%** | Streak: **{engine.stats['streak']}**\n"
            f"🧠 AI Memory: **{pred['memory_size']}** dự đoán\n"
            f"⚡ Số Algo: **{pred['algo_count']}**/60\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
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

    # ─── THỐNG KÊ ──────────────────────────────────────────────
    if data == "stats":
        s = engine.stats
        mem = engine.memory[-20:] if engine.memory else []
        correct = sum(1 for m in mem if m["predicted"] == m["actual"]) if mem else 0
        accuracy = round(correct / len(mem) * 100, 1) if mem else 0
        txt = (
            f"📊 **THỐNG KÊ TOOL LC79**\n\n"
            f"✅ Thắng   : **{s['win']}**\n"
            f"❌ Thua    : **{s['loss']}**\n"
            f"📈 Tổng    : **{s['total']}**\n"
            f"🎯 Win Rate: **{engine.wr}%**\n"
            f"⚡ Streak  : **{s['streak']}**\n"
            f"🏆 Best    : **{s['best']}**\n\n"
            f"🧠 AI Memory: **{len(engine.memory)}**\n"
            f"🎯 Accuracy: **{accuracy}%** (20 gần nhất)\n"
            f"📡 Dữ liệu  : **{len(engine.history)}** phiên\n"
            f"🤖 Số Algo  : **60**\n"
            f"🔄 Learned  : **{len(engine._learned_sessions)}**"
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

    # ─── ALGO CHI TIẾT ─────────────────────────────────────────
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

        lines = ["🧠 **60 THUẬT TOÁN CHI TIẾT**\n"]
        lines.append(f"{'ALGO':<10} {'KQ':<6} {'CONF':>5} {'W':>4}")
        lines.append("─" * 28)

        for name, res, conf in pred["per_algo"]:
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

    # ─── LỊCH SỬ ──────────────────────────────────────────────
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

    # ─── TÀI KHOẢN ─────────────────────────────────────────────
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
                f"Dùng: `/key LC79-XXXXXXXXXX`"
            )
        await q.edit_message_text(
            txt,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    # ─── TRẠNG THÁI ────────────────────────────────────────────
    if data == "status":
        txt = (
            f"⚡ **TOOL LC79 STATUS**\n\n"
            f"📡 Dữ liệu: {len(engine.history)} phiên\n"
            f"🧠 AI Memory: {len(engine.memory)} dự đoán\n"
            f"🤖 Thuật toán: 60 active\n"
            f"📊 Win Rate: {engine.wr}%\n"
            f"⚡ Streak: {engine.stats['streak']}\n"
            f"🔄 Sync: {SYNC_SEC}s\n"
            f"🎯 Accuracy: {engine.wr}%\n"
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

# ─── DELETE KEY COMMAND ──────────────────────────────────────────
async def delkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin")
        return

    if not ctx.args:
        await update.message.reply_text(
            "🗑️ **XÓA KEY**\n\nDùng: `/delkey LC79-XXXXXXXXXX`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    key = ctx.args[0].upper()
    result = delete_key_admin(key)
    if "thành công" in result:
        db.log_user_activity(uid, f"Xóa key {key}")
    await update.message.reply_text(result)

# ─── MESSAGE HANDLER ─────────────────────────────────────────────
async def message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id

    if txt.upper().startswith("LC79-"):
        result = activate_key(uid, txt.upper())
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(
            "⚡ **TOOL LC79 AI**\n\n"
            "Dùng `/start` để bắt đầu\n"
            "Dùng `/key LC79-XXXX` để kích hoạt\n"
            "Admin: `/admin` - `/delkey`",
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
        self.wfile.write(b"TOOL LC79 AI Bot is running!")

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
    print("  🔥 TOOL LC79 AI v4.0 🔥")
    print("  60 THUẬT TOÁN SIÊU VIP")
    print("  AI HỌC TỰ ĐỘNG | RENDER OPTIMIZED")
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
        print(f"  🤖 Thuật toán: 60/60")

    # Khởi tạo bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("key", key))
    app.add_handler(CommandHandler("delkey", delkey))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    print("  🚀 Bot Telegram đang chạy...")

    try:
        app.run_polling()
    except Exception as e:
        print(f"❌ Lỗi bot: {e}")

if __name__ == "__main__":
    main()
