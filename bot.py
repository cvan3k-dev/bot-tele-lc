#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#   VAN HOA AI BOT - ALL IN ONE (NO REDIS)
#   CRE: HQuanz VIP
#   Dùng file JSON để lưu dữ liệu
# ═══════════════════════════════════════════════════════════════

import os, sys, json, time, uuid, threading, ssl, urllib.request
from datetime import datetime, timedelta
from collections import Counter
from math import log2

# ─── TELEGRAM ──────────────────────────────────────────────────
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ════════════════════════════════════════════════════════════════
#  CONFIG - ĐỔI Ở ĐÂY
# ════════════════════════════════════════════════════════════════
BOT_TOKEN   = "8774993011:AAHM3uCpCqlaOTRdOIL1mDU-JGDkdLT78sA"
ADMIN_IDS   = [5888859004]
API_URL     = "https://wtxmd52.tele68.com/v1/txmd5/sessions"
SYNC_SEC    = 6
TAI, XIU    = "T", "X"
DATA_FILE   = "vanhoa_data.json"

# ════════════════════════════════════════════════════════════════
#  FILE DATABASE (KHÔNG CẦN REDIS)
# ════════════════════════════════════════════════════════════════
class DB:
    def __init__(self):
        self._data = self._load()
    
    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"keys": {}, "users": {}, "stats": {"total": 0, "win": 0, "loss": 0, "streak": 0, "best": 0}}
    
    def _save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def get_keys(self): return self._data.get("keys", {})
    def get_users(self): return self._data.get("users", {})
    def get_stats(self): return self._data.get("stats", {"total": 0, "win": 0, "loss": 0, "streak": 0, "best": 0})
    
    def save_key(self, k, v):
        self._data["keys"][k] = v
        self._save()
    
    def save_user(self, uid, v):
        self._data["users"][str(uid)] = v
        self._save()
    
    def save_stats(self, s):
        self._data["stats"] = s
        self._save()

db = DB()

# ════════════════════════════════════════════════════════════════
#  KEY SYSTEM
# ════════════════════════════════════════════════════════════════
def gen_key(days):
    key = "VH-" + uuid.uuid4().hex[:12].upper()
    db.save_key(key, {"expire": (datetime.now() + timedelta(days=days)).isoformat(), "used_by": None})
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
    db.save_user(uid, {"key": key, "expire": k["expire"]})
    exp = datetime.fromisoformat(k["expire"]).strftime("%d/%m/%Y")
    return f"✅ Kích hoạt thành công!\n⏰ Hết hạn: {exp}"

def is_valid(uid):
    if uid in ADMIN_IDS: return True
    u = db.get_users().get(str(uid))
    return u and datetime.fromisoformat(u["expire"]) > datetime.now()

def expire_str(uid):
    if uid in ADMIN_IDS: return "∞ Admin"
    u = db.get_users().get(str(uid))
    return datetime.fromisoformat(u["expire"]).strftime("%d/%m/%Y") if u else "Chưa kích hoạt"

# ════════════════════════════════════════════════════════════════
#  FETCH API
# ════════════════════════════════════════════════════════════════
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def fetch_history():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
            d = json.loads(r.read().decode())
            if d.get("list"):
                hist = [{"session": int(i["id"]), "result": "T" if i.get("resultTruyenThong") == "TAI" else "X"} for i in d["list"]]
                hist.reverse()
                return hist
    except: pass
    return []

# ════════════════════════════════════════════════════════════════
#  23 THUẬT TOÁN
# ════════════════════════════════════════════════════════════════
def opp(r): return XIU if r == TAI else TAI

def a1(hist):
    if len(hist) < 5: return hist[-1]["result"] if hist else TAI, 60
    r = [h["result"] for h in hist]
    if len(r) >= 4 and r[-1] != r[-2] and r[-2] != r[-3] and r[-3] != r[-4]:
        return opp(r[-1]), 72
    if len(r) >= 4 and r[-1] == r[-2] and r[-3] == r[-4] and r[-2] != r[-3]:
        return opp(r[-1]), 75
    if len(r) >= 3 and r[-1] == r[-2] == r[-3]:
        return r[-1], 78
    c = Counter(r[-5:])
    return (TAI if c[TAI] > c[XIU] else XIU), 62

