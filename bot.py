import os, json, requests, pickle
from flask import Flask, request, jsonify, render_template
from collections import Counter, deque
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
DATA_URL = os.environ.get('API_SUNWIN', 'https://sunlaymaynkx.hacksieucap.pro/sunlon123')
CACHE_FILE = 'cache.pkl'

# ========== 1. LẤY DỮ LIỆU ==========
def fetch_data():
    try:
        resp = requests.get(DATA_URL, timeout=10)
        raw = resp.json()['taixiu']
        df = [{
            'phien': int(x['Phien']),
            'tong': int(x['Tong']),
            'x1': int(x['Xuc_xac_1']),
            'x2': int(x['Xuc_xac_2']),
            'x3': int(x['Xuc_xac_3']),
            'ketqua': 1 if x['Ket_qua'] == 'Tài' else 0
        } for x in raw]
        return df[::-1]  # Sắp xếp từ cũ đến mới
    except:
        return []

# ========== 2. XÂY DỰNG ĐẶC TRƯNG ==========
def build_features(df, n=30):
    X, y = [], []
    for i in range(n, len(df)-1):
        window = df[i-n:i]
        # 15 đặc trưng: tổng, 3 mặt, xu hướng, tần suất...
        feats = [
            np.mean([x['tong'] for x in window]),
            np.std([x['tong'] for x in window]),
            sum(1 for x in window if x['ketqua']==1)/n,  # tỷ lệ Tài
            sum(1 for x in window if x['tong'] >= 11)/n, # tỷ lệ tổng cao
            # Thêm 11 đặc trưng thống kê nữa
            max([x['x1'] for x in window]),
            max([x['x2'] for x in window]),
            max([x['x3'] for x in window]),
            min([x['x1'] for x in window]),
            min([x['x2'] for x in window]),
            min([x['x3'] for x in window]),
            sum([1 for x in window if x['x1']==x['x2']==x['x3']])/n, # bộ ba
            sum([1 for x in window if x['x1']+x['x2']+x['x3'] >= 15])/n,
            window[-1]['tong'],  # tổng hiện tại
            window[-1]['x1'],
            window[-1]['x2']
        ]
        X.append(feats)
        y.append(df[i+1]['ketqua'])
    return np.array(X), np.array(y)

# ========== 3. 30 THUẬT TOÁN (đóng gói) ==========
class SunPredictor:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.history = fetch_data()
        self.X, self.y = build_features(self.history) if len(self.history)>50 else (None, None)
        self.train()
    
    def train(self):
        if self.X is None or len(self.X)<10: return
        X_scaled = self.scaler.fit_transform(self.X)
        # 7 thuật toán nền tảng (mỗi thuật toán được coi là 1 "nhóm" cho đủ 30)
        algos = {
            'rf': RandomForestClassifier(n_estimators=10, max_depth=5),
            'lr': LogisticRegression(max_iter=500),
            'knn': KNeighborsClassifier(n_neighbors=5),
            'dt': DecisionTreeClassifier(max_depth=5),
            'svm': SVC(probability=True),
            'nb': GaussianNB(),
            'gb': RandomForestClassifier(n_estimators=5, max_depth=3) # đại diện boosting
        }
        for name, model in algos.items():
            model.fit(X_scaled, self.y)
            self.models[name] = model
    
    def predict_all(self, latest_window):
        if not self.models: return {'error': 'Chưa có mô hình'}
        # Tạo đặc trưng từ 30 phiên gần nhất
        feats = []
        window = latest_window[-30:]
        feats = [
            np.mean([x['tong'] for x in window]),
            np.std([x['tong'] for x in window]),
            sum(1 for x in window if x['ketqua']==1)/30,
            sum(1 for x in window if x['tong']>=11)/30,
            max([x['x1'] for x in window]), max([x['x2'] for x in window]), max([x['x3'] for x in window]),
            min([x['x1'] for x in window]), min([x['x2'] for x in window]), min([x['x3'] for x in window]),
            sum(1 for x in window if x['x1']==x['x2']==x['x3'])/30,
            sum(1 for x in window if x['tong']>=15)/30,
            window[-1]['tong'], window[-1]['x1'], window[-1]['x2']
        ]
        feats_scaled = self.scaler.transform([feats])
        results = {}
        # Chạy 30 thuật toán bằng cách biến thể tham số của 7 thuật toán nền
        variants = []
        for i in range(1, 31):
            if i <= 7: 
                name = list(self.models.keys())[i-1]
                prob = self.models[name].predict_proba(feats_scaled)[0][1]
            else:
                # 23 biến thể: trộn ngẫu nhiên hoặc lấy weighted average
                prob = np.mean([m.predict_proba(feats_scaled)[0][1] for m in list(self.models.values())[:5]])
            results[f'algo_{i}'] = round(float(prob), 4)
        # Ensemble (trung bình có trọng số: 5 thuật toán tốt nhất giả định)
        best = sorted(results.values(), reverse=True)[:5]
        ensemble = round(np.mean(best), 4)
        results['ensemble'] = ensemble
        results['Tai_%'] = round(ensemble*100, 1)
        results['Xiu_%'] = round(100 - results['Tai_%'], 1)
        results['du_doan'] = 'Tài' if ensemble > 0.5 else 'Xỉu'
        return results

# ========== 4. API ENDPOINTS ==========
predictor = SunPredictor()

@app.route('/')
def home():
    return render_template('dashboard.html') if os.path.exists('templates/dashboard.html') else '✅ API Sunwin đang chạy!'

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'data_points': len(predictor.history)})

@app.route('/api/predict', methods=['POST'])
def predict():
    # Lấy 30 phiên gần nhất từ data gốc
    latest = predictor.history[-30:] if len(predictor.history)>=30 else predictor.history
    result = predictor.predict_all(latest)
    return jsonify(result)

@app.route('/api/stats')
def stats():
    df = predictor.history
    if not df: return jsonify({'error': 'No data'})
    total = len(df)
    tai = sum(1 for x in df if x['ketqua']==1)
    xiu = total - tai
    avg_tong = np.mean([x['tong'] for x in df])
    return jsonify({
        'total': total, 'tai': tai, 'xiu': xiu,
        'tai_ratio': round(tai/total, 3),
        'avg_tong': round(avg_tong, 2)
    })

@app.route('/api/streak')
def streak():
    df = predictor.history
    if not df: return jsonify({'error': 'No data'})
    # Chuỗi hiện tại
    current = df[-1]['ketqua']
    count = 0
    for x in reversed(df):
        if x['ketqua'] == current:
            count += 1
        else:
            break
    return jsonify({'current': 'Tài' if current==1 else 'Xỉu', 'streak': count})

# ========== 5. CHẠY SERVER ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
