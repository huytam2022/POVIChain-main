"""Smart-city service kiosks — the user's point of view, settled cross-chain.

Two scenarios share one rendering engine:
  * EV charging station  — a driver plugs in; battery ring fills, kWh & cost tick.
  * Smart water meter    — an IoT meter reports; a tank fills, m3 & bill tick.

In both, four city services confirm the settlement cross-chain (four "Smart
Zones" lighting up). All motion is driven by a fixed deterministic timeline
(no random): the same parameters always animate the same way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple



_CAR_DB: dict = {
    "vinfast vf 3":       20.0,
    "vinfast vf 5":       37.2,
    "vinfast vf 5 plus":  37.2,
    "vinfast vf 6":       59.6,
    "vinfast vf 7":       75.3,
    "vinfast vf 8":       87.7,
    "vinfast vf 8 plus":  87.7,
    "vinfast vf 9":      123.0,
    "vinfast vf e34":     42.0,
    "tesla model 3":      82.0,
    "tesla model y":      82.0,
    "tesla model s":     100.0,
    "toyota bz4x":        71.4,
    "bmw i4":             83.9,
    "hyundai ioniq 6":    77.4,
    "kia ev6":            77.4,
    "mercedes eqb":       66.5,
}
_DEFAULT_KWH    = 60.0
_PRICE_PER_KWH  = 3858

_VEHICLE_REG: dict = {
    "51K-123.45": {"wallet": "VI-0084912", "owner": "Nguyễn Văn An"},
    "29A-888.88": {"wallet": "VI-0031205", "owner": "Trần Thị Bích"},
    "43B-001.23": {"wallet": "VI-0099001", "owner": "Lê Văn Cường"},
    "77C-456.78": {"wallet": "VI-0055678", "owner": "Phạm Thị Dung"},
    "51F-999.00": {"wallet": "0901234567", "owner": "Hoàng Văn Em"},
}

_SOLAR_REG: dict = {
    "PV-5520": {"owner": "Nguyễn Văn An",  "wallet": "VI-0084912", "address": "Nhà phố, Gò Vấp"},
    "PV-1003": {"owner": "Trần Thị Bích",  "wallet": "VI-0031205", "address": "Biệt thự, TP. Thủ Đức"},
    "PV-0307": {"owner": "Lê Văn Cường",   "wallet": "VI-0099001", "address": "Nhà dân, Bình Chánh"},
}
_SOLAR_FIT_PRICE = 2030
_SOLAR_PR        = 0.82
_SOLAR_CO2       = 0.74


@dataclass(frozen=True)
class ChargeSession:
    model: str
    plate: str
    current_pct: int
    target_pct: int

    @property
    def battery_kwh(self) -> float:
        return _CAR_DB.get(self.model.lower().strip(), _DEFAULT_KWH)

    @property
    def add_kwh(self) -> float:
        return max(0.0, round((self.target_pct - self.current_pct) / 100.0 * self.battery_kwh, 2))

    @property
    def cost(self) -> int:
        return int(round(self.add_kwh * _PRICE_PER_KWH))

    @property
    def wallet(self) -> str:
        return _VEHICLE_REG.get(self.plate.strip().upper(), {}).get("wallet", "VI-GUEST")

    @property
    def owner(self) -> str:
        return _VEHICLE_REG.get(self.plate.strip().upper(), {}).get("owner", "Khách vãng lai")


_WATER_METER_DB: dict = {
    "ĐH-0427": {
        "device": "Hộ dân · ĐH-0427",
        "location": "Chung cư A, Quận 7",
        "reading_prev": 1284.6,
        "reading_curr": 1298.8,
        "price": 11500,
        "wallet": "VI-0084912",
        "owner": "Nguyễn Văn An",
    },
    "ĐH-1185": {
        "device": "Hộ dân · ĐH-1185",
        "location": "Khu dân cư Thủ Đức",
        "reading_prev": 876.2,
        "reading_curr": 885.8,
        "price": 11500,
        "wallet": "VI-0031205",
        "owner": "Trần Thị Bích",
    },
    "ĐH-3390": {
        "device": "Cụm thương mại · ĐH-3390",
        "location": "Toà văn phòng, Quận 1",
        "reading_prev": 4120.0,
        "reading_curr": 4161.0,
        "price": 14000,
        "wallet": "VI-0055678",
        "owner": "Công ty TNHH Văn phòng Sài Gòn",
    },
    "ĐH-0892": {
        "device": "Hộ dân · ĐH-0892",
        "location": "Phường Bình Thạnh, Quận Bình Thạnh",
        "reading_prev": 2045.3,
        "reading_curr": 2058.9,
        "price": 11500,
        "wallet": "VI-0099001",
        "owner": "Lê Văn Cường",
    },
    "ĐH-2201": {
        "device": "Hộ dân · ĐH-2201",
        "location": "Khu dân cư Phú Mỹ, Quận 7",
        "reading_prev": 3312.7,
        "reading_curr": 3328.1,
        "price": 11500,
        "wallet": "0901234567",
        "owner": "Hoàng Văn Em",
    },
}


@dataclass(frozen=True)
class WaterSession:
    meter_id: str

    def _rec(self) -> dict:
        return _WATER_METER_DB.get(self.meter_id.strip(), {})

    @property
    def found(self) -> bool:
        return bool(self._rec())

    @property
    def device(self) -> str:
        return self._rec().get("device", f"ĐH-{self.meter_id}")

    @property
    def location(self) -> str:
        return self._rec().get("location", "—")

    @property
    def reading_prev(self) -> float:
        return self._rec().get("reading_prev", 0.0)

    @property
    def reading_curr(self) -> float:
        return self._rec().get("reading_curr", 0.0)

    @property
    def period_m3(self) -> float:
        return round(self.reading_curr - self.reading_prev, 1)

    @property
    def price_per_m3(self) -> int:
        return self._rec().get("price", 11500)

    @property
    def cost(self) -> int:
        return int(round(self.period_m3 * self.price_per_m3))

    @property
    def wallet(self) -> str:
        return self._rec().get("wallet", "VI-GUEST")

    @property
    def owner(self) -> str:
        return self._rec().get("owner", "Không xác định")


@dataclass(frozen=True)
class SolarSession:
    """Một ngày bán điện mặt trời lên lưới.

    Khác với form cũ (gõ thẳng một con số kWh cố định), sản lượng ở đây được
    TÍNH RA từ các thông số người dân thực sự nhập: công suất hệ mái (kWp),
    số giờ nắng đỉnh trong ngày, và tỷ lệ điện dư bán lên lưới.
    """
    system_id: str
    address: str
    system_kwp: float
    sun_hours: float
    export_pct: int

    def _rec(self) -> dict:
        return _SOLAR_REG.get(self.system_id.strip().upper(), {})

    @property
    def found(self) -> bool:
        return bool(self._rec())

    @property
    def owner(self) -> str:
        return self._rec().get("owner", "Chủ hộ mới")

    @property
    def wallet(self) -> str:
        return self._rec().get("wallet", "VI-GUEST")

    @property
    def generated_kwh(self) -> float:
        """Tổng điện hệ mái phát ra hôm nay = kWp × giờ nắng × hiệu suất."""
        return round(self.system_kwp * self.sun_hours * _SOLAR_PR, 1)

    @property
    def export_kwh(self) -> float:
        """Phần điện dư thực sự bán lên lưới."""
        return round(self.generated_kwh * self.export_pct / 100.0, 1)

    @property
    def self_use_kwh(self) -> float:
        """Phần điện tự tiêu thụ trong nhà."""
        return round(self.generated_kwh - self.export_kwh, 1)

    @property
    def cost(self) -> int:
        """Tiền bán điện nhận về ví (đ)."""
        return int(round(self.export_kwh * _SOLAR_FIT_PRICE))

    @property
    def co2_kg(self) -> float:
        """Lượng CO₂ tránh phát thải nhờ điện sạch (kg)."""
        return round(self.generated_kwh * _SOLAR_CO2, 1)


@dataclass(frozen=True)
class _MeterView:
    brand_small: str
    brand_title: str
    brand_icon: str
    live_busy: str
    live_idle: str
    subj_emoji: str
    subj_name: str
    subj_sub: str
    verify_text: str
    gauge: str
    ring_start_pct: int
    ring_end_pct: int
    ring_label: str
    phase_run: str
    phase_done: str
    primary_target: float
    primary_decimals: int
    primary_unit: str
    secondary_target: int
    secondary_label: str
    steps: Tuple[Tuple[str, str, str], ...]
    tagline_html: str
    done_text: str
    idle_text: str
    step_times: Tuple[float, ...] = (1.0, 4.0, 7.0, 10.0)
    duration_s: float = 12.0


def _fmt_vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".") + " ₫"


def ev_view(s: ChargeSession) -> _MeterView:
    return _MeterView(
        brand_small="SMART CITY",
        brand_title="Trạm sạc thông minh",
        brand_icon="⚡",
        live_busy="ĐANG PHỤC VỤ",
        live_idle="SẴN SÀNG",
        subj_emoji="🚗",
        subj_name=s.model,
        subj_sub=f"{s.plate} · {s.owner}",
        verify_text="✓ Đã xác thực",
        gauge="ring",
        ring_start_pct=s.current_pct,
        ring_end_pct=s.target_pct,
        ring_label="PIN",
        phase_run="ĐANG SẠC",
        phase_done="ĐÃ SẠC XONG",
        primary_target=s.add_kwh,
        primary_decimals=1,
        primary_unit="kWh đã nạp",
        secondary_target=s.cost,
        secondary_label=f"Ví {s.wallet} · tự động",
        steps=(
            ("Định danh", "🪪", f"Xác thực xe {s.plate} & chủ xe"),
            ("Năng lượng", "⚡", f"Nạp {s.add_kwh:.1f} kWh · pin {s.current_pct}%→{s.target_pct}%"),
            ("Tài chính", "💳", f"Ví {s.wallet} · {_fmt_vnd(s.cost)}"),
            ("Giao thông", "🅿️", "Ghi tín dụng phí đỗ"),
        ),
        tagline_html=(
            f"Biển số <b>{s.plate}</b> tra cứu tự động trên chuỗi — "
            f"dung lượng pin <b>{s.battery_kwh:.0f} kWh</b>, "
            f"ví thanh toán <b>{s.wallet}</b> liên kết với chủ xe <b>{s.owner}</b>."
        ),
        done_text="✓ HOÀN TẤT · Cảm ơn quý khách, hẹn gặp lại!",
        idle_text="Nhập mẫu xe + biển số + mức pin mong muốn rồi bấm <b>BẮT ĐẦU SẠC</b>.",
    )


def water_view(s: WaterSession) -> _MeterView:
    return _MeterView(
        brand_small="SMART CITY",
        brand_title="Đồng hồ nước thông minh",
        brand_icon="💧",
        live_busy="ĐANG CHỐT KỲ",
        live_idle="ĐÃ ĐỒNG BỘ",
        subj_emoji="🏠",
        subj_name=s.device,
        subj_sub=f"{s.location} · {s.owner}",
        verify_text="✓ Đã đồng bộ",
        gauge="tank",
        ring_start_pct=0,
        ring_end_pct=100,
        ring_label="KỲ NÀY",
        phase_run="ĐANG ĐỌC SỐ",
        phase_done="ĐÃ CHỐT KỲ",
        primary_target=s.period_m3,
        primary_decimals=1,
        primary_unit="m³ đã dùng",
        secondary_target=s.cost,
        secondary_label=f"Ví {s.wallet} · tự động",
        steps=(
            ("Môi trường", "💧",
             f"Chỉ số {s.reading_prev:.1f}→{s.reading_curr:.1f} m³ (+{s.period_m3:.1f})"),
            ("Năng lượng", "⚡", "Cân đối bơm & lưới điện"),
            ("Tài chính", "💳", f"Ví {s.wallet} · {_fmt_vnd(s.cost)}"),
            ("Quản trị", "🏛️", f"Biểu giá {s.price_per_m3:,} ₫/m³ · ghi sổ"),
        ),
        tagline_html=(
            f"Mã đồng hồ <b>{s.meter_id}</b> tra cứu tự động — "
            f"chỉ số tháng trước <b>{s.reading_prev:.1f} m³</b>, "
            f"hiện tại <b>{s.reading_curr:.1f} m³</b>; "
            f"hoá đơn <b>{_fmt_vnd(s.cost)}</b> trừ tự động vào ví <b>{s.wallet}</b>."
        ),
        done_text="✓ ĐÃ CHỐT KỲ · Hoá đơn đã gửi tới người dân!",
        idle_text="Nhập mã đồng hồ nước rồi bấm <b>CHỐT KỲ & ĐỐI SOÁT</b>.",
    )


def solar_view(s: SolarSession) -> _MeterView:
    pct = int(round(s.export_pct))
    return _MeterView(
        brand_small="SMART CITY",
        brand_title="Điện mặt trời mái nhà",
        brand_icon="☀️",
        live_busy="ĐANG PHÁT ĐIỆN",
        live_idle="SẴN SÀNG",
        subj_emoji="🏡",
        subj_name=f"{s.system_id} · {s.system_kwp:g} kWp",
        subj_sub=f"{s.address} · {s.owner}",
        verify_text="✓ Đã đồng bộ hệ mái",
        gauge="ring",
        ring_start_pct=0,
        ring_end_pct=pct,
        ring_label="BÁN LÊN LƯỚI",
        phase_run="ĐANG ĐẨY LÊN LƯỚI",
        phase_done="ĐÃ CHỐT SẢN LƯỢNG",
        primary_target=s.export_kwh,
        primary_decimals=1,
        primary_unit="kWh bán lên lưới",
        secondary_target=s.cost,
        secondary_label=f"Ví {s.wallet} · tiền bán điện",
        steps=(
            ("Năng lượng", "⚡",
             f"Phát {s.generated_kwh:.1f} kWh · {s.system_kwp:g} kWp × {s.sun_hours:g}h nắng"),
            ("Môi trường", "🌱", f"Cấp tín chỉ carbon · giảm {s.co2_kg:.1f} kg CO₂"),
            ("Tài chính", "💳", f"Ví {s.wallet} · +{_fmt_vnd(s.cost)}"),
            ("Quản trị", "🏛️", f"Áp giá FIT {_SOLAR_FIT_PRICE:,} ₫/kWh"),
        ),
        tagline_html=(
            f"Hệ mái <b>{s.system_kwp:g} kWp</b> phát <b>{s.generated_kwh:.1f} kWh</b> hôm nay — "
            f"tự dùng <b>{s.self_use_kwh:.1f} kWh</b>, bán dư <b>{s.export_kwh:.1f} kWh</b> lên lưới; "
            f"tiền bán điện <b>{_fmt_vnd(s.cost)}</b> tự động về ví <b>{s.wallet}</b> của <b>{s.owner}</b>."
        ),
        done_text="✓ ĐÃ CHỐT SẢN LƯỢNG · Tiền bán điện đã vào ví!",
        idle_text="Chọn công suất hệ mái + giờ nắng + tỷ lệ bán lên lưới rồi bấm <b>CHỐT SẢN LƯỢNG NGÀY</b>.",
    )


def _gauge_svg(v: _MeterView) -> str:
    if v.gauge == "ring":
        return f"""
      <div class='ring'>
        <svg width='140' height='140' viewBox='0 0 140 140'>
          <circle cx='70' cy='70' r='60' fill='none' stroke='#16203a' stroke-width='12'/>
          <circle id='arc' cx='70' cy='70' r='60' fill='none' stroke='url(#g)' stroke-width='12'
                  stroke-linecap='round' stroke-dasharray='377' stroke-dashoffset='377'/>
          <defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
            <stop offset='0' stop-color='#38f0d4'/><stop offset='1' stop-color='#67e8f9'/>
          </linearGradient></defs>
        </svg>
        <div class='ctr'><div class='pc' id='pc'>{v.ring_start_pct}%</div><div class='lb'>{v.ring_label}</div></div>
      </div>"""
    return f"""
      <div class='tank'>
        <svg width='112' height='140' viewBox='0 0 112 140'>
          <rect x='6' y='6' width='100' height='128' rx='16' fill='#0a1326' stroke='#16203a' stroke-width='2'/>
          <defs>
            <linearGradient id='wg' x1='0' y1='0' x2='0' y2='1'>
              <stop offset='0' stop-color='#38f0d4'/><stop offset='1' stop-color='#0e7490'/>
            </linearGradient>
            <clipPath id='tankclip'><rect x='8' y='8' width='96' height='124' rx='14'/></clipPath>
          </defs>
          <g clip-path='url(#tankclip)'>
            <rect id='water' x='8' y='132' width='96' height='0' fill='url(#wg)' opacity='0.9'/>
          </g>
        </svg>
        <div class='ctr'><div class='pc' id='pc'>0</div><div class='lb'>{v.ring_label}</div></div>
      </div>"""


def _render(v: _MeterView, run_id: int, started: bool) -> str:
    autostart = "true" if started else "false"
    step_cards = []
    for i, (zone, icon, action) in enumerate(v.steps):
        step_cards.append(
            f"""
      <div class='step' id='step{i}'>
        <div class='step-ic'>{icon}</div>
        <div class='step-tx'><div class='step-zone'>{zone}</div><div class='step-act'>{action}</div></div>
        <div class='step-st' id='st{i}'>⏳</div>
      </div>"""
        )
    steps_js = ",".join(str(t) for t in v.step_times)
    idle_block = "" if started else f"<div class='idle'>{v.idle_text}</div>"

    return f"""<!DOCTYPE html>