def a2(hist):
    if len(hist) < 10: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    def t(n):
        s = r[-n:]; c = s.count(TAI)
        return (TAI if c > n-c else XIU, abs(c-(n-c))/n)
    s_t, s_s = t(5); m_t, m_s = t(10); l_t, l_s = t(min(30, len(r)))
    sc = {TAI: 0.0, XIU: 0.0}
    for p, q, w in [(s_t, s_s, 0.5), (m_t, m_s, 0.3), (l_t, l_s, 0.2)]:
        sc[p] += q * w
    w = TAI if sc[TAI] >= sc[XIU] else XIU
    return w, min(92, int(60 + min(sc[w], 0.4) * 80))

def a3(hist):
    if len(hist) < 12: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-12:]]
    t = r.count(TAI); x = 12-t
    if abs(t-x) >= 4:
        return (XIU if t > x else TAI), int(65 + (abs(t-x)-4)*4)
    return hist[-1]["result"], 55

def a4(hist):
    if len(hist) < 6: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-6:]]
    l3 = r[-3:]
    if all(v == TAI for v in l3): return TAI, 76
    if all(v == XIU for v in l3): return XIU, 76
    if l3[0] == l3[1] and l3[1] != l3[2]: return l3[1], 70
    if l3[1] == l3[2] and l3[0] != l3[1]: return opp(l3[2]), 68
    t = r.count(TAI)
    return (TAI if t > 3 else XIU), 62

def a5(hist):
    if len(hist) < 20: return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-20:]]
    t = r.count(TAI); x = 20-t
    if abs(t-x) >= 8:
        return (XIU if t > x else TAI), int(65 + (abs(t-x)-8)*2)
    return hist[-1]["result"], 55

def a6(hist):
    if len(hist) < 5: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]; streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last: streak += 1
        else: break
    if streak >= 7: return opp(last), 82
    if streak >= 5: return opp(last), 75
    if streak >= 4: return opp(last), 68
    if streak >= 3: return last, 72
    return last, 62

def a7(hist):
    if len(hist) < 15: return hist[-1]["result"] if hist else TAI, 55
    r = [h["result"] for h in hist[-15:]]
    t = r.count(TAI); x = 15-t
    ratio = max(t,x)/15
    if ratio > 0.73:
        return (XIU if t > x else TAI), int(65 + ratio*20)
    return hist[-1]["result"], 55

def a8(hist):
    if len(hist) < 10: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-10:]]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    rate = chg/9
    if rate > 0.75: return hist[-1]["result"], 52
    return Counter(r).most_common(1)[0][0], int(68 - rate*30)

def a9(hist):
    if len(hist) < 8: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-8:]]
    fib = [1,1,2,3,5,8,13,21][:len(r)]
    tw = sum(fib[i] for i,v in enumerate(r) if v == TAI)
    xw = sum(fib[i] for i,v in enumerate(r) if v == XIU)
    w = TAI if tw >= xw else XIU
    return w, min(88, int(60 + (abs(tw-xw)/(tw+xw))*35 if tw+xw > 0 else 60))

def a10(hist):
    if len(hist) < 20: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]; streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last: streak += 1
        else: break
    brk = 0; total = 0
    for i in range(len(r)-1):
        run = 1
        for j in range(i-1, -1, -1):
            if r[j] == r[i]: run += 1
            else: break
        if run == streak and i+1 < len(r):
            total += 1
            if r[i+1] != r[i]: brk += 1
    prob = brk/total if total > 0 else 0.5
    return (opp(last) if prob > 0.55 else last), int(55 + prob*35)

