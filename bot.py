import os, json, requests
from flask import Flask, request, jsonify
import numpy as np
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
DATA_URL = os.environ.get('API_SUNWIN', 'https://sunlaymaynkx.hacksieucap.pro/sunlon123')

# ========== 1. LẤY DỮ LIỆU ==========
def fetch_data():
    try:
        resp = requests.get(DATA_URL, timeout=15)
        raw = resp.json()['taixiu']
        df = [{
            'phien': int(x['Phien']),
            'tong': int(x['Tong']),
            'x1': int(x['Xuc_xac_1']),
            'x2': int(x['Xuc_xac_2']),
            'x3': int(x['Xuc_xac_3']),
            'ketqua': 1 if x['Ket_qua'] == 'Tài' else 0
        } for x in raw]
        return df[::-1]
    except Exception as e:
        print('Lỗi fetch:', e)
        return []

# ========== 2. LỚP DỰ ĐOÁN ==========
class SunPredictor:
    def __init__(self):
        self.history = fetch_data()
        self.X, self.y = self.build_features() if len(self.history) > 50 else (None, None)
        self.weights = self.train_weights() if self.X is not None else None
    
    def build_features(self, n=30):
        """Xây dựng đặc trưng từ cửa sổ 30 phiên"""
        df = self.history
        X, y = [], []
        for i in range(n, len(df)-1):
            win = df[i-n:i]
            # Tính các đặc trưng từ window
            tong = [x['tong'] for x in win]
            x1 = [x['x1'] for x in win]
            x2 = [x['x2'] for x in win]
            x3 = [x['x3'] for x in win]
            ketqua = [x['ketqua'] for x in win]
            
            feats = [
                np.mean(tong),
                np.std(tong),
                sum(ketqua) / n,  # tỷ lệ Tài
                sum(1 for t in tong if t >= 11) / n,  # tỷ lệ tổng cao
                max(x1), max(x2), max(x3),
                min(x1), min(x2), min(x3),
                sum(1 for a,b,c in zip(x1,x2,x3) if a==b==c) / n,  # bộ ba
                sum(1 for t in tong if t >= 15) / n,
                tong[-1], x1[-1], x2[-1]  # giá trị hiện tại
            ]
            X.append(feats)
            y.append(df[i+1]['ketqua'])
        return np.array(X), np.array(y)
    
    def train_weights(self):
        """Huấn luyện 30 thuật toán đơn giản và gán trọng số"""
        X, y = self.X, self.y
        n = len(X)
        algos = []
        
        # ----- 30 THUẬT TOÁN (dùng X để train, dùng win để dự đoán) -----
        # 1-5: Trung bình trượt có trọng số (dùng tổng điểm)
        for w in [0.5, 0.6, 0.7, 0.8, 0.9]:
            algos.append(lambda win, w=w: 1 if np.mean([x['tong'] for x in win[-10:]]) >= 10.5*w + 5.5*(1-w) else 0)
        
        # 6-10: Tần suất Tài gần đây (5,10,15,20,25 phiên)
        for k in [5,10,15,20,25]:
            algos.append(lambda win, k=k: 1 if sum(1 for x in win[-k:] if x['ketqua']==1) >= k/2 else 0)
        
        # 11-15: Ngưỡng tổng điểm (10, 10.5, 11, 11.5, 12)
        for t in [10, 10.5, 11, 11.5, 12]:
            algos.append(lambda win, t=t: 1 if np.mean([x['tong'] for x in win[-15:]]) >= t else 0)
        
        # 16-20: Dựa trên mặt xúc xắc (x1, x2, x3)
        for idx in [1,2,3]:
            for threshold in [2, 3, 4, 5, 6]:
                algos.append(lambda win, idx=idx, th=threshold: 1 if np.mean([x[f'x{idx}'] for x in win[-10:]]) >= th else 0)
        
        # 21-25: Kết hợp xác suất Markov (độ dài chuỗi 2,3,4,5,6)
        for length in [2,3,4,5,6]:
            algos.append(lambda win, length=length: self.markov(win, length))
        
        # 26-30: Tổ hợp ngẫu nhiên có kiểm soát (dùng 5 cách kết hợp)
        for alpha in [0.1, 0.3, 0.5, 0.7, 0.9]:
            algos.append(lambda win, alpha=alpha: self.ensemble_combo(win, alpha))
        
        # Đánh giá độ chính xác trên tập huấn luyện
        accuracies = []
        for algo in algos:
            correct = 0
            for i in range(100, n):
                # Lấy window tương ứng từ history gốc
                win = self.history[i-30:i]
                pred = algo(win)
                if pred == y[i]:
                    correct += 1
            acc = correct / max(1, n-100)
            accuracies.append(acc)
        
        # Trọng số tỷ lệ với độ chính xác (làm mịn để tránh 0)
        weights = np.array(accuracies) + 0.01
        weights = weights / np.sum(weights)
        
        return {
            'algos': algos,
            'weights': weights.tolist(),
            'accuracies': accuracies
        }
    
    def markov(self, win, length):
        """Dự đoán bằng Markov: tìm chuỗi giống nhất trong quá khứ"""
        if len(win) < length:
            return 0
        # Lấy chuỗi ketqua của length phiên gần nhất
        last = tuple(x['ketqua'] for x in win[-length:])
        # Tìm trong lịch sử (bỏ qua 30 phiên cuối để tránh trùng)
        for i in range(len(self.history) - length - 30, 0, -1):
            if tuple(x['ketqua'] for x in self.history[i:i+length]) == last:
                return self.history[i+length]['ketqua']
        return 0
    
    def ensemble_combo(self, win, alpha):
        """Kết hợp trung bình trượt và tần suất"""
        ma = np.mean([x['tong'] for x in win[-10:]])
        freq = sum(1 for x in win[-10:] if x['ketqua']==1) / 10
        return 1 if (alpha * ma + (1-alpha) * freq * 11) >= 5.5 else 0
    
    def predict_all(self, latest_window):
        """Chạy 30 thuật toán trên window mới"""
        if not self.weights:
            return {'error': 'Chưa huấn luyện'}
        
        results = {}
        for i, algo in enumerate(self.weights['algos']):
            try:
                pred = algo(latest_window)
                # Đảm bảo pred là số 0 hoặc 1
                results[f'algo_{i+1}'] = float(max(0, min(1, int(pred))))
            except Exception as e:
                results[f'algo_{i+1}'] = 0.5
        
        # Ensemble có trọng số
        weighted = sum(results[f'algo_{i+1}'] * self.weights['weights'][i] 
                      for i in range(len(self.weights['algos'])))
        weighted = max(0, min(1, weighted))  # ép về [0,1]
        
        return {
            'ensemble': round(weighted, 4),
            'Tai_%': round(weighted * 100, 1),
            'Xiu_%': round(100 - weighted * 100, 1),
            'du_doan': 'Tài' if weighted > 0.5 else 'Xỉu',
            'chi_tiet': results
        }

