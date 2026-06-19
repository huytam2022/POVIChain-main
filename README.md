# Kiến trúc liên thông liên chuỗi nhẹ cho mạng biên dị thể

Nguyên mẫu nghiên cứu cho khả năng liên thông liên chuỗi (cross-chain
interoperability) nhẹ và xác minh được, dành cho dịch vụ IoT trong thành phố
thông minh. Hệ thống gồm phần lõi giao thức (đồng thuận dựa trên tương tác đã
xác minh, điều phối Smart Zone, xác minh lai MCU/gateway), một bộ mô phỏng
hướng dấu vết tất định để so sánh giao thức, và một dashboard minh hoạ đa vai trò.

Đánh giá dùng phương pháp mô phỏng hướng dấu vết với độ trễ mật mã được hiệu
chuẩn từ phần cứng thật (Raspberry Pi 4 và ESP32-S3). Toàn bộ mô phỏng là tất
định: chạy lại cho cùng một kết quả.

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

Dùng trực tiếp trong Python:

```python
from povichain.simulation.runner import Runner

runner = Runner(configs_root="configs", schemas_root="schemas", data_root="data")
result = runner.run_manifest("configs/experiments/main_comparison_mode_b.yaml")
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

Kiểm chứng độ trung thực: bộ mô phỏng tái tạo số đo benchmark thật trên
Raspberry Pi 4 và ESP32-S3 (độ trễ tạo bằng chứng/xác minh, CPU, bộ nhớ) trong
khoảng tin cậy 95%.

```bash
python run_validation.py
```

Kết quả ghi vào `outputs/validation/fidelity_table.{csv,md}` (sai số tương đối
lớn nhất ~1.6%).

## Kiểm thử

```bash
pytest -q
```

## Demo

```bash
pip install -r requirements_dashboard.txt
python -m streamlit run src/dashboard/streamlit_app.py
```

Hoặc dùng script khởi chạy: `run_dashboard.bat` (Windows) /
`bash run_dashboard.sh` (Linux/macOS). Demo gồm ba vai trò: người dân (trạm sạc
xe điện, hoá đơn nước, đo điện mặt trời), quản trị (theo dõi epoch, bảng điều
khiển validator, sức khoẻ mạng), và thanh tra (xác minh danh tính không tiết lộ
trên năm loại chứng chỉ).

## Cấu trúc thư mục

```
src/
  povichain/        Lõi giao thức: đồng thuận, mật mã, định tuyến, thiết bị, mô phỏng, báo cáo
  relay_protocol/   Bộ mô phỏng baseline kiểu relay
  oracle_protocol/  Bộ mô phỏng baseline kiểu oracle
  dashboard/        Giao diện Streamlit (kiosk, vai trò, trình xem dấu vết)
  resilience/       Runner và sinh biểu đồ cho thí nghiệm bền vững
  performance/      Runner và sinh biểu đồ cho thí nghiệm hiệu năng
  resource_usage/   Runner và sinh biểu đồ cho tài nguyên thiết bị
  ablation/         Ablation đo thật (measure.py) và sinh biểu đồ
  security_analysis/ Phân tích an ninh - kinh tế (ECoC, tập trung hoá)

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