def a11(hist):
    if len(hist) < 15: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-15:]]
    chg = sum(1 for i in range(1, len(r)) if r[i] != r[i-1])
    vol = chg/14
    if vol < 0.3:
        return Counter(r).most_common(1)[0][0], int(70 + (0.3-vol)*60)
    if vol > 0.75: return opp(r[-1]), 62
    c = Counter(r[-5:])
    return (TAI if c[TAI] > c[XIU] else XIU), 62

def a12(hist):
    if len(hist) < 4: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    dbp = {
        ("T","X","T","X"):TAI, ("X","T","X","T"):XIU,
        ("T","T","X","X"):TAI, ("X","X","T","T"):XIU,
        ("T","X","X","T"):XIU, ("X","T","T","X"):TAI,
        ("T","T","T","X"):XIU, ("X","X","X","T"):TAI,
        ("T","X","T","T"):XIU, ("X","T","X","X"):TAI,
    }
    db3 = {("T","X","T"):TAI, ("X","T","X"):XIU, ("T","T","X"):XIU, ("X","X","T"):TAI}
    if len(r) >= 4 and tuple(r[-4:]) in dbp: return dbp[tuple(r[-4:])], 72
    if len(r) >= 3 and tuple(r[-3:]) in db3: return db3[tuple(r[-3:])], 65
    return r[-1], 55

def a13(hist): return a2(hist)
def a14(hist):
    if len(hist) < 25: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-20:]]
    dom = Counter(r).most_common(1)[0][0]
    ratio = r.count(dom)/20
    return opp(dom) if ratio > 0.65 else hist[-1]["result"], int(55 + ratio*20)

def a15(hist):
    if len(hist) < 10: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    t10 = r[-10:]; t = t10.count(TAI); x = 10-t
    if abs(t-x)/10 > 0.5:
        return (TAI if t > x else XIU), int(65 + abs(t-x)/10*30)
    c = Counter(r[-5:])
    return c.most_common(1)[0][0], 62

def a16(hist):
    if len(hist) < 15: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    last = r[-1]; streak = 1
    for i in range(len(r)-2, -1, -1):
        if r[i] == last: streak += 1
        else: break
    sc = {opp(last): 0.0, last: 0.0}
    if streak >= 5: sc[opp(last)] += 0.4
    elif streak >= 3: sc[opp(last)] += 0.2
    else: sc[last] += 0.2
    dom = Counter(r[-10:]).most_common(1)[0][0]
    if dom == last: sc[last] += 0.3
    else: sc[opp(last)] += 0.3
    c = Counter(r[-20:]) if len(r) >= 20 else Counter(r)
    n = len(c.elements())
    ent = -sum((v/n)*log2(v/n) for v in c.values() if v > 0) if n > 0 else 1
    if ent > 0.95: sc[opp(last)] += 0.2
    else: sc[last] += 0.2
    w = max(sc, key=sc.get)
    return w, min(90, int(60 + sc[w]*40))

def a17(hist): return a15(hist)
def a18(hist):
    if len(hist) < 6: return hist[-1]["result"] if hist else TAI, 58
    s = [h["result"] for h in hist[-6:]]
    t = s.count(TAI); x = 6-t
    if t > x*2: return TAI, int(72 + (t-x)*3)
    if x > t*2: return XIU, int(72 + (x-t)*3)
    return (TAI if t > x else XIU), int(62 + abs(t-x)*4)

def a19(hist):
    if len(hist) < 30: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    pn = {}; pc = {}
    for i in range(len(r)-3):
        k = tuple(r[i:i+3]); nxt = r[i+3] if i+3 < len(r) else None
        if nxt:
            pc[k] = pc.get(k, 0) + 1
            if k not in pn: pn[k] = {TAI: 0, XIU: 0}
            pn[k][nxt] += 1
    l3 = tuple(r[-3:])
    if l3 in pn:
        p = pn[l3]
        w = TAI if p[TAI] >= p[XIU] else XIU
        return w, min(88, int(58 + (p[w]/(p[TAI]+p[XIU]))*35))
    return Counter(r[-10:]).most_common(1)[0][0], 58