# ========== 3. API ==========
predictor = SunPredictor()

@app.route('/')
def home():
    return jsonify({
        'message': 'Sunwin API Pro',
        'endpoints': [
            '/api/health',
            '/api/predict (POST)',
            '/api/stats',
            '/api/streak'
        ]
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'data_points': len(predictor.history),
        'trained': predictor.weights is not None
    })

@app.route('/api/predict', methods=['POST'])
def predict():
    if len(predictor.history) < 30:
        return jsonify({'error': 'Cần ít nhất 30 phiên dữ liệu'})
    latest = predictor.history[-30:]
    result = predictor.predict_all(latest)
    return jsonify(result)

@app.route('/api/stats')
def stats():
    df = predictor.history
    if not df:
        return jsonify({'error': 'No data'})
    total = len(df)
    tai = sum(1 for x in df if x['ketqua'] == 1)
    xiu = total - tai
    avg_tong = np.mean([x['tong'] for x in df])
    return jsonify({
        'total': total,
        'tai': tai,
        'xiu': xiu,
        'tai_ratio': round(tai/total, 3),
        'avg_tong': round(avg_tong, 2)
    })

@app.route('/api/streak')
def streak():
    df = predictor.history
    if not df:
        return jsonify({'error': 'No data'})
    current = df[-1]['ketqua']
    count = 0
    for x in reversed(df):
        if x['ketqua'] == current:
            count += 1
        else:
            break
    return jsonify({
        'current': 'Tài' if current == 1 else 'Xỉu',
        'streak': count
    })

# ========== 4. CHẠY SERVER ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
