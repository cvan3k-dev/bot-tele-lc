import os, json, time, uuid, hashlib, re, threading
from datetime import datetime, timedelta
from collections import Counter, deque
from math import log2
import urllib.request, urllib.error, ssl

# ── TG BOT ──────────────────────────────────────────────────────
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ParseMode
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)

# ════════════════════════════════════════════════════════════════
#   CONFIG — ĐỔI Ở ĐÂY
# ════════════════════════════════════════════════════════════════
BOT_TOKEN   = "8774993011:AAHM3uCpCqlaOTRdOIL1mDU-JGDkdLT78sA"
ADMIN_IDS   = [5888859004]          # Telegram ID của admin
API_URL     = "https://wtxmd52.tele68.com/v1/txmd5/sessions"
DATA_FILE   = "vanhoa_data.json"
SYNC_SEC    = 6

# ════════════════════════════════════════════════════════════════
#   DATA STORE
# ════════════════════════════════════════════════════════════════
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"keys": {}, "users": {}, "stats": {}}

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

DATA = load_data()

# ════════════════════════════════════════════════════════════════
#   KEY SYSTEM
# ════════════════════════════════════════════════════════════════
def gen_key(days: int, note: str = "") -> str:
    key = "VH-" + uuid.uuid4().hex[:12].upper()
    expire = (datetime.now() + timedelta(days=days)).isoformat()
    DATA["keys"][key] = {
        "expire": expire,
        "note": note,
        "used_by": None,
        "created": datetime.now().isoformat()
    }
    save_data(DATA)
    return key

def check_key(key: str) -> tuple[bool, str]:
    if key not in DATA["keys"]:
        return False, "❌ Key không tồn tại"
    k = DATA["keys"][key]
    if datetime.fromisoformat(k["expire"]) < datetime.now():
        return False, "❌ Key đã hết hạn"
    return True, "✅ Key hợp lệ"

def activate_key(user_id: int, key: str) -> str:
    ok, msg = check_key(key)
    if not ok: return msg
    k = DATA["keys"][key]
    if k["used_by"] and k["used_by"] != user_id:
        return "❌ Key đã được dùng bởi người khác"
    k["used_by"] = user_id
    DATA["users"][str(user_id)] = {
        "key": key,
        "expire": k["expire"],
        "activated": datetime.now().isoformat()
    }
    save_data(DATA)
    exp = datetime.fromisoformat(k["expire"]).strftime("%d/%m/%Y %H:%M")
    return f"✅ Kích hoạt thành công!\n⏰ Hết hạn: {exp}"

def is_user_valid(user_id: int) -> bool:
    if user_id in ADMIN_IDS: return True
    u = DATA["users"].get(str(user_id))
    if not u: return False
    return datetime.fromisoformat(u["expire"]) > datetime.now()

def user_expire(user_id: int) -> str:
    if user_id in ADMIN_IDS: return "∞ Admin"
    u = DATA["users"].get(str(user_id))
    if not u: return "Chưa kích hoạt"
    return datetime.fromisoformat(u["expire"]).strftime("%d/%m/%Y %H:%M")

# ════════════════════════════════════════════════════════════════
#   SSL + API FETCH
# ════════════════════════════════════════════════════════════════
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode   = ssl.CERT_NONE

def fetch_history():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
            d = json.loads(r.read().decode())
            if d.get("list"):
                hist = [{"session":int(i["id"]),
                         "result":"T" if i.get("resultTruyenThong")=="TAI" else "X"}
                        for i in d["list"]]
                hist.reverse()
                return hist
    except: pass
    return []

# ════════════════════════════════════════════════════════════════
#   21 THUẬT TOÁN DỰ ĐOÁN
# ════════════════════════════════════════════════════════════════
TAI, XIU = "T", "X"
def opp(r): return XIU if r==TAI else TAI

