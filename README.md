# Kiến trúc liên thông liên chuỗi nhẹ cho mạng biên dị thể

Nguyên mẫu nghiên cứu cho khả năng liên thông liên chuỗi (cross-chain
interoperability) nhẹ và xác minh được, dành cho dịch vụ IoT trong thành phố
thông minh. Hệ thống gồm phần lõi giao thức (đồng thuận dựa trên tương tác đã
xác minh, điều phối Smart Zone, xác minh lai MCU/gateway), một bộ mô phỏng
hướng dấu vết tất định để so sánh giao thức, và một dashboard minh hoạ đa vai trò.

Đánh giá dùng phương pháp mô phỏng hướng dấu vết với độ trễ mật mã được hiệu
chuẩn từ phần cứng thật (Raspberry Pi 4 và ESP32-S3). Toàn bộ mô phỏng là tất
định: chạy lại cho cùng một kết quả.

## Tổ chức mã nguồn

Mã nguồn trong `src/` được tách thành ba tầng rõ ràng:

- **`src/povichain/`** — thư viện lõi giao thức (đồng thuận PoVI, mật mã, định
  tuyến, thiết bị, mô phỏng, báo cáo). Mọi thành phần khác đều phụ thuộc vào đây.
- **`src/research/`** — mã thực nghiệm nghiên cứu: hai baseline (relay/oracle) và
  các runner đánh giá theo bốn câu hỏi nghiên cứu (RQ1–RQ4) cùng đối chiếu fidelity.
- **`src/demo/`** — mã demo (dashboard Streamlit minh hoạ đa vai trò).

Dự án chạy theo kiểu thêm `src/` vào đường dẫn (không cần cài đặt gói). Các điểm
vào ở thư mục gốc (`run*.py`, `run_dashboard.*`) đã tự thêm `src/` vào `sys.path`;
khi gọi trực tiếp bằng `python -m` thì đặt `PYTHONPATH=src`.

## Yêu cầu

- Python 3.10 trở lên
- `pyyaml` cho phần lõi mô phỏng (đọc manifest/cấu hình)
- Phần demo: `pip install -r requirements_dashboard.txt`

## Chạy một thí nghiệm

Mỗi thí nghiệm được mô tả bằng một manifest YAML trong `configs/experiments/`.
Chạy qua điểm vào dòng lệnh:

```bash
python run.py --config configs/experiments/main_comparison_mode_b.yaml
```

Kết quả ghi vào `outputs/<experiment_id>/` (gồm `*_summary.json`,
`aggregated_metrics.json`, `raw_metrics.json`). Có thể chỉ định nơi ghi bằng
`--output-dir`.

Dùng trực tiếp trong Python (cần có `src/` trên đường dẫn, ví dụ
`PYTHONPATH=src`):

```python
from povichain.simulation.runner import Runner

runner = Runner(configs_root="configs", schemas_root="schemas", data_root="data")
result = runner.run_manifest("configs/experiments/main_comparison_mode_b.yaml")
```

Chạy riêng hai baseline để so sánh:

```bash
python run_relay_protocol.py --config configs/experiments/relay_protocol_comparison.yaml
PYTHONPATH=src python -m research.oracle_protocol --config configs/experiments/oracle_protocol_comparison.yaml
```

Một số manifest theo bốn câu hỏi nghiên cứu:

- `rq1_sybil_collusion.yaml`, `rq1_network_partitions.yaml` — an ninh đối kháng
- `rq2_multidomain_load.yaml`, `rq2_stress_epochs.yaml` — mở rộng đa miền
- `rq3_end_device.yaml`, `rq3_gateway_profile.yaml` — hiệu quả trên thiết bị IoT
- `main_comparison_mode_b.yaml` — so sánh với baseline IBC-like / LayerZero-like

## Ablation (đo thật)

Phân tích vai trò từng thành phần bằng cách **tắt lần lượt** mỗi trụ cột kiến
trúc rồi **đo trực tiếp** thông lượng / độ trễ / năng lượng từ mô phỏng (không
phải áp hệ số ước lượng):