def a20(hist):
    if len(hist) < 10: return hist[-1]["result"] if hist else TAI, 60
    sc = {TAI: 0.0, XIU: 0.0}
    for fn, w in [(a2, 1.5), (a6, 1.3), (a19, 1.2), (a16, 1.1)]:
        r, c = fn(hist)
        sc[r] += w * (c/100)
    w = max(sc, key=sc.get)
    return w, min(92, int(60 + (sc[w]/(sc[TAI]+sc[XIU]))*35 if sc[TAI]+sc[XIU] > 0 else 60))

def a21(hist):
    if len(hist) < 50: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-50:]]
    t = r.count(TAI); x = 50-t
    if abs(t-x)/50 > 0.2:
        return (XIU if t > x else TAI), int(62 + abs(t-x)/50*40)
    return hist[-1]["result"], 55

def a22(hist):
    if len(hist) < 20: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist]
    tr = {}
    for i in range(len(r)-2):
        k = (r[i], r[i+1]); nxt = r[i+2]
        if k not in tr: tr[k] = {TAI: 0, XIU: 0}
        tr[k][nxt] += 1
    k2 = (r[-2], r[-1])
    if k2 in tr:
        p = tr[k2]; tot = p[TAI] + p[XIU]
        if tot > 0:
            w = TAI if p[TAI] >= p[XIU] else XIU
            return w, min(90, int(60 + (p[w]/tot)*32))
    return r[-1], 58

def a23(hist):
    if len(hist) < 10: return hist[-1]["result"] if hist else TAI, 58
    r = [h["result"] for h in hist[-12:]]
    n = len(r); c = Counter(r)
    ent = -sum((v/n)*log2(v/n) for v in c.values() if v > 0)
    if ent < 0.7:
        return c.most_common(1)[0][0], int(80 - ent*15)
    if ent > 0.95: return opp(r[-1]), 65
    c5 = Counter(r[-5:])
    return (TAI if c5[TAI] > c5[XIU] else XIU), 62

ALGOS = [
    ("A01 Basic", a1), ("A02 Trend", a2), ("A03 Imbalance", a3),
    ("A04 Short", a4), ("A05 Weight", a5), ("A06 Streak", a6),
    ("A07 Rebalance", a7), ("A08 Random", a8), ("A09 Adv", a9),
    ("A10 Break", a10), ("A11 Volatility", a11), ("A12 Pattern", a12),
    ("A13 Perf", a13), ("A14 TrendBrk", a14), ("A15 Follow", a15),
    ("A16 CompBrk", a16), ("A17 Adaptive", a17), ("A18 ShortTr", a18),
    ("A19 Popular", a19), ("A20 Ensemble", a20), ("A21 Global", a21),
    ("A22 Markov2", a22), ("A23 Entropy", a23),
]

# ════════════════════════════════════════════════════════════════
#  PREDICTION ENGINE
# ════════════════════════════════════════════════════════════════
class Engine:
    def __init__(self):
        self.history = []
        self.weights = {n: 1.0 for n, _ in ALGOS}
        self.stats = db.get_stats()
        self.last = None
    
    def update(self, hist):
        if not hist: return
        old = self.history[-1]["session"] if self.history else None
        self.history = hist
        if self.last and old and hist[-1]["session"] == self.last.get("session"):
            actual = hist[-1]["result"]
            self.stats["total"] += 1
            hit = self.last["result"] == actual
            if hit:
                self.stats["win"] += 1
                self.stats["streak"] += 1
                self.stats["best"] = max(self.stats["best"], self.stats["streak"])
            else:
                self.stats["loss"] += 1
                self.stats["streak"] = 0
            for n, p in self.last.get("details", {}).items():
                if p == actual:
                    self.weights[n] = min(2.0, self.weights[n] * 1.05)
                else:
                    self.weights[n] = max(0.3, self.weights[n] * 0.96)
            db.save_stats(self.stats)
    
    def predict(self):
        if not self.history: return None
        votes = {TAI: 0.0, XIU: 0.0}
        details = {}
        per = []
        for n, fn in ALGOS:
            try:
                r, c = fn(self.history)
                votes[r] += self.weights[n] * (c/100)
                details[n] = r
                per.append((n, r, c))
            except:
                per.append((n, "ERR", 0))
        total = votes[TAI] + votes[XIU]
        w = TAI if votes[TAI] >= votes[XIU] else XIU
        conf = int((votes[w]/total)*100) if total > 0 else 50
        conf = min(97, max(55, conf))
        self.last = {"session": self.history[-1]["session"] + 1, "result": w, "details": details}
        return {
            "winner": w, "conf": conf, "next_id": self.last["session"],
            "last": self.history[-1], "per_algo": per,
            "tai_pct": int(votes[TAI]/total*100) if total > 0 else 50,
            "xiu_pct": int(votes[XIU]/total*100) if total > 0 else 50,
        }
    
    @property
    def wr(self):
        return round(self.stats["win"]/self.stats["total"]*100, 1) if self.stats["total"] else 0