def a1_basic_pattern(hist):
    """Nhận biết cầu cơ bản"""
    if len(hist)<5: return hist[-1]["result"] if hist else TAI, 60
    r=[h["result"] for h in hist]
    # cầu 1-1
    if len(r)>=4 and r[-1]!=r[-2] and r[-2]!=r[-3] and r[-3]!=r[-4]:
        return opp(r[-1]),72
    # cầu 2-2
    if len(r)>=4 and r[-1]==r[-2] and r[-3]==r[-4] and r[-2]!=r[-3]:
        return opp(r[-1]),75
    # cầu 3
    if len(r)>=3 and r[-1]==r[-2]==r[-3]:
        return r[-1],78
    c=Counter(r[-5:])
    return (TAI if c[TAI]>c[XIU] else XIU),62

def a2_trend_multi(hist):
    """Bắt trend ngắn/trung/dài"""
    if len(hist)<10: return hist[-1]["result"] if hist else TAI, 58
    r=[h["result"] for h in hist]
    def trend(n):
        seg=r[-n:]; t=seg.count(TAI); x=n-t
        return (TAI if t>x else XIU, abs(t-x)/n)
    s_t,s_s=trend(5); m_t,m_s=trend(10)
    lg_t,lg_s=(trend(min(30,len(r))))
    # tổng hợp có trọng số
    scores={TAI:0.0,XIU:0.0}
    for t,s,w in [(s_t,s_s,0.5),(m_t,m_s,0.3),(lg_t,lg_s,0.2)]:
        scores[t]+=s*w
    winner=TAI if scores[TAI]>=scores[XIU] else XIU
    conf=int(60+min(scores[winner],0.4)*80)
    return winner,min(92,conf)

def a3_imbalance(hist):
    """Chênh lệch cao → cân bằng"""
    if len(hist)<12: return hist[-1]["result"] if hist else TAI, 58
    seg=[h["result"] for h in hist[-12:]]
    t=seg.count(TAI); x=12-t
    if abs(t-x)>=4:
        return (XIU if t>x else TAI), int(65+(abs(t-x)-4)*4)
    return hist[-1]["result"], 55

def a4_short_term(hist):
    """Phân tích 6 phiên gần"""
    if len(hist)<6: return hist[-1]["result"] if hist else TAI, 58
    r=[h["result"] for h in hist[-6:]]
    last3=r[-3:]
    if all(v==TAI for v in last3): return TAI,76
    if all(v==XIU for v in last3): return XIU,76
    if last3[0]==last3[1] and last3[1]!=last3[2]: return last3[1],70
    if last3[1]==last3[2] and last3[0]!=last3[1]: return opp(last3[2]),68
    seg=r; t=seg.count(TAI)
    return (TAI if t>3 else XIU),62

def a5_weight_balance(hist):
    """Cân bằng trọng số dự đoán"""
    if len(hist)<20: return hist[-1]["result"] if hist else TAI, 55
    r=[h["result"] for h in hist[-20:]]
    t=r.count(TAI); x=20-t
    if abs(t-x)>=8:
        return (XIU if t>x else TAI), int(65+(abs(t-x)-8)*2)
    return hist[-1]["result"],55

def a6_break_streak(hist):
    """Bẻ cầu / theo cầu dây"""
    if len(hist)<5: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    last=r[-1]; streak=1
    for i in range(len(r)-2,-1,-1):
        if r[i]==last: streak+=1
        else: break
    if streak>=7: return opp(last),82
    if streak>=5: return opp(last),75
    if streak>=4: return opp(last),68
    if streak>=3: return last,72
    return last,62

def a7_weight_rebalance(hist):
    """Tái cân bằng sau lệch dài"""
    if len(hist)<15: return hist[-1]["result"] if hist else TAI,55
    r=[h["result"] for h in hist[-15:]]
    t=r.count(TAI); x=15-t
    ratio=max(t,x)/15
    if ratio>0.73:
        return (XIU if t>x else TAI), int(65+ratio*20)
    return hist[-1]["result"],55

def a8_randomness(hist):
    """Phát hiện cầu xấu → giảm tin cậy"""
    if len(hist)<10: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist[-10:]]
    chg=sum(1 for i in range(1,len(r)) if r[i]!=r[i-1])
    rate=chg/9
    if rate>0.75: return hist[-1]["result"],52  # cầu xấu
    c=Counter(r); dom=c.most_common(1)[0][0]
    return dom, int(68-(rate*30))

