#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════
#   TOOL BACCARAT AI - ĐA SẢNH SIÊU VIP
#   Version: 5.1 | 60 Thuật Toán | Phân Tích P/B/T
#   Hỗ trợ nhiều sảnh | AI Học Tăng Cường | FIX CHỌN SẢNH
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
    LOCK_FILE = "baccarat.lock"
    fp = open(LOCK_FILE, 'w')
    fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except:
    print("⚠️ Tool Baccarat đã chạy ở instance khác! Thoát...")
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
API_URL = os.getenv("API_URL", "https://bcr-mimr.onrender.com/api/sexy")
SYNC_SEC = int(os.getenv("SYNC_SEC", "5"))
PLAYER, BANKER, TIE = "P", "B", "T"
DATA_FILE = "baccarat_data.json"

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
            "user_activity": {},
            "tables": {}
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
    
    def get_tables(self):
        return self._data.get("tables", {})
    
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
    
    def save_tables(self, tables):
        self._data["tables"] = tables
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
    key = "BAC-" + uuid.uuid4().hex[:12].upper()
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
#  FETCH API BACCARAT
# ═══════════════════════════════════════════════════════════════════
def fetch_baccarat_data():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            if data and isinstance(data, list):
                # Lưu thông tin các sảnh
                tables_info = {}
                for table in data:
                    table_name = table.get("table_name", "Unknown")
                    tables_info[table_name] = {
                        "round": table.get("round", 0),
                        "full_map": table.get("full_map", ""),
                        "result": table.get("result", ""),
                        "dealer_name": table.get("dealer_name", "")
                    }
                db.save_tables(tables_info)
                return data
    except Exception as e:
        print(f"⚠️ Lỗi fetch Baccarat API: {e}")
    return []

# ═══════════════════════════════════════════════════════════════════
#  60 THUẬT TOÁN BACCARAT
# ═══════════════════════════════════════════════════════════════════
def opp(r):
    """Đối lập Player/Banker"""
    if r == PLAYER:
        return BANKER
    elif r == BANKER:
        return PLAYER
    return TIE

# ─── THUẬT TOÁN CƠ BẢN (1-10) ──────────────────────────────────
def a1_basic(hist):
    if len(hist) < 5:
        return hist[-1] if hist else PLAYER, 60
    r = hist[-10:]
    if len(r) >= 4 and r[-1] != r[-2] and r[-2] != r[-3] and r[-3] != r[-4]:
        return opp(r[-1]), 72
    if len(r) >= 4 and r[-1] == r[-2] and r[-3] == r[-4] and r[-2] != r[-3]:
        return opp(r[-1]), 75
    if len(r) >= 3 and r[-1] == r[-2] == r[-3]:
        return r[-1], 78
    c = Counter(r[-5:])
    return max(c, key=c.get), 62