engine = Engine()

# ════════════════════════════════════════════════════════════════
#  BACKGROUND SYNC
# ════════════════════════════════════════════════════════════════
def bg_sync():
    while True:
        try:
            h = fetch_history()
            if h:
                engine.update(h)
                print(f"📡 Sync: {len(h)} phiên")
        except: pass
        time.sleep(SYNC_SEC)

threading.Thread(target=bg_sync, daemon=True).start()

# ════════════════════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════════════════════
def bar(p, w=14): return "█"*int(p/100*w) + "░"*(w-int(p/100*w))

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 DỰ ĐOÁN", callback_data="pred"),
         InlineKeyboardButton("📊 THỐNG KÊ", callback_data="stats")],
        [InlineKeyboardButton("🧠 ALGO", callback_data="algo"),
         InlineKeyboardButton("📋 LỊCH SỬ", callback_data="hist")],
        [InlineKeyboardButton("🔑 TÀI KHOẢN", callback_data="account")],
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 KEY 7D", callback_data="mk7"),
         InlineKeyboardButton("🔑 KEY 30D", callback_data="mk30")],
        [InlineKeyboardButton("🔑 KEY 90D", callback_data="mk90"),
         InlineKeyboardButton("📋 LIST KEY", callback_data="listkeys")],
        [InlineKeyboardButton("👥 LIST USER", callback_data="listusers")],
        [InlineKeyboardButton("🔙 HOME", callback_data="home")],
    ])

def home_msg(uid):
    return f"⚡ VAN HOA AI\n👤 ID: `{uid}`\n⏰ Hết hạn: `{expire_str(uid)}`\n\nChọn chức năng:"

# ════════════════════════════════════════════════════════════════
#  HANDLERS
# ════════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(home_msg(update.effective_user.id), reply_markup=main_kb(), parse_mode=ParseMode.MARKDOWN)

async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền")
        return
    await update.message.reply_text("🛡️ ADMIN PANEL", reply_markup=admin_kb(), parse_mode=ParseMode.MARKDOWN)

async def key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Dùng: /key VH-XXXXXXXXXX")
        return
    await update.message.reply_text(activate_key(update.effective_user.id, ctx.args[0].upper()))