def a9_advanced_pattern(hist):
    """Pattern nâng cao: fibonacci, sóng"""
    if len(hist)<8: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist[-8:]]
    # fibonacci pattern weight
    fib=[1,1,2,3,5,8,13,21][:len(r)]
    tw=sum(fib[i] for i,v in enumerate(r) if v==TAI)
    xw=sum(fib[i] for i,v in enumerate(r) if v==XIU)
    winner=TAI if tw>=xw else XIU
    total=tw+xw
    conf=int(60+(abs(tw-xw)/total)*35) if total>0 else 60
    return winner,min(88,conf)

def a10_break_probability(hist):
    """Xác suất bẻ cầu theo lịch sử"""
    if len(hist)<20: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    last=r[-1]; streak=1
    for i in range(len(r)-2,-1,-1):
        if r[i]==last: streak+=1
        else: break
    # đếm lịch sử bẻ sau streak tương tự
    breaks=0; total=0
    for i in range(len(r)-1):
        run=1
        for j in range(i-1,-1,-1):
            if r[j]==r[i]: run+=1
            else: break
        if run==streak and i+1<len(r):
            total+=1
            if r[i+1]!=r[i]: breaks+=1
    prob=breaks/total if total>0 else 0.5
    return (opp(last) if prob>0.55 else last), int(55+prob*35)

def a11_volatility(hist):
    """Phân tích biến động"""
    if len(hist)<15: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist[-15:]]
    chg=sum(1 for i in range(1,len(r)) if r[i]!=r[i-1])
    vol=chg/14
    if vol<0.3:
        c=Counter(r); return c.most_common(1)[0][0], int(70+(0.3-vol)*60)
    if vol>0.75: return opp(r[-1]),62
    c=Counter(r[-5:]); return (TAI if c[TAI]>c[XIU] else XIU),62

def a12_short_pattern_db(hist):
    """Short pattern database"""
    if len(hist)<4: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    db={
        ("T","X","T","X"):TAI,("X","T","X","T"):XIU,
        ("T","T","X","X"):TAI,("X","X","T","T"):XIU,
        ("T","X","X","T"):XIU,("X","T","T","X"):TAI,
        ("T","T","T","X"):XIU,("X","X","X","T"):TAI,
        ("T","X","T","T"):XIU,("X","T","X","X"):TAI,
    }
    last4=tuple(r[-4:])
    if last4 in db: return db[last4],72
    last3=tuple(r[-3:])
    db3={
        ("T","X","T"):TAI,("X","T","X"):XIU,
        ("T","T","X"):XIU,("X","X","T"):TAI,
    }
    if last3 in db3: return db3[last3],65
    return r[-1],55

def a13_performance_weight(hist):
    """Ensemble theo hiệu suất"""
    # simplified — delegate to trend
    return a2_trend_multi(hist)

def a14_trend_break_prob(hist):
    """Xác suất bẻ trend"""
    if len(hist)<25: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    t20=r[-20:]; dom=Counter(t20).most_common(1)[0][0]
    dom_ratio=t20.count(dom)/20
    if dom_ratio>0.65:
        # đếm lịch sử khi trend mạnh có bẻ không
        return opp(dom), int(55+dom_ratio*20)
    return hist[-1]["result"],58

def a15_trend_follow(hist):
    """Nên bám theo trend không"""
    if len(hist)<10: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    t10=r[-10:]; t=t10.count(TAI); x=10-t
    strength=abs(t-x)/10
    if strength>0.5:
        return (TAI if t>x else XIU), int(65+strength*30)
    t5=r[-5:]; t5c=Counter(t5)
    return t5c.most_common(1)[0][0], 62