```bash
python run_ablation.py
```

Bốn biến thể: bỏ trọng số danh tiếng, đồng thuận toàn mạng (bỏ ủy ban VRF),
đồng thuận Full-ZKP (bỏ xác minh lai), và bỏ điều phối Smart Zone. Kết quả ghi
vào `outputs/rq4_ablations/measured_{ablations.csv, summary.json, summary.md}`.

## Đối chiếu mô phỏng vs số đo phần cứng

Kiểm tra nhất quán nội tại: xác nhận bộ mô phỏng tái tạo **trung thực** các số đo
benchmark đã hiệu chuẩn trên Raspberry Pi 4 và ESP32-S3 (độ trễ tạo bằng
chứng/xác minh, CPU, bộ nhớ) — mọi giá trị nằm trong khoảng tin cậy 95% của số
đo. Đây là sanity check cho cơ chế phát-lại tất định (không phải xác thực mô
hình độc lập trên testbed mới).

```bash
python run_validation.py
```

Kết quả ghi vào `outputs/validation/fidelity_table.{csv,md}` (độ lệch tương đối
lớn nhất ~1.6%).

## Kiểm thử

```bash
pytest -q
```

## Demo

```bash
pip install -r requirements_dashboard.txt
python -m streamlit run src/demo/dashboard/streamlit_app.py
```

Hoặc dùng script khởi chạy: `run_dashboard.bat` (Windows) /
`bash run_dashboard.sh` (Linux/macOS). Demo gồm ba vai trò: người dân (trạm sạc
xe điện, hoá đơn nước, đo điện mặt trời), quản trị (theo dõi epoch, bảng điều
khiển validator, sức khoẻ mạng), và thanh tra (xác minh danh tính không tiết lộ
trên năm loại chứng chỉ).

## Cấu trúc thư mục

```
src/
  povichain/          Lõi giao thức: đồng thuận, mật mã, định tuyến, thiết bị, mô phỏng, báo cáo
  research/           Mã thực nghiệm nghiên cứu (baselines + đánh giá RQ1–RQ4)
    relay_protocol/   Bộ mô phỏng baseline kiểu relay (IBC-like)
    oracle_protocol/  Bộ mô phỏng baseline kiểu oracle (LayerZero-like)
    resilience/       Runner + sinh biểu đồ thí nghiệm bền vững (RQ1)
    performance/      Runner + sinh biểu đồ thí nghiệm hiệu năng (RQ2)
    resource_usage/   Runner + sinh biểu đồ tài nguyên thiết bị (RQ3)
    ablation/         Ablation đo thật (measure.py) + sinh biểu đồ (RQ4)
    security_analysis/ Phân tích an ninh - kinh tế (ECoC, tập trung hoá)
    validation/       Đối chiếu fidelity bộ mô phỏng (run_validation.py)
  demo/               Mã demo
    dashboard/        Giao diện Streamlit (kiosk, vai trò, trình xem dấu vết)

configs/
  defaults/         Hồ sơ mạng, thiết bị, năng lượng, workload
  experiments/      Manifest thí nghiệm (Mode A / B và các kịch bản)
  profiles/         Hồ sơ giao thức tổng hợp

data/               Chuỗi đo lường đầu vào và artefact bootstrap đúng schema
schemas/            JSON Schema cho manifest và dữ liệu hiệu chuẩn
outputs/            Kết quả thí nghiệm
tests/              Bộ kiểm thử pytest
```

## Ghi chú tái lập

Logic giao thức tách biệt khỏi dữ liệu đo thiết bị: độ trễ mật mã và mức tiêu
thụ tài nguyên được hiệu chuẩn ngoại tuyến rồi tiêm vào bộ mô phỏng qua các điểm
tiêm chuẩn hoá theo schema. Năng lượng mỗi giao dịch là giá trị hiệu chuẩn ở mức
giao thức (xem `configs/experiments/end_device.yaml`), nhất quán giữa các thí
nghiệm. Nhờ tách biệt này, người đọc tái lập được kết quả khi cung cấp tệp hiệu
chuẩn thiết bị đúng schema.