async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; data = q.data
    
    # Admin
    if data in ("mk7", "mk30", "mk90"):
        if uid not in ADMIN_IDS: await q.edit_message_text("❌ Không có quyền"); return
        days = {"mk7":7, "mk30":30, "mk90":90}[data]
        k = gen_key(days)
        await q.edit_message_text(f"✅ Key {days} ngày:\n`{k}`\n/k {k}", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())
        return
    
    if data == "listkeys":
        if uid not in ADMIN_IDS: return
        lines = ["📋 KEYS:\n"]
        for k, v in list(db.get_keys().items())[-20:]:
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            used = f"✅@{v['used_by']}" if v["used_by"] else "⭕"
            lines.append(f"`{k}` {exp} {used}")
        await q.edit_message_text("\n".join(lines) or "Trống", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())
        return
    
    if data == "listusers":
        if uid not in ADMIN_IDS: return
        lines = ["👥 USERS:\n"]
        for u, v in db.get_users().items():
            exp = datetime.fromisoformat(v["expire"]).strftime("%d/%m")
            lines.append(f"`{u}` {exp}")
        await q.edit_message_text("\n".join(lines) or "Trống", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())
        return
    
    if data == "home":
        await q.edit_message_text(home_msg(uid), reply_markup=main_kb(), parse_mode=ParseMode.MARKDOWN)
        return
    
    # Check user
    if not is_valid(uid):
        await q.edit_message_text("🔒 Chưa kích hoạt\n/key VH-XXXX", parse_mode=ParseMode.MARKDOWN, 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
        return
    
    # Predict
    if data == "pred":
        p = engine.predict()
        if not p:
            await q.edit_message_text("⏳ Đang tải...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data="pred")]]))
            return
        txt = f"⚡ DỰ ĐOÁN\n{'─'*20}\n🔮 {p['winner']} | {p['conf']}%\n📈 TÀI {bar(p['tai_pct'])} {p['tai_pct']}%\n📉 XỈU {bar(p['xiu_pct'])} {p['xiu_pct']}%\n📊 WR: {engine.wr}% | Streak: {engine.stats['streak']}"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 CẬP NHẬT", callback_data="pred"), InlineKeyboardButton("🧠 ALGO", callback_data="algo")], [InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
        return
    
    # Stats
    if data == "stats":
        s = engine.stats
        txt = f"📊 THỐNG KÊ\n✅ Thắng: {s['win']}\n❌ Thua: {s['loss']}\n📈 Tổng: {s['total']}\n🎯 WR: {engine.wr}%\n⚡ Streak: {s['streak']}"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="stats"), InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
        return
    
    # Algo
    if data == "algo":
        p = engine.predict()
        if not p:
            await q.edit_message_text("⏳ Chưa có dữ liệu", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
            return
        lines = ["🧠 ALGOS:\n"]
        for n, r, c in p["per_algo"]:
            lines.append(f"{n}: {'T' if r==TAI else 'X' if r==XIU else '?'} {c}%")
        await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 DỰ ĐOÁN", callback_data="pred"), InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
        return
    
    # History
    if data == "hist":
        h = engine.history[-15:] if engine.history else []
        if not h:
            await q.edit_message_text("⏳ Chưa có lịch sử", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
            return
        lines = ["📋 LỊCH SỬ:\n"]
        for hh in reversed(h):
            lines.append(f"#{hh['session']} {'T' if hh['result']==TAI else 'X'}")
        await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="hist"), InlineKeyboardButton("🏠 HOME", callback_data="home")]]))
        return
    
    # Account
    if data == "account":
        u = db.get_users().get(str(uid))
        if uid in ADMIN_IDS:
            txt = f"🛡️ ADMIN\nID: `{uid}`"
        elif u:
            exp = datetime.fromisoformat(u["expire"])
            txt = f"✅ ACTIVE\nID: `{uid}`\nHết hạn: {exp.strftime('%d/%m/%Y')}\nCòn: {(exp-datetime.now()).days} ngày"
        else:
            txt = f"❌ CHƯA KÍCH HOẠT\nID: `{uid}`\n/key VH-XXXX"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 HOME", callback_data="home")]]))

async def msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.upper().startswith("VH-"):
        await update.message.reply_text(activate_key(update.effective_user.id, txt.upper()))
    else:
        await update.message.reply_text("Dùng /start hoặc /key VH-XXXX")

# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════
def main():
    print("═"*40)
    print("  VAN HOA AI BOT - HQuanz VIP")
    print("  23 Algorithms | JSON File | All-in-One")
    print("═"*40)
    
    # Load initial data
    h = fetch_history()
    if h:
        engine.update(h)
        print(f"  Loaded {len(h)} phiên")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("key", key))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    
    print("  Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