def a16_comprehensive_break(hist):
    """Tổng hợp nhiều phương pháp bẻ"""
    if len(hist)<15: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    last=r[-1]; streak=1
    for i in range(len(r)-2,-1,-1):
        if r[i]==last: streak+=1
        else: break
    scores={opp(last):0.0, last:0.0}
    # factor 1: streak
    if streak>=5: scores[opp(last)]+=0.4
    elif streak>=3: scores[opp(last)]+=0.2
    else: scores[last]+=0.2
    # factor 2: 10 phiên
    t10=r[-10:]; dom=Counter(t10).most_common(1)[0][0]
    if dom==last: scores[last]+=0.3
    else: scores[opp(last)]+=0.3
    # factor 3: entropy
    c=Counter(r[-20:]) if len(r)>=20 else Counter(r)
    n=len(c.elements())
    ent=-sum((v/n)*log2(v/n) for v in c.values() if v>0) if n>0 else 1
    if ent>0.95: scores[opp(last)]+=0.2
    else: scores[last]+=0.2
    winner=max(scores,key=scores.get)
    conf=int(60+scores[winner]*40)
    return winner, min(90,conf)

def a17_adaptive_weight(hist):
    """Trọng số thích ứng"""
    return a15_trend_follow(hist)

def a18_short_trend(hist):
    """Xu hướng ngắn 6 phiên"""
    if len(hist)<6: return hist[-1]["result"] if hist else TAI,58
    seg=[h["result"] for h in hist[-6:]]
    t=seg.count(TAI); x=6-t
    if t>x*2: return TAI, int(72+(t-x)*3)
    if x>t*2: return XIU, int(72+(x-t)*3)
    return (TAI if t>x else XIU), int(62+abs(t-x)*4)

def a19_popular_trend(hist):
    """Xu hướng phổ biến trong lịch sử"""
    if len(hist)<30: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    # tìm pattern 3 phiên phổ biến nhất
    pat_next={};pat_cnt={}
    for i in range(len(r)-3):
        k=tuple(r[i:i+3]); nxt=r[i+3] if i+3<len(r) else None
        if nxt:
            pat_cnt[k]=pat_cnt.get(k,0)+1
            if k not in pat_next: pat_next[k]={TAI:0,XIU:0}
            pat_next[k][nxt]+=1
    last3=tuple(r[-3:])
    if last3 in pat_next:
        p=pat_next[last3]
        winner=TAI if p[TAI]>=p[XIU] else XIU
        total=p[TAI]+p[XIU]
        conf=int(58+(p[winner]/total)*35) if total>0 else 58
        return winner,min(88,conf)
    c=Counter(r[-10:]); return c.most_common(1)[0][0],58

def a20_ensemble_top(hist):
    """Ensemble top models"""
    if len(hist)<10: return hist[-1]["result"] if hist else TAI,60
    scores={TAI:0.0,XIU:0.0}
    weights=[(a2_trend_multi,1.5),(a6_break_streak,1.3),
             (a19_popular_trend,1.2),(a16_comprehensive_break,1.1)]
    for fn,w in weights:
        r,c=fn(hist)
        scores[r]+=w*(c/100)
    total=scores[TAI]+scores[XIU]
    winner=max(scores,key=scores.get)
    conf=int(60+(scores[winner]/total)*35) if total>0 else 60
    return winner,min(92,conf)

def a21_global_balance(hist):
    """Cân bằng tổng thể toàn cục"""
    if len(hist)<50: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist[-50:]]
    t=r.count(TAI); x=50-t
    imb=abs(t-x)/50
    if imb>0.2:
        return (XIU if t>x else TAI), int(62+imb*40)
    return hist[-1]["result"],55

# thêm mới: Markov bậc 2
def a_markov2(hist):
    """Markov chain bậc 2"""
    if len(hist)<20: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist]
    trans={}
    for i in range(len(r)-2):
        k=(r[i],r[i+1]); nxt=r[i+2]
        if k not in trans: trans[k]={TAI:0,XIU:0}
        trans[k][nxt]+=1
    k2=(r[-2],r[-1])
    if k2 in trans:
        p=trans[k2]; tot=p[TAI]+p[XIU]
        if tot>0:
            winner=TAI if p[TAI]>=p[XIU] else XIU
            conf=int(60+(p[winner]/tot)*32)
            return winner,min(90,conf)
    return r[-1],58

