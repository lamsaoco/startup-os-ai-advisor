# 🚀 Hướng dẫn Setup — Startup OS AI Advisor

> Áp dụng cho: Ubuntu 22.04/24.04 mới toanh, chưa cài gì.

---

## ⚠️ Những thứ KHÔNG được commit lên Git

Các file/thư mục dưới đây đã được liệt kê trong `.gitignore` và **tuyệt đối không push lên repository**:

| File / Thư mục | Lý do |
|---|---|
| `.env` | Chứa API keys, credentials — bí mật tuyệt đối |
| `data/` | Chứa file JSON tạm + ONNX model ~900MB |
| `data/.model_cache/` | Model HuggingFace (~900MB, dùng Git LFS nếu cần) |
| `data/bronze/` | File crawl tạm, tự xóa sau mỗi DAG run |
| `.venv/` | Virtual environment Python (~200MB) |
| `logs/` | Airflow task logs (auto-generated) |
| `standalone_admin_password.txt` | Mật khẩu Airflow auto-generated |
| `airflow.cfg` | Config Airflow runtime |
| `airflow.db` | SQLite database của Airflow (dev only) |

> **Quy tắc vàng:** Nếu file chứa credential, lớn hơn 1MB, hoặc auto-generated — đừng commit.

---

## Bước 1 — Cài `uv` (Python Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Kiểm tra
uv --version
```

---

## Bước 2 — Cài `Docker` + `Docker Compose`

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # Apply ngay không cần đăng xuất

# Kiểm tra
docker --version
docker compose version
```

> ⚠️ Dùng `docker compose` (có dấu cách), KHÔNG dùng `docker-compose` (đã deprecated).

---

## Bước 3 — Cài Python dependencies

```bash
cd ~/startup-os-ai-advisor
uv sync
```

---

## Bước 4 — Tạo file `.env`

```bash
cp .env.example .env
nano .env   # hoặc dùng VS Code / bất kỳ editor nào
```

Điền đầy đủ các giá trị sau:

```env
# Notion
NOTION_API_KEY=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_ROOT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # Lấy từ URL Notion page (32 hex chars)

# Gemini
GEMINI_API_KEY=AQ.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# PostgreSQL (giữ nguyên nếu dùng Docker local)
POSTGRES_HOST=postgres   # Dùng "localhost" nếu chạy script ngoài Docker
POSTGRES_PORT=5432
POSTGRES_DB=startup_os
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Airflow — QUAN TRỌNG: phải khớp UID của host user
# Chạy `id -u` để lấy UID. Sai UID → lỗi "Permission denied" khi ghi file.
AIRFLOW_UID=1000

# Email alerts khi DAG fail (tuỳ chọn — bỏ trống để tắt)
ALERT_EMAIL=your@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password (không phải password Gmail thường)
                                     # Lấy tại: https://myaccount.google.com/apppasswords
```

### Lấy `NOTION_ROOT_PAGE_ID`

Mở trang gốc của Notion handbook → copy URL → lấy 32 ký tự hex ở cuối:
```
https://notion.so/The-Company-Building-Handbook-48f392a1a551836795f9010caa84da89
                                                 ↑ đây là ROOT_PAGE_ID
```

---

## Bước 5 — Tạo thư mục dữ liệu cần thiết

Các thư mục này bị gitignore nên không có trong repo, cần tạo thủ công:

```bash
mkdir -p data/bronze
mkdir -p data/.model_cache
```

---

## Bước 6 — Khởi động Docker services

```bash
docker compose up -d

# Kiểm tra status
docker compose ps
```

Kết quả mong đợi:

```
NAME                    STATUS          PORTS
startup_os_postgres     Up (healthy)    0.0.0.0:5432->5432/tcp
startup_os_pgadmin      Up              0.0.0.0:5050->80/tcp
startup_os_grafana      Up              0.0.0.0:3000->3000/tcp
startup_os_airflow      Up              0.0.0.0:8080->8080/tcp
```

> ⏳ Airflow cần ~60 giây để khởi động lần đầu (build DB, tạo admin user).

---

## Bước 7 — Trigger ingestion pipeline

Mở Airflow UI tại **http://localhost:8080** (admin / admin):

1. Vào tab **DAGs**
2. Enable DAG `01_notion_extraction`
3. Nhấn **▶ Trigger DAG**
4. Chờ DAG 01 chạy xong → tự động trigger DAG 02
5. DAG 02 sẽ download ONNX model (~900MB, lần đầu mất 5–10 phút) → embed và load vào PostgreSQL

> ℹ️ Model chỉ download **một lần** và được cache tại `data/.model_cache/`. Lần chạy tiếp theo sẽ dùng cache offline.

---

## 🌐 URLs sau khi khởi động

| Service    | URL                      | Login                   |
|------------|--------------------------|-------------------------|
| Airflow UI | http://localhost:8080    | admin / admin           |
| pgAdmin    | http://localhost:5050    | admin@admin.com / admin |
| Grafana    | http://localhost:3000    | admin / admin           |
| PostgreSQL | localhost:5432           | postgres / postgres     |

---

## 🗺️ Quick start (copy-paste all-in-one)

```bash
# 1. Cài tools
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER && newgrp docker

# 2. Clone và setup project
cd ~/startup-os-ai-advisor
uv sync

# 3. Cấu hình
cp .env.example .env
nano .env   # ← điền NOTION_API_KEY, NOTION_ROOT_PAGE_ID, GEMINI_API_KEY, AIRFLOW_UID=$(id -u)

# 4. Tạo thư mục dữ liệu
mkdir -p data/bronze data/.model_cache

# 5. Khởi động
docker compose up -d
```

---

## ❓ Troubleshooting thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `uv: command not found` | PATH chưa load | `source ~/.bashrc` |
| `docker: command not found` | Chưa cài hoặc group chưa apply | `newgrp docker` |
| `Permission denied` ghi file trong Airflow | `AIRFLOW_UID` sai | Đặt `AIRFLOW_UID=$(id -u)` trong `.env` |
| `Permission denied` download model | `HF_HOME` hoặc `data/.model_cache` chưa writable | `mkdir -p data/.model_cache` |
| `Broken DAG` do import lỗi | Module không tìm thấy trong container | Kiểm tra `PYTHONPATH` trong `docker-compose.yml` |
| `Connection refused` port 5432 từ Airflow DAG | `POSTGRES_HOST=localhost` — trong Docker container, localhost là chính container đó | Đổi thành `POSTGRES_HOST=postgres` trong `.env` |
| `Connection refused` port 5432 khi chạy script local | PostgreSQL chưa chạy hoặc dùng `POSTGRES_HOST=postgres` | `docker compose up -d` và đổi `POSTGRES_HOST=localhost` |
| `SMTPAuthenticationError` | Gmail không chấp nhận password thường | Tạo App Password tại myaccount.google.com/apppasswords |
| DAG 02 không nhận file bronze | XCom không pass đúng path | Đảm bảo đang dùng version DAG mới (PythonOperator trigger) |
