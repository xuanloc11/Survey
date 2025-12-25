# HCMUTE Survey (SurveyProject)

Hệ thống khảo sát xây dựng bằng **Python/Django**: tạo khảo sát, thêm câu hỏi/lựa chọn, thu thập phản hồi, giới hạn truy cập (mật khẩu/whitelist), giới hạn số lượt, và xuất kết quả **CSV/Excel**.

## Tính năng chính

- **Quản lý khảo sát**: tạo/sửa/xóa, bật/tắt hoạt động, ảnh tiêu đề, thời gian bắt đầu/kết thúc.
- **Câu hỏi**: text / single choice / multiple choice, bắt buộc/không bắt buộc, sắp xếp thứ tự.
- **Giới hạn truy cập**:
  - **Mật khẩu khảo sát** (hash bằng Django).
  - **Whitelist email** (yêu cầu đăng nhập bằng email có trong danh sách).
  - **One response only** (mỗi người/thiết bị chỉ trả lời 1 lần tùy cấu hình).
  - **Max responses** (đủ số lượng thì khóa).
- **Chống spam**: Cloudflare Turnstile (áp dụng cho người dùng chưa đăng nhập).
- **Xem lại phản hồi** (nếu bật) hoặc **gửi email xác nhận** (nếu bật).
- **Báo cáo**: trang kết quả + export **CSV/Excel**.

## Tech stack

- Python + Django 5.x
- PostgreSQL (`psycopg2-binary`)
- Export Excel: `openpyxl`
- Captcha verify: `requests`

## Cấu trúc thư mục (phần quan trọng)

- `SurveyProject/`: cấu hình project (settings/urls/wsgi/asgi)
- `surveys/`: app nghiệp vụ
  - `models.py`, `forms.py`, `migrations/`
  - `views/`: tách view theo nhóm
    - `auth.py`, `pages.py`, `survey.py`, `questions.py`, `take.py`, `results.py`, `api.py`, `errors.py`, `utils.py`
  - `urls.py`
- `templates/`: giao diện Django templates
- `static/`: CSS/asset
- `media/`: file upload (ảnh header, avatar, ...)

## Yêu cầu

- Python 3.10+ (khuyến nghị)
- PostgreSQL đã cài và có database

## Cài đặt & chạy dự án

### 1) Tạo môi trường và cài dependencies

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2) Cấu hình biến môi trường (email + captcha)

Project đọc biến môi trường qua `python-dotenv`. Tạo file `.env` ở thư mục gốc:

```bash
copy env.example .env
```

Sau đó chỉnh các biến trong `.env` (xem file `env.example`).

### 3) Cấu hình database

Hiện tại `SurveyProject/settings.py` đang cấu hình **PostgreSQL** trực tiếp trong `DATABASES`.

- Tạo database (ví dụ: `surveydb`)
- Chỉnh lại các giá trị trong `SurveyProject/settings.py`:
  - `NAME`, `USER`, `PASSWORD`, `HOST`, `PORT`

> Gợi ý: Nếu bạn muốn “chuẩn production”, có thể refactor để đọc các thông số DB từ `.env`.

### 4) Migrate database + tạo admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5) Chạy server

```bash
python manage.py runserver
```

- Trang chủ: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Luồng sử dụng nhanh (không cần UI demo)

1. Đăng nhập → vào **My Surveys**
2. Tạo survey (mặc định tạo dạng nháp) → thêm câu hỏi / lựa chọn
3. Xuất bản survey (bật active) → copy link chia sẻ
4. Người dùng vào link → nhập mật khẩu (nếu có) → làm khảo sát
5. Chủ survey xem **results** hoặc export CSV/Excel

## Ghi chú cấu hình

### Email (Resend SMTP)

Trong `SurveyProject/settings.py` đang dùng:
- `EMAIL_HOST = smtp.resend.com`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` lấy từ `.env`

### Cloudflare Turnstile

Biến môi trường:
- `CLOUDFLARE_TURNSTILE_SITE_KEY`
- `CLOUDFLARE_TURNSTILE_SECRET_KEY`

Nếu không cấu hình, phần captcha có thể không hoạt động đúng cho user ẩn danh.

## Tài liệu

- Báo cáo: `docs/BaoCao_HeThong_KhaoSat_HCMUTE_Survey.docx`