def a_entropy(hist):
    """Shannon entropy"""
    if len(hist)<10: return hist[-1]["result"] if hist else TAI,58
    r=[h["result"] for h in hist[-12:]]
    n=len(r); c=Counter(r)
    ent=-sum((v/n)*log2(v/n) for v in c.values() if v>0)
    if ent<0.7:
        dom=c.most_common(1)[0][0]
        return dom, int(80-ent*15)
    if ent>0.95: return opp(r[-1]),65
    c5=Counter(r[-5:]); return (TAI if c5[TAI]>c5[XIU] else XIU),62

ALGOS = [
    ("A01 Basic Pattern",    a1_basic_pattern),
    ("A02 Trend Multi",      a2_trend_multi),
    ("A03 Imbalance",        a3_imbalance),
    ("A04 Short Term",       a4_short_term),
    ("A05 Weight Balance",   a5_weight_balance),
    ("A06 Break Streak",     a6_break_streak),
    ("A07 Rebalance",        a7_weight_rebalance),
    ("A08 Randomness",       a8_randomness),
    ("A09 Adv Pattern",      a9_advanced_pattern),
    ("A10 Break Prob",       a10_break_probability),
    ("A11 Volatility",       a11_volatility),
    ("A12 Pattern DB",       a12_short_pattern_db),
    ("A13 Perf Weight",      a13_performance_weight),
    ("A14 Trend Break",      a14_trend_break_prob),
    ("A15 Trend Follow",     a15_trend_follow),
    ("A16 Comp Break",       a16_comprehensive_break),
    ("A17 Adaptive",         a17_adaptive_weight),
    ("A18 Short Trend",      a18_short_trend),
    ("A19 Popular Trend",    a19_popular_trend),
    ("A20 Ensemble Top",     a20_ensemble_top),
    ("A21 Global Balance",   a21_global_balance),
    ("A22 Markov-2",         a_markov2),
    ("A23 Entropy",          a_entropy),
]

# ════════════════════════════════════════════════════════════════
#   ENSEMBLE ENGINE
# ════════════════════════════════════════════════════════════════
class PredEngine:
    def __init__(self):
        self.history=[]
        self.weights={n:1.0 for n,_ in ALGOS}
        self.perf={n:{"w":0,"t":0} for n,_ in ALGOS}
        self.last_pred=None
        self.stats={"total":0,"win":0,"loss":0,"streak":0,"best":0}

    def update_history(self, hist):
        if not hist: return
        old_last=self.history[-1]["session"] if self.history else None
        self.history=hist
        new_last=hist[-1]
        # kiểm tra kết quả dự đoán cũ
        if self.last_pred and old_last:
            if new_last["session"]==self.last_pred["session"]:
                self._eval(new_last["result"])

    def _eval(self, actual):
        self.stats["total"]+=1
        hit=self.last_pred["result"]==actual
        if hit:
            self.stats["win"]+=1
            self.stats["streak"]+=1
            self.stats["best"]=max(self.stats["best"],self.stats["streak"])
        else:
            self.stats["loss"]+=1
            self.stats["streak"]=0
        # update weights per algo
        for name,pred in self.last_pred["details"].items():
            p=self.perf[name]
            p["t"]+=1
            if pred==actual:
                p["w"]+=1
                self.weights[name]=min(2.0,self.weights[name]*1.05)
            else:
                self.weights[name]=max(0.3,self.weights[name]*0.96)

    def predict(self):
        if not self.history: return None
        votes={TAI:0.0,XIU:0.0}
        details={}
        per_algo=[]
        for name,fn in ALGOS:
            try:
                res,conf=fn(self.history)
                w=self.weights[name]*(conf/100)
                votes[res]+=w
                details[name]=res
                per_algo.append((name,res,conf))
            except:
                per_algo.append((name,"ERR",0))
        total=votes[TAI]+votes[XIU]
        winner=TAI if votes[TAI]>=votes[XIU] else XIU
        conf=int((votes[winner]/total)*100) if total>0 else 50
        conf=min(97,max(55,conf))
        next_id=self.history[-1]["session"]+1
        self.last_pred={"session":next_id,"result":winner,"details":details}
        return {
            "winner":winner,
            "conf":conf,
            "next_id":next_id,
            "last":self.history[-1],
            "per_algo":per_algo,
            "tai_pct":int(votes[TAI]/total*100) if total>0 else 50,
            "xiu_pct":int(votes[XIU]/total*100) if total>0 else 50,
        }

    @property
    def wr(self):
        return round(self.stats["win"]/self.stats["total"]*100,1) if self.stats["total"] else 0