<html data-run='{run_id}'><head><meta charset='utf-8'>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap' rel='stylesheet'>
<style>
  :root {{ --bg:#04050d; --line:#1d2740; --teal:#38f0d4; --ink:#eef2ff; --dim:#8492b4; --good:#34d399; --warn:#fbbf24; --bad:#f87171; }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; padding:0; background:var(--bg); font-family:'Outfit',Inter,system-ui,sans-serif; color:var(--ink); overflow:hidden; }}
  .wrap {{ max-width:560px; margin:0 auto; padding:14px 8px; }}
  .scr {{ background:linear-gradient(180deg,#0c1326,#070b16); border:1px solid var(--line); border-radius:22px; padding:18px 20px 20px; box-shadow:0 24px 60px rgba(0,0,0,.5); }}
  .top {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }}
  .brand {{ display:flex; align-items:center; gap:10px; }}
  .logo {{ width:34px;height:34px;border-radius:10px; background:rgba(56,240,212,.12); border:1px solid rgba(56,240,212,.25); display:flex;align-items:center;justify-content:center;font-size:18px; }}
  .brand b {{ font-size:13px; letter-spacing:.1px; font-weight:600; }}
  .brand small {{ display:block; font-size:9px; letter-spacing:2.5px; color:var(--teal); font-weight:600; }}
  .live {{ font-size:10px; color:var(--teal); display:flex; align-items:center; gap:6px; font-weight:600; letter-spacing:.5px; }}
  .live .d {{ width:7px;height:7px;border-radius:50%;background:var(--teal); animation:pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100%{{opacity:.4}} 50%{{opacity:1}} }}
  .veh {{ display:flex; align-items:center; gap:12px; background:#0a1124; border:1px solid var(--line); border-radius:12px; padding:11px 13px; margin-bottom:14px; }}
  .veh .em {{ font-size:24px; }}
  .veh .nm {{ font-size:14.5px; font-weight:700; }}
  .veh .pl {{ font-size:11px; color:var(--dim); margin-top:1px; }}
  .veh .ok {{ margin-left:auto; font-size:10.5px; color:var(--teal); font-weight:600; opacity:0; transform:translateX(6px); transition:.5s; }}
  .veh .ok.on {{ opacity:1; transform:none; }}
  .ring-row {{ display:flex; align-items:center; gap:20px; margin:4px 2px 14px; }}
  .ring, .tank {{ position:relative; width:140px; height:140px; flex:0 0 auto; }}
  .tank {{ width:112px; }}
  .ring svg {{ transform:rotate(-90deg); }}
  .ring .ctr, .tank .ctr {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
  .ring .pc, .tank .pc {{ font-size:30px; font-weight:800; line-height:1; }}
  .ring .lb, .tank .lb {{ font-size:9px; letter-spacing:2px; color:var(--dim); margin-top:5px; font-weight:600; text-transform:uppercase; }}
  .tank .pc {{ color:var(--ink); }}
  .meta {{ flex:1; }}
  .meta .st {{ font-size:9px; letter-spacing:2px; font-weight:600; color:var(--teal); text-transform:uppercase; }}
  .stat {{ margin-top:10px; }}
  .stat .v {{ font-size:26px; font-weight:800; letter-spacing:-.5px; font-variant-numeric:tabular-nums; }}
  .stat .u {{ font-size:11.5px; color:var(--dim); margin-left:5px; font-weight:500; }}
  .stat .k2 {{ font-size:10.5px; color:var(--dim); margin-top:2px; }}
  .cost .v {{ color:var(--teal); }}
  .settle {{ background:#0a1124; border:1px solid var(--line); border-radius:12px; padding:12px 13px; }}
  .settle .hd {{ font-size:10px; color:var(--dim); font-weight:600; letter-spacing:.5px; display:flex; align-items:center; gap:7px; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
  .step {{ display:flex; align-items:center; gap:9px; background:#070d1e; border:1px solid #16203a; border-radius:10px; padding:8px 10px; opacity:.4; transition:.4s; }}
  .step.on {{ opacity:1; border-color:rgba(56,240,212,.4); background:rgba(56,240,212,.04); }}
  .step-ic {{ font-size:16px; }}
  .step-zone {{ font-size:12px; font-weight:700; }}
  .step-act {{ font-size:10px; color:var(--dim); margin-top:1px; line-height:1.4; }}
  .step-st {{ margin-left:auto; font-size:13px; flex-shrink:0; }}
  .step.on .step-st {{ color:var(--teal); }}
  .tag {{ font-size:10.5px; color:var(--dim); line-height:1.6; margin-top:11px; }}
  .tag b {{ color:var(--ink); font-weight:600; }}
  .done {{ margin-top:13px; text-align:center; font-size:13.5px; font-weight:700; color:var(--teal); opacity:0; transform:translateY(6px); transition:.5s; height:0; overflow:hidden; letter-spacing:.5px; }}
  .done.on {{ opacity:1; transform:none; height:auto; }}
  .idle {{ text-align:center; color:var(--dim); font-size:12.5px; padding:28px 0 10px; line-height:1.6; }}
  .idle b {{ color:var(--ink); font-weight:600; }}
</style></head>
<body>
<div class='wrap'><div class='scr'>
  <div class='top'>
    <div class='brand'>
      <div class='logo'>{v.brand_icon}</div>
      <div><small>{v.brand_small}</small><b>{v.brand_title}</b></div>
    </div>
    <div class='live'><span class='d'></span>{v.live_busy if started else v.live_idle}</div>
  </div>

  <div class='veh'>
    <div class='em'>{v.subj_emoji}</div>
    <div><div class='nm'>{v.subj_name}</div><div class='pl'>{v.subj_sub}</div></div>
    <div class='ok' id='vehok'>{v.verify_text}</div>
  </div>

  <div class='ring-row'>
    {_gauge_svg(v)}
    <div class='meta'>
      <div class='st' id='phase'>{v.phase_run}</div>
      <div class='stat'><span class='v' id='kwh'>0.0</span><span class='u'>{v.primary_unit}</span></div>
      <div class='stat cost'><span class='v' id='cost'>0 ₫</span><div class='k2'>{v.secondary_label}</div></div>
    </div>
  </div>

  <div class='settle'>
    <div class='hd'>🔒 Quyết toán an toàn xuyên chuỗi · 4 dịch vụ thành phố</div>
    <div class='grid'>{''.join(step_cards)}</div>
    <div class='tag'>{v.tagline_html}</div>
    <div class='done' id='done'>{v.done_text}</div>
  </div>
  {idle_block}
</div></div>

<script>
(function() {{
  if (!{autostart}) return;
  var DUR = {v.duration_s} * 1000;
  var gauge = '{v.gauge}';
  var startPct = {v.ring_start_pct}, endPct = {v.ring_end_pct};
  var primT = {v.primary_target}, primDec = {v.primary_decimals}, costT = {v.secondary_target};
  var stepT = [{steps_js}];
  var C = 377, fired = [false,false,false,false], t0 = null;
  var arc = document.getElementById('arc'), water = document.getElementById('water');
  var pcEl = document.getElementById('pc'), kwhEl = document.getElementById('kwh'), costEl = document.getElementById('cost');
  function vnd(n) {{ return Math.round(n).toLocaleString('vi-VN') + ' ₫'; }}
  function ease(x) {{ return 1 - Math.pow(1-x, 2); }}
  setTimeout(function() {{ var el=document.getElementById('vehok'); if(el) el.classList.add('on'); }}, 500);
  function frame(ts) {{
    if (t0 === null) t0 = ts;
    var p = Math.min(1, (ts - t0) / DUR), e = ease(p);
    if (gauge === 'ring' && arc) {{
      arc.setAttribute('stroke-dashoffset', C - C * (endPct/100) * e);
      pcEl.textContent = Math.round(startPct + (endPct-startPct)*e) + '%';
    }} else if (gauge === 'tank' && water) {{
      var h = 124 * e;
      water.setAttribute('y', 132 - h);
      water.setAttribute('height', h);
      pcEl.textContent = (primT * e).toFixed(primDec);
    }}
    kwhEl.textContent = (primT * e).toFixed(primDec);
    costEl.textContent = vnd(costT * e);
    var el = (ts - t0)/1000;
    for (var i=0;i<stepT.length;i++) {{
      if (!fired[i] && el >= stepT[i]) {{
        fired[i] = true;
        var s=document.getElementById('step'+i), st=document.getElementById('st'+i);
        if(s) s.classList.add('on'); if(st) st.textContent='✓';
      }}
    }}
    if (p < 1) requestAnimationFrame(frame);
    else {{ document.getElementById('phase').textContent='{v.phase_done}'; document.getElementById('done').classList.add('on'); }}
  }}
  requestAnimationFrame(frame);
}})();
</script>
</body></html>"""


@dataclass(frozen=True)
class ServiceSession:
    kind: str
    subj_name: str
    subj_sub: str
    amount: float
    price: int = 0

    @property
    def cost(self) -> int:
        p = self.price if self.price else SERVICE_CFG[self.kind]["price"]
        return int(round(self.amount * p))


SERVICE_CFG = {
    "metro": dict(
        brand_title="Cổng soát vé Metro", brand_icon="🚇",
        live_busy="ĐANG DI CHUYỂN", live_idle="MỜI CHẠM VÉ",
        subj_emoji="📱", verify_text="✓ Vé hợp lệ",
        gauge="ring", ring_label="HÀNH TRÌNH",
        phase_run="ĐANG DI CHUYỂN", phase_done="ĐÃ ĐẾN NƠI",
        primary_unit="ga đã qua", primary_decimals=0, secondary_label="trừ cước tự động",
        price=2400,
        steps=(("Định danh", "🪪", "Xác thực vé điện tử"),
               ("Tài chính", "💳", "Trừ cước theo chặng"),
               ("Giao thông", "🚇", "Đối soát liên tuyến"),
               ("Quản trị", "🏛️", "Trợ giá HSSV/cao tuổi")),
        tagline=("Vé nằm trên <b>chuỗi ví cá nhân</b>, mạng vận tải nằm trên "
                 "<b>chuỗi thành phố</b> — chạm một cái là qua cổng, hệ thống tự đối soát xuyên chuỗi."),
        done_text="✓ ĐÃ ĐẾN NƠI · Chúc quý khách một ngày tốt lành!",
        idle_text="Bấm <b>CHẠM VÉ & ĐI</b> để mô phỏng một lượt đi metro.",
        action_btn="🚇  Chạm vé & đi",
        amount_label="Số ga di chuyển", amount_min=2, amount_max=14,
        presets=(("Hành khách · Vé #A12", "Bến Thành → Suối Tiên", 8),
                 ("Hành khách · Vé #B07", "Bến Thành → An Sương", 11),
                 ("HSSV · Vé #S33 (trợ giá)", "Thủ Đức → Bến Thành", 6)),
    ),
    "parking": dict(
        brand_title="Bãi đỗ xe thông minh", brand_icon="🅿️",
        live_busy="ĐANG ĐỖ", live_idle="CÒN CHỖ TRỐNG",
        subj_emoji="🚙", verify_text="✓ Đã nhận diện biển số",
        gauge="ring", ring_label="PHIÊN ĐỖ",
        phase_run="ĐANG ĐỖ", phase_done="ĐÃ RỜI BÃI",
        primary_unit="giờ đã đỗ", primary_decimals=0, secondary_label="phí đỗ tự động",
        price=20000,
        steps=(("Định danh", "🚙", "Nhận diện biển số"),
               ("Giao thông", "🅿️", "Cấp & theo dõi chỗ trống"),
               ("Tài chính", "💳", "Tính phí theo giờ"),
               ("Quản trị", "🏛️", "Giá theo khu vực & giờ cao điểm")),
        tagline=("Xe nằm trên <b>chuỗi thiết bị IoT</b>, hệ thống bãi đỗ nằm trên "
                 "<b>chuỗi thành phố</b> — vào ra không cần vé giấy, hệ thống tự tính phí xuyên chuỗi."),
        done_text="✓ ĐÃ RỜI BÃI · Đã thanh toán phí đỗ, hẹn gặp lại!",
        idle_text="Bấm <b>XE VÀO BÃI</b> để mô phỏng một phiên đỗ xe.",
        action_btn="🅿️  Xe vào bãi",
        amount_label="Thời gian đỗ (giờ)", amount_min=1, amount_max=12,
        presets=(("Xe 51F-234.56", "Bãi đỗ Vincom, Quận 1", 3),
                 ("Xe 30A-998.77", "Bãi đỗ sân bay Tân Sơn Nhất", 6),
                 ("Xe 29C-112.34", "Bãi đỗ Bệnh viện Chợ Rẫy", 2)),
    ),
    "solar": dict(
        brand_title="Điện mặt trời mái nhà", brand_icon="☀️",
        live_busy="ĐANG PHÁT ĐIỆN", live_idle="ĐÃ ĐỒNG BỘ",
        subj_emoji="🏡", verify_text="✓ Đã đồng bộ hệ mái",
        gauge="ring", ring_label="HÔM NAY",
        phase_run="ĐANG PHÁT ĐIỆN", phase_done="ĐÃ CHỐT SẢN LƯỢNG",
        primary_unit="kWh bán lên lưới", primary_decimals=1, secondary_label="tiền bán điện nhận về ví",
        price=2030,
        steps=(("Năng lượng", "⚡", "Đo điện phát lên lưới"),
               ("Môi trường", "🌱", "Cấp tín chỉ carbon"),
               ("Tài chính", "💳", "Trả tiền vào ví người dân"),
               ("Quản trị", "🏛️", "Áp giá mua điện (FIT)")),
        tagline=("Hệ mái nằm trên <b>chuỗi thiết bị IoT</b>, công ty điện lực nằm trên "
                 "<b>chuỗi thành phố</b> — người dân bán điện dư lên lưới và được trả tiền tự động, xuyên chuỗi."),
        done_text="✓ ĐÃ CHỐT SẢN LƯỢNG · Tiền bán điện đã vào ví!",
        idle_text="Bấm <b>CHỐT SẢN LƯỢNG NGÀY</b> để mô phỏng một ngày bán điện lên lưới.",
        action_btn="☀️  Chốt sản lượng ngày",
        amount_label="Điện phát lên lưới (kWh)", amount_min=3, amount_max=40,
        presets=(("Hệ mái 5.5 kWp", "Nhà phố, Gò Vấp", 18),
                 ("Hệ mái 10 kWp", "Biệt thự, Quận 9", 32),
                 ("Hệ mái 3 kWp", "Nhà dân, Bình Chánh", 11)),
    ),
}


def service_view(s: ServiceSession) -> _MeterView:
    c = SERVICE_CFG[s.kind]
    return _MeterView(
        brand_small="SMART CITY", brand_title=c["brand_title"], brand_icon=c["brand_icon"],
        live_busy=c["live_busy"], live_idle=c["live_idle"],
        subj_emoji=c["subj_emoji"], subj_name=s.subj_name, subj_sub=s.subj_sub,
        verify_text=c["verify_text"], gauge=c["gauge"],
        ring_start_pct=0, ring_end_pct=100, ring_label=c["ring_label"],
        phase_run=c["phase_run"], phase_done=c["phase_done"],
        primary_target=s.amount, primary_decimals=c["primary_decimals"], primary_unit=c["primary_unit"],
        secondary_target=s.cost, secondary_label=c["secondary_label"],
        steps=c["steps"], tagline_html=c["tagline"], done_text=c["done_text"], idle_text=c["idle_text"],
    )


def render_kiosk_html(session: ChargeSession, run_id: int, started: bool) -> str:
    return _render(ev_view(session), run_id, started)


def render_service_html(session: ServiceSession, run_id: int, started: bool) -> str:
    return _render(service_view(session), run_id, started)


def render_solar_html(session: SolarSession, run_id: int, started: bool) -> str:
    return _render(solar_view(session), run_id, started)


def service_presets(kind: str) -> List[ServiceSession]:
    price = SERVICE_CFG[kind]["price"]
    return [ServiceSession(kind, name, sub, float(amt), price)
            for (name, sub, amt) in SERVICE_CFG[kind]["presets"]]


def render_water_html(session: WaterSession, run_id: int, started: bool) -> str:
    return _render(water_view(session), run_id, started)


def vehicle_presets() -> List[ChargeSession]:
    return [
        ChargeSession("VinFast VF 8", "51K-123.45", 87.7, 32, 38.0, 3858),
        ChargeSession("VinFast VF 9", "30G-678.90", 123.0, 24, 55.0, 3858),
        ChargeSession("VinFast VF e34", "29A-456.12", 42.0, 41, 22.0, 3858),
    ]


def water_presets() -> List[WaterSession]:
    return [WaterSession("ĐH-0427"), WaterSession("ĐH-1185"), WaterSession("ĐH-3390")]
