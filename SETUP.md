# 🚀 Hướng dẫn Setup Máy Ảo Mới — Startup OS AI Advisor

> Áp dụng cho: Ubuntu 22.04/24.04 mới toanh, chưa cài gì.

---

## Bước 1 — Cài `uv` (Python Package Manager)

`uv` thay thế cho `pip` + `venv`, nhanh hơn nhiều và tự quản lý virtual env.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Thêm vào PATH vĩnh viễn (để không bị "command not found" lần sau):

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Kiểm tra:

```bash
uv --version
# uv 0.11.32 (x86_64-unknown-linux-gnu)
```

---

## Bước 2 — Cài `Docker` + `Docker Compose`

Dùng script cài chính thức của Docker (cài cả Docker Engine lẫn Compose plugin):

```bash
curl -fsSL https://get.docker.com | sudo sh
```

Thêm user vào group `docker` để chạy không cần `sudo`:

```bash
sudo usermod -aG docker $USER
```

> ⚠️ **Quan trọng:** Phải **đăng xuất rồi đăng nhập lại** (hoặc mở terminal mới) để group có hiệu lực.  
> Hoặc dùng lệnh sau để apply ngay trong session hiện tại:
> ```bash
> newgrp docker
> ```

Kiểm tra:

```bash
docker --version
# Docker version 29.6.2, build dfc4efb

docker compose version
# Docker Compose version v5.3.1
```

> ⚠️ **Lưu ý:** Dùng `docker compose` (có dấu cách), KHÔNG dùng `docker-compose` (gạch nối) — lệnh cũ đã bị deprecated.

---

## Bước 3 — Cài dependencies Python cho project

Vào thư mục project và chạy `uv sync`:

```bash
cd ~/startup-os-ai-advisor
uv sync
```

Lệnh này sẽ:
- Tạo virtual env tại `.venv/`
- Cài tất cả 42 packages từ `uv.lock` (fastembed, psycopg2, notion-client, tiktoken, v.v.)

---

## Bước 4 — Tạo file `.env`

Copy file mẫu và điền thông tin:

```bash
cd ~/startup-os-ai-advisor
nano .env
```

Nội dung file `.env`:

```env
# Notion
NOTION_API_KEY=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_ROOT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Gemini
GEMINI_API_KEY=AQ.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# PostgreSQL (giữ nguyên nếu dùng Docker local)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=startup_os
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

---

## Bước 5 — Khởi động PostgreSQL bằng Docker

```bash
cd ~/startup-os-ai-advisor
docker compose up -d
```

Kiểm tra các container đang chạy:

```bash
docker compose ps
```

Kết quả mong đợi:

```
NAME                    STATUS          PORTS
startup_os_postgres     Up (healthy)    0.0.0.0:5432->5432/tcp
startup_os_pgadmin      Up              0.0.0.0:5050->80/tcp
startup_os_grafana      Up              0.0.0.0:3000->3000/tcp
```

Chờ PostgreSQL healthy (khoảng 10-20 giây):

```bash
docker compose logs postgres --tail=5
```

---

## Bước 6 — Chạy Ingestion Pipeline

```bash
# Chạy toàn bộ (ingest tất cả Notion pages)
uv run python -m ingestion.run_ingestion

# Chạy thử với 5 pages đầu tiên (để test nhanh)
uv run python -m ingestion.run_ingestion --limit 5
```

---

## 🗺️ Tóm tắt nhanh (copy-paste all-in-one)

```bash
# 1. Cài uv
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

# 2. Cài Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 3. Cài Python dependencies
cd ~/startup-os-ai-advisor
uv sync

# 4. Tạo .env (điền API keys)
nano .env

# 5. Khởi động database
docker compose up -d

# 6. Chạy pipeline
uv run python -m ingestion.run_ingestion --limit 5
```

---

## 🌐 Các URL sau khi khởi động

| Service     | URL                         | Login                   |
|-------------|------------------------------|-------------------------|
| pgAdmin     | http://localhost:5050        | admin@admin.com / admin |
| Grafana     | http://localhost:3000        | admin / admin           |
| PostgreSQL  | localhost:5432               | postgres / postgres     |

---

## ❓ Troubleshooting thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `uv: command not found` | PATH chưa load | `source ~/.bashrc` |
| `docker-compose: command not found` | Dùng lệnh cũ | Dùng `docker compose` (có dấu cách) |
| `permission denied` khi chạy docker | Chưa apply group hoặc quyền socket | `newgrp docker` hoặc `sudo chmod 666 /var/run/docker.sock` |
| `Connection refused` port 5432 | PostgreSQL chưa chạy | `docker compose up -d` |
| `uv sync` lỗi | Không có `pyproject.toml` | Đảm bảo đang ở đúng thư mục project |