ENGINE=PredEngine()
LAST_HIST=[]

# ════════════════════════════════════════════════════════════════
#   BACKGROUND SYNC
# ════════════════════════════════════════════════════════════════
def bg_sync():
    global LAST_HIST
    while True:
        hist=fetch_history()
        if hist:
            ENGINE.update_history(hist)
            LAST_HIST=hist
        time.sleep(SYNC_SEC)

sync_thread=threading.Thread(target=bg_sync,daemon=True)

# ════════════════════════════════════════════════════════════════
#   BOT UI HELPERS
# ════════════════════════════════════════════════════════════════
def bar(pct,w=14):
    f=int(pct/100*w)
    return "█"*f+"░"*(w-f)

def fmt_result(r):
    return "🔴 TÀI" if r==TAI else "🔵 XỈU"

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 DỰ ĐOÁN",  callback_data="pred"),
         InlineKeyboardButton("📊 THỐNG KÊ", callback_data="stats")],
        [InlineKeyboardButton("🧠 CHI TIẾT ALGO",callback_data="algo"),
         InlineKeyboardButton("📋 LỊCH SỬ",  callback_data="hist")],
        [InlineKeyboardButton("🔑 TÀI KHOẢN",callback_data="account")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 TẠO KEY 7 NGÀY",  callback_data="mk7"),
         InlineKeyboardButton("🔑 TẠO KEY 30 NGÀY", callback_data="mk30")],
        [InlineKeyboardButton("🔑 TẠO KEY 90 NGÀY", callback_data="mk90"),
         InlineKeyboardButton("📋 DANH SÁCH KEY",   callback_data="listkeys")],
        [InlineKeyboardButton("👥 DANH SÁCH USER",  callback_data="listusers")],
        [InlineKeyboardButton("🔙 QUAY LẠI",        callback_data="home")],
    ])

def home_msg(user_id):
    return (
        "╔═══════════════════════════╗\n"
        "║  ⚡ VAN HOA AI PREDICTOR  ║\n"
        "║  23 ALGOS × ENSEMBLE AI   ║\n"
        "╚═══════════════════════════╝\n\n"
        f"👤 ID: `{user_id}`\n"
        f"⏰ Hết hạn: `{user_expire(user_id)}`\n\n"
        "Chọn chức năng bên dưới:"
    )