def a2_trend(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 58
    r = hist
    def trend(n):
        s = r[-n:]
        c = Counter(s)
        most = max(c, key=c.get)
        return most, c[most]/n
    s_p, s_s = trend(5)
    m_p, m_s = trend(10)
    l_p, l_s = trend(20)
    deep_p, deep_s = trend(30)
    sc = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
    for p, q, w in [(s_p, s_s, 0.4), (m_p, m_s, 0.3), (l_p, l_s, 0.2), (deep_p, deep_s, 0.1)]:
        sc[p] += q * w
    winner = max(sc, key=sc.get)
    return winner, min(92, int(60 + min(sc[winner], 0.4) * 80))

def a3_imbalance(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    if abs(p-b) >= 6:
        return BANKER if p > b else PLAYER, int(65 + (abs(p-b)-6)*3)
    return hist[-1], 55

def a4_short(hist):
    if len(hist) < 8:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-8:]
    l3 = r[-3:]
    if all(v == PLAYER for v in l3):
        return PLAYER, 76
    if all(v == BANKER for v in l3):
        return BANKER, 76
    if l3[0] == l3[1] and l3[1] != l3[2]:
        return l3[1], 70
    if l3[1] == l3[2] and l3[0] != l3[1]:
        return opp(l3[2]), 68
    c = Counter(r)
    return max(c, key=c.get), 62

def a5_weight(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-30:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    if abs(p-b) >= 10:
        return BANKER if p > b else PLAYER, int(65 + (abs(p-b)-10)*2)
    return hist[-1], 55

def a6_break(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 58
    r = hist
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
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    ratio = max(p, b) / 20
    if ratio > 0.70:
        return BANKER if p > b else PLAYER, int(65 + ratio*25)
    return hist[-1], 55

def a8_random(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    rate = chg/14
    if rate > 0.70:
        return hist[-1], 50
    return Counter(r).most_common(1)[0][0], int(68 - rate*30)

def a9_fib(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-10:]
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55][:len(r)]
    scores = {PLAYER: 0, BANKER: 0, TIE: 0}
    for i, v in enumerate(r):
        if v in scores:
            scores[v] += fib[i]
    winner = max(scores, key=scores.get)
    return winner, min(88, int(60 + (scores[winner]/(sum(scores.values())))*40 if sum(scores.values()) > 0 else 60))

def a10_prob(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = hist
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

# ─── THUẬT TOÁN NÂNG CAO (11-20) ──────────────────────────────
def a11_volatility(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-20:]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    vol = chg/19
    if vol < 0.3:
        return Counter(r).most_common(1)[0][0], int(72 + (0.3-vol)*70)
    if vol > 0.70:
        return opp(r[-1]), 62
    return Counter(r[-6:]).most_common(1)[0][0], 62

def a12_pattern(hist):
    if len(hist) < 5:
        return hist[-1] if hist else PLAYER, 58
    r = hist
    patterns = {
        ("P","B","P","B"): PLAYER, ("B","P","B","P"): BANKER,
        ("P","P","B","B"): PLAYER, ("B","B","P","P"): BANKER,
        ("P","B","B","P"): BANKER, ("B","P","P","B"): PLAYER,
        ("P","P","P","B"): BANKER, ("B","B","B","P"): PLAYER,
        ("P","B","P","P"): BANKER, ("B","P","B","B"): PLAYER,
        ("P","P","B","P"): PLAYER, ("B","B","P","B"): BANKER,
    }
    patterns3 = {
        ("P","B","P"): PLAYER, ("B","P","B"): BANKER,
        ("P","P","B"): BANKER, ("B","B","P"): PLAYER,
        ("P","B","B"): BANKER, ("B","P","P"): PLAYER,
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
        return hist[-1] if hist else PLAYER, 58
    r = hist[-25:]
    c = Counter(r)
    dom = c.most_common(1)[0][0]
    ratio = c[dom]/25
    if ratio > 0.60:
        return opp(dom), int(55 + ratio*25)
    return hist[-1], 58

def a15_follow(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 58
    r = hist
    t15 = r[-15:]
    c = Counter(t15)
    dom = c.most_common(1)[0][0]
    if c[dom]/15 > 0.45:
        return dom, int(65 + c[dom]/15*35)
    return Counter(r[-6:]).most_common(1)[0][0], 62

def a16_compbreak(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = hist
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
        return hist[-1] if hist else PLAYER, 58
    r = hist[-8:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    if p > b*2.5:
        return PLAYER, int(74 + (p-b)*2)
    if b > p*2.5:
        return BANKER, int(74 + (b-p)*2)
    return max(c, key=c.get), int(62 + abs(p-b)*5)

def a19_popular(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-35:]
    pn = {}
    pc = {}
    for i in range(len(r)-4):
        k = tuple(r[i:i+4])
        nxt = r[i+4] if i+4 < len(r) else None
        if nxt:
            pc[k] = pc.get(k, 0) + 1
            if k not in pn:
                pn[k] = {PLAYER: 0, BANKER: 0, TIE: 0}
            if nxt in pn[k]:
                pn[k][nxt] += 1
    l4 = tuple(r[-4:])
    if l4 in pn:
        p = pn[l4]
        w = max(p, key=p.get)
        total = p[PLAYER] + p[BANKER] + p[TIE]
        return w, min(90, int(60 + (p[w]/total)*35 if total > 0 else 60))
    return Counter(r[-12:]).most_common(1)[0][0], 58

def a20_ensemble(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 60
    sc = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
    for fn, w in [(a2_trend, 1.6), (a6_break, 1.4), (a19_popular, 1.3), (a16_compbreak, 1.2), (a23_entropy, 1.1)]:
        r, c = fn(hist)
        sc[r] += w * (c/100)
    total = sc[PLAYER] + sc[BANKER] + sc[TIE]
    w = max(sc, key=sc.get)
    return w, min(94, int(60 + (sc[w]/total)*40 if total > 0 else 60))

# ─── THUẬT TOÁN THỐNG KÊ (21-30) ─────────────────────────────
def a21_global(hist):
    if len(hist) < 50:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-50:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    if abs(p-b)/50 > 0.2:
        return BANKER if p > b else PLAYER, int(63 + abs(p-b)/50*42)
    return hist[-1], 55

def a22_markov2(hist):
    if len(hist) < 25:
        return hist[-1] if hist else PLAYER, 58
    r = hist
    tr = {}
    for i in range(len(r)-2):
        k = (r[i], r[i+1])
        nxt = r[i+2]
        if k not in tr:
            tr[k] = {PLAYER: 0, BANKER: 0, TIE: 0}
        if nxt in tr[k]:
            tr[k][nxt] += 1
    k2 = (r[-2], r[-1])
    if k2 in tr:
        p = tr[k2]
        total = p[PLAYER] + p[BANKER] + p[TIE]
        if total > 0:
            w = max(p, key=p.get)
            return w, min(91, int(62 + (p[w]/total)*34))
    return r[-1], 58

def a23_entropy(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-15:]
    n = len(r)
    c = Counter(r)
    ent = -sum((v/n)*log2(v/n) for v in c.values() if v > 0)
    if ent < 0.65:
        return c.most_common(1)[0][0], int(82 - ent*20)
    if ent > 0.90:
        return opp(r[-1]), 68
    return Counter(r[-6:]).most_common(1)[0][0], 62

def a24_rolling(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-20:]
    wins = [5, 7, 10, 12, 15, 20]
    scores = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
    for w in wins:
        seg = r[-w:]
        c = Counter(seg)
        for result in [PLAYER, BANKER, TIE]:
            scores[result] += c.get(result, 0) * (w/20)
    w = max(scores, key=scores.get)
    total = scores[PLAYER] + scores[BANKER] + scores[TIE]
    conf = int(55 + (scores[w]/total)*40) if total > 0 else 55
    return w, min(90, conf)

def a25_zigzag(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-12:]
    zigzag = sum(1 for i in range(2, len(r)) if r[i] != r[i-1] and r[i-1] != r[i-2])
    if zigzag >= 6:
        return opp(r[-1]), 72
    return Counter(r[-6:]).most_common(1)[0][0], 62

def a26_deepsim(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-30:]
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
    return Counter(r[-10:]).most_common(1)[0][0], 62

def a27_momentum(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-20:]
    momentum = 0
    for i in range(1, len(r)):
        if r[i] == PLAYER:
            momentum += 1
        elif r[i] == BANKER:
            momentum -= 1
    if abs(momentum) >= 6:
        return PLAYER if momentum > 0 else BANKER, int(65 + abs(momentum)*2)
    return hist[-1], 58

def a28_meanrev(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-30:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    if p/30 > 0.65:
        return BANKER, int(60 + (p/30 - 0.65)*100)
    if p/30 < 0.35:
        return PLAYER, int(60 + (0.35 - p/30)*100)
    return hist[-1], 55

def a29_rsi(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-15:]
    gains = sum(1 for i in range(1, len(r)) if r[i] == PLAYER and r[i-1] == BANKER)
    losses = sum(1 for i in range(1, len(r)) if r[i] == BANKER and r[i-1] == PLAYER)
    if gains + losses == 0:
        return r[-1], 55
    rsi = gains / (gains + losses) * 100
    if rsi > 70:
        return BANKER, int(65 + (rsi-70)*0.5)
    if rsi < 30:
        return PLAYER, int(65 + (30-rsi)*0.5)
    return r[-1], 58

def a30_macd(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-20:]]
    def sma(data, n):
        return sum(data[-n:]) / n
    ema12 = sma(r, 12)
    ema26 = sma(r, 26)
    macd = ema12 - ema26
    if macd > 0.2:
        return PLAYER, int(65 + macd*20)
    if macd < -0.2:
        return BANKER, int(65 + abs(macd)*20)
    return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 58

# ─── THUẬT TOÁN KỸ THUẬT (31-40) ─────────────────────────────
def a31_bollinger(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-20:]]
    mean = sum(r) / len(r)
    std = sqrt(sum((x - mean)**2 for x in r) / len(r))
    last = r[-1]
    if last > mean + std:
        return BANKER, int(65 + (last - mean - std)*20)
    if last < mean - std:
        return PLAYER, int(65 + (mean - std - last)*20)
    return ("P" if last > 0 else "B" if last < 0 else "T"), 58

def a32_support(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 58
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-20:]]
    highs = []
    lows = []
    for i in range(2, len(r)-2):
        if r[i] > r[i-1] and r[i] > r[i-2] and r[i] > r[i+1] and r[i] > r[i+2]:
            highs.append(r[i])
        if r[i] < r[i-1] and r[i] < r[i-2] and r[i] < r[i+1] and r[i] < r[i+2]:
            lows.append(r[i])
    if highs and r[-1] >= max(highs):
        return BANKER, 68
    if lows and r[-1] <= min(lows):
        return PLAYER, 68
    return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 58

def a33_fibretrace(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-30:]]
    high = max(r)
    low = min(r)
    diff = high - low
    if diff == 0:
        return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 55
    current = r[-1]
    fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    for level in fib_levels:
        price = high - diff * level
        if abs(current - price) / diff < 0.05:
            if current > 0:
                return PLAYER, 72
            elif current < 0:
                return BANKER, 72
    return ("P" if current > 0 else "B" if current < 0 else "T"), 58

def a34_mlsim(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = hist[-30:]
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
    return Counter(r[-10:]).most_common(1)[0][0], 60

def a35_nnsim(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 58
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-30:]]
    weights = [0.5, 0.3, 0.2, 0.1, -0.1, -0.2, -0.3, -0.5]
    weighted_sum = 0
    for i in range(min(len(weights), len(r))):
        weighted_sum += r[-(i+1)] * weights[i]
    if weighted_sum > 0.3:
        return PLAYER, int(65 + weighted_sum*20)
    if weighted_sum < -0.3:
        return BANKER, int(65 + abs(weighted_sum)*20)
    return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 58

# ─── THUẬT TOÁN ĐẶC BIỆT CHO BACCARAT (36-45) ─────────────────
def a36_pattern_PB(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-10:]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1] and r[i] != TIE and r[i-1] != TIE)
    if changes >= 7:
        return opp(r[-1]), 70
    return r[-1], 58

def a37_streak_analyzer(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    max_streak = 1
    current = 1
    for i in range(1, len(r)):
        if r[i] == r[i-1] and r[i] != TIE:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1
    if max_streak >= 5:
        return opp(r[-1]), 72
    return r[-1], 58

def a38_banker_bias(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    b = c.get(BANKER, 0)
    if b/20 > 0.55:
        return BANKER, int(65 + (b/20-0.55)*100)
    if b/20 < 0.35:
        return PLAYER, int(65 + (0.35-b/20)*100)
    return hist[-1], 55

def a39_player_bias(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    if p/20 > 0.55:
        return PLAYER, int(65 + (p/20-0.55)*100)
    if p/20 < 0.35:
        return BANKER, int(65 + (0.35-p/20)*100)
    return hist[-1], 55

def a40_tie_pattern(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    ties = r.count(TIE)
    if ties >= 3:
        last_non_tie = next((x for x in reversed(r) if x != TIE), PLAYER)
        return opp(last_non_tie), int(60 + ties*3)
    return hist[-1], 55

def a41_trend_oscillator(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    p_count = r.count(PLAYER)
    b_count = r.count(BANKER)
    if p_count > b_count:
        if p_count - b_count >= 4:
            return BANKER, 70
        return PLAYER, 62
    else:
        if b_count - p_count >= 4:
            return PLAYER, 70
        return BANKER, 62

def a42_candle_pattern(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-10:]
    if len(r) >= 3:
        if r[-3] == PLAYER and r[-2] == BANKER and r[-1] == PLAYER:
            return BANKER, 72
        if r[-3] == BANKER and r[-2] == PLAYER and r[-1] == BANKER:
            return PLAYER, 72
    return r[-1], 58

def a43_wave_analysis(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    turns = sum(1 for i in range(2, len(r)) if r[i] != r[i-1] and r[i-1] != r[i-2] and r[i] != TIE and r[i-1] != TIE)
    if turns >= 5:
        return opp(r[-1]), 68
    return r[-1], 55

def a44_parallel_streak(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    streaks = []
    current = 1
    for i in range(1, len(r)):
        if r[i] == r[i-1] and r[i] != TIE:
            current += 1
        else:
            if current >= 2:
                streaks.append((r[i-1], current))
            current = 1
    if current >= 2:
        streaks.append((r[-1], current))
    if len(streaks) >= 2:
        if streaks[-1][0] == streaks[-2][0]:
            return opp(streaks[-1][0]), 75
    return r[-1], 58

def a45_momentum_reversal(hist):
    if len(hist) < 10:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-10:]
    momentum = 0
    for i in range(1, len(r)):
        if r[i] == PLAYER:
            momentum += 1
        elif r[i] == BANKER:
            momentum -= 1
    if abs(momentum) >= 5:
        return PLAYER if momentum < 0 else BANKER, 68
    return r[-1], 55

# ─── THUẬT TOÁN AI NÂNG CAO (46-60) ────────────────────────────
def a46_pattern_boost(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
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
        return hist[-1] if hist else PLAYER, 55
    votes = {PLAYER: 0, BANKER: 0, TIE: 0}
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
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    if changes > len(r) * 0.6:
        return Counter(r[-5:]).most_common(1)[0][0], 62
    else:
        c = Counter(r[-10:])
        dom = c.most_common(1)[0][0]
        return dom, int(60 + c[dom]/len(r)*30)

def a49_neural_boost(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-20:]]
    weights = [0.3, 0.2, 0.15, 0.1, 0.08, 0.07, 0.05, 0.05]
    pred = 0
    for i in range(min(len(weights), len(r))):
        pred += r[-(i+1)] * weights[i]
    pred = pred / sum(weights[:min(len(weights), len(r))])
    if pred > 0.2:
        return PLAYER, int(65 + pred*30)
    if pred < -0.2:
        return BANKER, int(65 + abs(pred)*30)
    return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 55

def a50_trend_strength(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    strength = abs(p-b) / 20
    if strength > 0.4:
        return PLAYER if p > b else BANKER, int(65 + strength*40)
    return r[-1], 55

def a51_volatility_break(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1] and r[i] != TIE and r[i-1] != TIE)
    if changes >= 10:
        return opp(r[-1]), int(68 + (changes - 10)*2)
    return r[-1], 58

def a52_multi_timeframe(hist):
    if len(hist) < 30:
        return hist[-1] if hist else PLAYER, 55
    r = hist
    tf5 = Counter(r[-5:]).most_common(1)[0][0]
    tf10 = Counter(r[-10:]).most_common(1)[0][0]
    tf20 = Counter(r[-20:]).most_common(1)[0][0]
    if tf5 == tf10 == tf20:
        return tf5, int(65 + 10)
    return r[-1], 55

def a53_gaussian_filter(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = [1 if h == PLAYER else -1 if h == BANKER else 0 for h in hist[-15:]]
    gaussian_weights = [0.05, 0.1, 0.15, 0.2, 0.25, 0.2, 0.15, 0.1, 0.05]
    pred = 0
    for i in range(min(len(gaussian_weights), len(r))):
        pred += r[-(i+1)] * gaussian_weights[i]
    if pred > 0.2:
        return PLAYER, int(62 + pred*30)
    if pred < -0.2:
        return BANKER, int(62 + abs(pred)*30)
    return ("P" if r[-1] > 0 else "B" if r[-1] < 0 else "T"), 55

def a54_monte_carlo(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    c = Counter(r)
    p_prob = c.get(PLAYER, 0) / 20
    b_prob = c.get(BANKER, 0) / 20
    if p_prob > 0.55:
        return PLAYER, int(65 + p_prob*20)
    if b_prob > 0.55:
        return BANKER, int(65 + b_prob*20)
    return r[-1], 55

def a55_fractal(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    patterns = []
    for i in range(len(r) - 5):
        patterns.append(tuple(r[i:i+5]))
    if len(patterns) >= 2:
        last_pattern = tuple(r[-5:])
        count = sum(1 for p in patterns if p == last_pattern)
        if count >= 2:
            return r[-5], int(65 + count*5)
    return r[-1], 55

def a56_optimal_f(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    win_rate = sum(1 for i in range(1, len(r)) if r[i] == r[i-1] and r[i] != TIE) / 20
    if win_rate > 0.6:
        return r[-1], int(65 + win_rate*30)
    return r[-1], 55

def a57_risk_adjusted(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-15:]
    c = Counter(r)
    p = c.get(PLAYER, 0)
    b = c.get(BANKER, 0)
    volatility = sum(1 for i in range(1, len(r)) if r[i] != r[i-1] and r[i] != TIE and r[i-1] != TIE) / 15
    if volatility < 0.3:
        return PLAYER if p > b else BANKER, int(65 + (1-volatility)*30)
    return r[-1], 55

def a58_momentum_break(hist):
    if len(hist) < 12:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-12:]
    momentum = sum(1 for i in range(1, len(r)) if r[i] == r[i-1] and r[i] != TIE)
    if momentum >= 8:
        return opp(r[-1]), int(70 + (momentum-6)*3)
    return r[-1], 58

def a59_weighted_ensemble(hist):
    if len(hist) < 15:
        return hist[-1] if hist else PLAYER, 55
    results = []
    for fn, w in [(a2_trend, 0.3), (a6_break, 0.3), (a16_compbreak, 0.25), (a23_entropy, 0.15)]:
        try:
            res, conf = fn(hist)
            results.append((res, conf * w))
        except:
            pass
    if not results:
        return hist[-1], 55
    votes = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
    for res, weight in results:
        votes[res] += weight
    winner = max(votes, key=votes.get)
    total = votes[PLAYER] + votes[BANKER] + votes[TIE]
    conf = int(votes[winner] / total * 100) if total > 0 else 50
    return winner, min(90, conf)

def a60_adaptive_ensemble(hist):
    if len(hist) < 20:
        return hist[-1] if hist else PLAYER, 55
    r = hist[-20:]
    changes = sum(1 for i in range(1, len(r)) if r[i] != r[i-1] and r[i] != TIE and r[i-1] != TIE) / 20
    if changes > 0.5:
        res, conf = a4_short(hist)
        return res, conf
    else:
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
    ("MLSim", a34_mlsim), ("NNSim", a35_nnsim), ("PatternPB", a36_pattern_PB),
    ("Streak", a37_streak_analyzer), ("BankerBias", a38_banker_bias), ("PlayerBias", a39_player_bias),
    ("TiePattern", a40_tie_pattern), ("Oscillator", a41_trend_oscillator), ("Candle", a42_candle_pattern),
    ("Wave", a43_wave_analysis), ("Parallel", a44_parallel_streak), ("MomentumRev", a45_momentum_reversal),
    ("PatBoost", a46_pattern_boost), ("EnsVote", a47_ensemble_vote), ("AdaMoment", a48_adaptive_momentum),
    ("Neural", a49_neural_boost), ("TrendStr", a50_trend_strength), ("VolBreak", a51_volatility_break),
    ("MultiTF", a52_multi_timeframe), ("Gaussian", a53_gaussian_filter), ("MonteCarlo", a54_monte_carlo),
    ("Fractal", a55_fractal), ("OptimalF", a56_optimal_f), ("RiskAdj", a57_risk_adjusted),
    ("MomBreak", a58_momentum_break), ("WEnsemble", a59_weighted_ensemble), ("AdaEns", a60_adaptive_ensemble),
]

# ═══════════════════════════════════════════════════════════════════
#  AI ENGINE - HỌC TỪ DỰ ĐOÁN (FIX CHỌN SẢNH)
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
        self.current_table = None
        self.tables_data = {}

    def update_tables(self, data):
        """Cập nhật dữ liệu các sảnh - FIX"""
        if not data:
            return
        # Lưu dữ liệu sảnh
        self.tables_data = {}
        for table in data:
            table_name = table.get("table_name")
            if table_name:
                self.tables_data[table_name] = table
        
        db.save_tables(self.tables_data)
        
        # Cập nhật lịch sử cho sảnh đang chọn
        if self.current_table and self.current_table in self.tables_data:
            full_map = self.tables_data[self.current_table].get("full_map", "")
            if full_map:
                self.history = list(full_map)
                print(f"✅ Cập nhật sảnh {self.current_table}: {len(self.history)} ván")

    def select_table(self, table_name):
        """Chọn sảnh và cập nhật lịch sử - FIX"""
        self.current_table = table_name
        
        # Lấy từ tables_data đã lưu
        if table_name in self.tables_data:
            full_map = self.tables_data[table_name].get("full_map", "")
            if full_map:
                self.history = list(full_map)
                return True
        
        # Fallback: lấy từ database
        tables = db.get_tables()
        if table_name in tables:
            full_map = tables[table_name].get("full_map", "")
            if full_map:
                self.history = list(full_map)
                return True
        
        self.history = []
        return False

    def update_history_from_map(self, full_map, round_num):
        """Cập nhật lịch sử từ full_map"""
        if not full_map:
            return
        new_history = list(full_map)
        old_last = self.history[-1] if self.history else None
        self.history = new_history
        
        if self.last and old_last and len(self.history) > 0:
            actual = self.history[-1]
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
            pattern_key = "".join(self.history[-5:])
            if pattern_key not in self.pattern_db:
                self.pattern_db[pattern_key] = {PLAYER: 0, BANKER: 0, TIE: 0}
            if actual in self.pattern_db[pattern_key]:
                self.pattern_db[pattern_key][actual] += 1
            db.save_pattern(pattern_key, self.pattern_db[pattern_key])

    def predict(self, table_name=None):
        """Dự đoán cho sảnh cụ thể - FIX"""
        if table_name:
            self.select_table(table_name)

        if not self.history:
            return None

        votes = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
        details = {}
        per_algo = []

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
            pattern_key = "".join(self.history[-5:])
            if pattern_key in self.pattern_db:
                p = self.pattern_db[pattern_key]
                total = p[PLAYER] + p[BANKER] + p[TIE]
                if total > 0:
                    votes[PLAYER] += p[PLAYER] / total * 0.15
                    votes[BANKER] += p[BANKER] / total * 0.15
                    votes[TIE] += p[TIE] / total * 0.15

        total_votes = votes[PLAYER] + votes[BANKER] + votes[TIE]
        if total_votes == 0:
            winner = PLAYER
            confidence = 50
        else:
            winner = max(votes, key=votes.get)
            confidence = int((votes[winner] / total_votes) * 100)

        confidence = min(97, max(50, confidence))

        self.last = {
            "session": len(self.history) + 1,
            "result": winner,
            "details": details,
            "confidence": confidence
        }

        return {
            "winner": winner,
            "conf": confidence,
            "next_id": len(self.history) + 1,
            "last": self.history[-1] if self.history else None,
            "per_algo": per_algo,
            "p_pct": int(votes[PLAYER] / total_votes * 100) if total_votes > 0 else 33,
            "b_pct": int(votes[BANKER] / total_votes * 100) if total_votes > 0 else 33,
            "t_pct": int(votes[TIE] / total_votes * 100) if total_votes > 0 else 34,
            "algo_count": len([a for a in per_algo if a[1] != "ERR"]),
            "memory_size": len(self.memory)
        }

    def _get_memory_boost(self):
        boost = {PLAYER: 0.0, BANKER: 0.0, TIE: 0.0}
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
            data = fetch_baccarat_data()
            if data:
                engine.update_tables(data)
                print(f"📡 Baccarat Sync: {len(data)} sảnh | AI Memory: {len(engine.memory)}")
        except Exception as e:
            print(f"⚠️ Sync error: {e}")
        time.sleep(SYNC_SEC)

threading.Thread(target=bg_sync, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
#  GIAO DIỆN TOOL BACCARAT
# ═══════════════════════════════════════════════════════════════════
def bar(p, w=18):
    f = int(p / 100 * w)
    return "█" * f + "░" * (w - f)

def result_emoji(r):
    if r == PLAYER:
        return "🔵 PLAYER"
    elif r == BANKER:
        return "🔴 BANKER"
    return "⚪ TIE"

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 DỰ ĐOÁN NGAY", callback_data="pred"),
         InlineKeyboardButton("📊 THỐNG KÊ", callback_data="stats")],
        [InlineKeyboardButton("🧠 60 ALGOS", callback_data="algo"),
         InlineKeyboardButton("📋 LỊCH SỬ", callback_data="hist")],
        [InlineKeyboardButton("📋 DANH SÁCH SẢNH", callback_data="tables"),
         InlineKeyboardButton("👤 TÀI KHOẢN", callback_data="account")],
        [InlineKeyboardButton("⚡ TRẠNG THÁI", callback_data="status"),
         InlineKeyboardButton("🤖 AI LEARNING", callback_data="ai_learn")],
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
        "║   🔥 TOOL BACCARAT AI 🔥            ║\n"
        "║   ⚡ 60 THUẬT TOÁN SIÊU VIP ⚡      ║\n"
        "║   🧠 AI HỌC TỪ DỰ ĐOÁN             ║\n"
        "║   📊 PHÂN TÍCH ĐA SẢNH             ║\n"
        "╚═══════════════════════════════════════╝\n\n"
        f"👤 ID: `{uid}`\n"
        f"⏰ Hết hạn: `{expire_str(uid)}`\n"
        f"🧠 Bộ nhớ AI: {len(engine.memory)} dự đoán\n"
        f"📊 Win Rate: {engine.wr}%\n"
        f"⚡ Thuật toán: 60/60\n"
        f"🎯 Sảnh hiện tại: `{engine.current_table or 'Chưa chọn'}`\n\n"
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
        "🛡️ **TOOL BACCARAT ADMIN PANEL**\n\n"
        "📋 Quản lý key và người dùng:",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text("🔑 Dùng: `/key BAC-XXXXXXXXXX`", parse_mode=ParseMode.MARKDOWN)
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
            "`/delkey BAC-XXXXXXXXXX`",
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

    # ─── CHECK USER ────────────────────────────────────────────
    if not is_valid(uid):
        await q.edit_message_text(
            "🔒 **CHƯA KÍCH HOẠT / HẾT HẠN**\n\n"
            "Dùng lệnh:\n`/key BAC-XXXXXXXXXX`\n\n"
            "Liên hệ admin để mua key.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 HOME", callback_data="home")]
            ])
        )
        return

    # ─── DANH SÁCH SẢNH ────────────────────────────────────────
    if data == "tables":
        tables = db.get_tables()
        if not tables:
            # Thử fetch lại
            data = fetch_baccarat_data()
            if data:
                engine.update_tables(data)
                tables = db.get_tables()
        
        if not tables:
            await q.edit_message_text(
                "⏳ Đang tải dữ liệu sảnh...\nVui lòng thử lại sau.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="tables"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return
        
        lines = ["📋 **DANH SÁCH SẢNH BACCARAT**\n"]
        for table_name, info in list(tables.items())[:20]:
            result = info.get("result", "?")
            dealer = info.get("dealer_name", "Unknown")
            round_num = info.get("round", 0)
            emoji = "🟢" if result == PLAYER else "🔴" if result == BANKER else "⚪"
            lines.append(f"{emoji} `{table_name}` - {dealer} - Ván: {round_num} - {result_emoji(result)}")
        
        lines.append(f"\n📌 Tổng: {len(tables)} sảnh")
        lines.append("💡 Chọn sảnh để dự đoán:")
        
        keyboard = []
        for table_name in list(tables.keys())[:15]:
            keyboard.append([InlineKeyboardButton(table_name, callback_data=f"table_{table_name}")])
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="tables"),
                         InlineKeyboardButton("🏠 HOME", callback_data="home")])
        
        await q.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ─── CHỌN SẢNH - FIX ──────────────────────────────────────
    if data.startswith("table_"):
        table_name = data.replace("table_", "")
        
        # Fetch dữ liệu mới nhất
        data = fetch_baccarat_data()
        if data:
            engine.update_tables(data)
        
        # Chọn sảnh và cập nhật lịch sử
        if engine.select_table(table_name):
            # Lấy thông tin sảnh từ tables_data
            table_info = engine.tables_data.get(table_name, {})
            result = table_info.get("result", "?")
            dealer = table_info.get("dealer_name", "Unknown")
            
            await q.edit_message_text(
                f"✅ Đã chọn sảnh: **{table_name}**\n\n"
                f"🎰 Nhà cái: {dealer}\n"
                f"📊 Lịch sử: {len(engine.history)} ván\n"
                f"📌 Ván gần nhất: {result_emoji(result) if result != '?' else 'Chưa có'}\n\n"
                f"Dùng nút DỰ ĐOÁN để xem kết quả",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 DỰ ĐOÁN NGAY", callback_data="pred"),
                     InlineKeyboardButton("📋 LỊCH SỬ", callback_data="hist")],
                    [InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
        else:
            await q.edit_message_text(
                f"⚠️ Sảnh **{table_name}** chưa có dữ liệu\n"
                f"Vui lòng thử lại sau.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 DANH SÁCH SẢNH", callback_data="tables"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
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
        if not engine.current_table:
            await q.edit_message_text(
                "⚠️ **VUI LÒNG CHỌN SẢNH TRƯỚC**\n\n"
                "Dùng nút `📋 DANH SÁCH SẢNH` để chọn.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 DANH SÁCH SẢNH", callback_data="tables"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return
            
        pred = engine.predict()
        if not pred:
            await q.edit_message_text(
                "⏳ Đang tải dữ liệu...\nVui lòng thử lại sau.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Thử lại", callback_data="pred"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return

        winner_emoji = "🔵" if pred["winner"] == PLAYER else "🔴" if pred["winner"] == BANKER else "⚪"
        winner_name = "PLAYER" if pred["winner"] == PLAYER else "BANKER" if pred["winner"] == BANKER else "TIE"

        txt = (
            f"╔════════════════════════════════════╗\n"
            f"║   🔥 TOOL BACCARAT DỰ ĐOÁN 🔥     ║\n"
            f"║   ⚡ 60 THUẬT TOÁN SIÊU VIP ⚡    ║\n"
            f"╚════════════════════════════════════╝\n\n"
            f"🎯 Sảnh: **{engine.current_table}**\n"
            f"📌 Lịch sử: {len(engine.history)} ván\n"
            f"📋 Ván gần nhất: {result_emoji(pred['last']) if pred['last'] else 'Chưa có'}\n\n"
            f"{'─'*32}\n"
            f"  {winner_emoji} **{winner_name}**\n"
            f"  📊 Độ tin cậy: **{pred['conf']}%**\n"
            f"{'─'*32}\n"
            f"🔵 PLAYER {bar(pred['p_pct'])} {pred['p_pct']}%\n"
            f"🔴 BANKER {bar(pred['b_pct'])} {pred['b_pct']}%\n"
            f"⚪ TIE    {bar(pred['t_pct'])} {pred['t_pct']}%\n\n"
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
            f"📊 **THỐNG KÊ TOOL BACCARAT**\n\n"
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
            f"🔄 Learned  : **{len(engine._learned_sessions)}**\n"
            f"🎯 Sảnh     : **{engine.current_table or 'Chưa chọn'}**"
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
                "⏳ Chưa có dữ liệu\nVui lòng chọn sảnh trước.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return

        lines = ["🧠 **60 THUẬT TOÁN CHI TIẾT**\n"]
        lines.append(f"{'ALGO':<10} {'KQ':<6} {'CONF':>5} {'W':>4}")
        lines.append("─" * 28)

        for name, res, conf in pred["per_algo"]:
            r_str = "🔵P" if res == PLAYER else "🔴B" if res == BANKER else "⚪T" if res == TIE else "💤"
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
        if not engine.current_table:
            await q.edit_message_text(
                "⚠️ Vui lòng chọn sảnh trước\nDùng nút `📋 DANH SÁCH SẢNH`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 DANH SÁCH SẢNH", callback_data="tables"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return
            
        hist = engine.history[-15:] if engine.history else []
        if not hist:
            await q.edit_message_text(
                "⏳ Chưa có lịch sử cho sảnh này",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="hist"),
                     InlineKeyboardButton("🏠 HOME", callback_data="home")]
                ])
            )
            return

        lines = ["📋 **15 VÁN GẦN NHẤT**\n"]
        for i, h in enumerate(reversed(hist)):
            r = result_emoji(h)
            lines.append(f"#{len(hist)-i}  {r}")

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
                f"Dùng: `/key BAC-XXXXXXXXXX`"
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
        tables = db.get_tables()
        txt = (
            f"⚡ **TOOL BACCARAT STATUS**\n\n"
            f"📡 Dữ liệu: {len(engine.history)} ván\n"
            f"🧠 AI Memory: {len(engine.memory)} dự đoán\n"
            f"🤖 Thuật toán: 60 active\n"
            f"📊 Win Rate: {engine.wr}%\n"
            f"⚡ Streak: {engine.stats['streak']}\n"
            f"🔄 Sync: {SYNC_SEC}s\n"
            f"🎯 Accuracy: {engine.wr}%\n"
            f"🎰 Sảnh: {len(tables)} sảnh\n"
            f"📋 Sảnh hiện tại: {engine.current_table or 'Chưa chọn'}\n"
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
            "🗑️ **XÓA KEY**\n\nDùng: `/delkey BAC-XXXXXXXXXX`",
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

    if txt.upper().startswith("BAC-"):
        result = activate_key(uid, txt.upper())
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(
            "⚡ **TOOL BACCARAT AI**\n\n"
            "Dùng `/start` để bắt đầu\n"
            "Dùng `/key BAC-XXXX` để kích hoạt\n"
            "Admin: `/admin` - `/delkey`\n\n"
            "📌 Đầu tiên chọn sảnh từ nút `📋 DANH SÁCH SẢNH`",
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
        self.wfile.write(b"TOOL BACCARAT AI Bot is running!")

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
    print("  🔥 TOOL BACCARAT AI v5.1 🔥")
    print("  60 THUẬT TOÁN SIÊU VIP")
    print("  HỖ TRỢ ĐA SẢNH | AI HỌC TỰ ĐỘNG")
    print("  RENDER OPTIMIZED | HQuanz Studio")
    print("═" * 50)

    # Khởi động Web Server
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"  🌐 Web server thread đã khởi động (port {PORT})")

    # Load dữ liệu
    data = fetch_baccarat_data()
    if data:
        engine.update_tables(data)
        print(f"  ✅ Loaded {len(data)} sảnh")
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
