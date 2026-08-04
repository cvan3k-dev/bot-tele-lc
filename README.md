# Sunwin API - 30 thuật toán dự đoán

## Deploy lên Render
1. Fork repo này
2. Tạo Web Service trên Render, chọn repo
3. Thêm biến môi trường `API_SUNWIN` (nếu cần)
4. Deploy tự động

## Cách dùng API
- `GET /api/health` → Kiểm tra
- `POST /api/predict` → Dự đoán phiên tiếp theo
- `GET /api/stats` → Thống kê tổng quan
- `GET /api/streak` → Chuỗi hiện tại

## Ví dụ kết quả dự đoán
{
  "algo_1": 0.56, "algo_2": 0.62, ..., "ensemble": 0.58,
  "Tai_%": 58.0, "Xiu_%": 42.0, "du_doan": "Tài"
}