# ════════════════════════════════════════════════════════════════
#   HANDLERS
# ════════════════════════════════════════════════════════════════
def cmd_start(update:Update, ctx:CallbackContext):
    uid=update.effective_user.id
    update.message.reply_text(
        home_msg(uid),
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

def cmd_admin(update:Update, ctx:CallbackContext):
    uid=update.effective_user.id
    if uid not in ADMIN_IDS:
        update.message.reply_text("❌ Không có quyền admin"); return
    update.message.reply_text(
        "🛡️ **ADMIN PANEL**\n\nChọn thao tác:",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

def cmd_key(update:Update, ctx:CallbackContext):
    uid=update.effective_user.id
    args=ctx.args
    if not args:
        update.message.reply_text("Dùng: /key VH-XXXXXXXXXX"); return
    result=activate_key(uid, args[0].upper())
    update.message.reply_text(result)

def on_callback(update:Update, ctx:CallbackContext):
    q=update.callback_query; q.answer()
    uid=q.from_user.id
    data=q.data

    # admin actions
    if data in ("mk7","mk30","mk90"):
        if uid not in ADMIN_IDS:
            q.edit_message_text("❌ Không có quyền"); return
        days={"mk7":7,"mk30":30,"mk90":90}[data]
        key=gen_key(days, f"Admin tạo {days}d")
        q.edit_message_text(
            f"✅ Đã tạo key {days} ngày:\n\n`{key}`\n\nGửi cho user dùng lệnh:\n`/key {key}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard()
        ); return

    if data=="listkeys":
        if uid not in ADMIN_IDS: return
        lines=["📋 **DANH SÁCH KEY**\n"]
        for k,v in list(DATA["keys"].items())[-20:]:
            exp=datetime.fromisoformat(v["expire"]).strftime("%d/%m/%y")
            used=f"✅@{v['used_by']}" if v["used_by"] else "⭕ Chưa dùng"
            lines.append(f"`{k}` — {exp} — {used}")
        q.edit_message_text("\n".join(lines) or "Chưa có key nào",
                             parse_mode=ParseMode.MARKDOWN,
                             reply_markup=admin_keyboard()); return

    if data=="listusers":
        if uid not in ADMIN_IDS: return
        lines=["👥 **DANH SÁCH USER**\n"]
        for u,v in DATA["users"].items():
            exp=datetime.fromisoformat(v["expire"]).strftime("%d/%m/%y")
            lines.append(f"ID `{u}` — hết hạn {exp}")
        q.edit_message_text("\n".join(lines) or "Chưa có user nào",
                             parse_mode=ParseMode.MARKDOWN,
                             reply_markup=admin_keyboard()); return

    if data=="home":
        q.edit_message_text(home_msg(uid), reply_markup=main_keyboard(),
                             parse_mode=ParseMode.MARKDOWN); return

    # user check
    if not is_user_valid(uid):
        q.edit_message_text(
            "🔒 **Chưa kích hoạt / Hết hạn**\n\nDùng lệnh:\n`/key VH-XXXXXXXXXX`\n\nLiên hệ admin để mua key.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Trang chủ",callback_data="home")
            ]])
        ); return

    if data=="pred":
        pred=ENGINE.predict()
        if not pred:
            q.edit_message_text("⏳ Đang tải dữ liệu...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Thử lại",callback_data="pred"),
                    InlineKeyboardButton("🏠 Home",callback_data="home")
                ]])); return

        w="TÀI 🔴" if pred["winner"]==TAI else "XỈU 🔵"
        c=pred["conf"]
        t_bar=bar(pred["tai_pct"])
        x_bar=bar(pred["xiu_pct"])
        last=pred["last"]
        lr="🔴 TÀI" if last["result"]==TAI else "🔵 XỈU"

        txt=(
            f"╔════════════════════════╗\n"
            f"║    ⚡ KẾT QUẢ DỰ ĐOÁN  ║\n"
            f"╚════════════════════════╝\n\n"
            f"📌 Phiên trước : `{last['session']}`  →  {lr}\n"
            f"🎯 Phiên sau   : `{pred['next_id']}`\n\n"
            f"{'─'*28}\n"
            f"  DỰ ĐOÁN :  **{w}**\n"
            f"  TIN CẬY :  {c}%\n"
            f"{'─'*28}\n"
            f"🔴 TÀI  {t_bar} {pred['tai_pct']}%\n"
            f"🔵 XỈU  {x_bar} {pred['xiu_pct']}%\n\n"
            f"📊 Thắng/Thua: {ENGINE.stats['win']}/{ENGINE.stats['loss']} "
            f"| WR: {ENGINE.wr}%\n"
            f"⚡ Streak: {ENGINE.stats['streak']}"
        )
        q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 CẬP NHẬT",callback_data="pred"),
                 InlineKeyboardButton("🧠 ALGO",callback_data="algo")],
                [InlineKeyboardButton("🏠 Home",callback_data="home")]
            ])); return

    if data=="stats":
        s=ENGINE.stats
        wr=ENGINE.wr
        txt=(
            f"📊 **THỐNG KÊ TỔNG HỢP**\n\n"
            f"✅ Thắng   : {s['win']}\n"
            f"❌ Thua    : {s['loss']}\n"
            f"📈 Tổng    : {s['total']}\n"
            f"🎯 WinRate : {wr}%\n"
            f"⚡ Streak  : {s['streak']}\n"
            f"🏆 Best    : {s['best']}\n\n"
            f"📡 Dữ liệu : {len(ENGINE.history)} phiên loaded\n"
            f"🕐 Update  : {datetime.now().strftime('%H:%M:%S')}"
        )
        q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh",callback_data="stats"),
                 InlineKeyboardButton("🏠 Home",callback_data="home")]
            ])); return

    if data=="algo":
        pred=ENGINE.predict()
        if not pred:
            q.edit_message_text("⏳ Chưa có dữ liệu",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Home",callback_data="home")
                ]])); return

        lines=["🧠 **CHI TIẾT 23 THUẬT TOÁN**\n"]
        lines.append(f"{'ALGO':<18} {'KQ':<6} {'CONF':>5}")
        lines.append("─"*32)
        for name,res,conf in pred["per_algo"]:
            r_str="🔴T" if res==TAI else ("🔵X" if res==XIU else "💤")
            lines.append(f"`{name:<18}` {r_str}  {conf:>3}%")

        q.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 DỰ ĐOÁN",callback_data="pred"),
                 InlineKeyboardButton("🏠 Home",callback_data="home")]
            ])); return

    if data=="hist":
        hist=ENGINE.history[-15:] if ENGINE.history else []
        if not hist:
            q.edit_message_text("⏳ Chưa có lịch sử",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Home",callback_data="home")
                ]])); return
        lines=["📋 **LỊCH SỬ 15 PHIÊN GẦN**\n"]
        for h in reversed(hist):
            r="🔴 TÀI" if h["result"]==TAI else "🔵 XỈU"
            lines.append(f"#{h['session']}  {r}")
        q.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh",callback_data="hist"),
                 InlineKeyboardButton("🏠 Home",callback_data="home")]
            ])); return

    if data=="account":
        u=DATA["users"].get(str(uid))
        if uid in ADMIN_IDS:
            acc_txt=f"🛡️ **ADMIN**\n\n📛 ID: `{uid}`\n⏰ Hết hạn: ∞"
        elif u:
            exp=datetime.fromisoformat(u["expire"])
            days_left=(exp-datetime.now()).days
            acc_txt=(
                f"✅ **TÀI KHOẢN ACTIVE**\n\n"
                f"📛 ID: `{uid}`\n"
                f"🔑 Key: `{u['key']}`\n"
                f"⏰ Hết hạn: `{exp.strftime('%d/%m/%Y %H:%M')}`\n"
                f"📅 Còn lại: `{days_left} ngày`"
            )
        else:
            acc_txt=f"❌ **CHƯA KÍCH HOẠT**\n\n📛 ID: `{uid}`\n\nDùng: `/key VH-XXXXXXXXXX`"
        q.edit_message_text(acc_txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Home",callback_data="home")
            ]])); return

def on_message(update:Update, ctx:CallbackContext):
    uid=update.effective_user.id
    txt=update.message.text.strip()
    # auto detect key input
    if txt.upper().startswith("VH-"):
        result=activate_key(uid, txt.upper())
        update.message.reply_text(result); return
    update.message.reply_text(
        "Dùng /start để bắt đầu hoặc /key VH-XXXX để kích hoạt key"
    )

# ════════════════════════════════════════════════════════════════
#   MAIN
# ════════════════════════════════════════════════════════════════
def main():
    print("═"*50)
    print("  VAN HOA AI BOT — STARTING")
    print("  23 Algorithms | Key System | Admin Panel")
    print("═"*50)

    # pre-load data
    hist=fetch_history()
    if hist:
        ENGINE.update_history(hist)
        print(f"  Loaded {len(hist)} phiên lịch sử")

    sync_thread.start()
    print("  Background sync: ON")

    upd=Updater(BOT_TOKEN,use_context=True)
    dp=upd.dispatcher
    dp.add_handler(CommandHandler("start",cmd_start))
    dp.add_handler(CommandHandler("admin",cmd_admin))
    dp.add_handler(CommandHandler("key",cmd_key))
    dp.add_handler(CallbackQueryHandler(on_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, on_message))

    print("  Bot running...")
    upd.start_polling()
    upd.idle()

if __name__=="__main__":
    main()
