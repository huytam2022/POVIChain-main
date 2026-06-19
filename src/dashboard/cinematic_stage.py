"""Live cross-chain stage: Blockchain A -> PoVIChain internals -> Blockchain B zones.

The SVG is generated deterministically: same seed paints the same packet
trajectories and timings every time. Curved bezier paths, per-packet variable
speed, fade-in/out, and ambient heartbeat pulses combine to make the system
feel alive without using random or Gaussian noise.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Sequence, Tuple


ZONES: Tuple[str, ...] = ("Identity", "Finance", "Traffic", "Energy", "Environment", "Governance")

ZONE_VN = {
    "Identity": "Định danh",
    "Finance": "Tài chính",
    "Traffic": "Giao thông",
    "Energy": "Năng lượng",
    "Environment": "Môi trường",
    "Governance": "Quản trị",
}

STAGE_W = 1320
STAGE_H = 640

CHAIN_A_X = 40
CHAIN_A_Y = 60
CHAIN_A_W = 210
CHAIN_A_H = 520

POVI_X = 290
POVI_Y = 60
POVI_W = 540
POVI_H = 520

CHAIN_B_X = 880
CHAIN_B_Y = 60
CHAIN_B_W = 400
CHAIN_B_H = 520

ZONE_X = CHAIN_B_X + 22
ZONE_Y = CHAIN_B_Y + 110
ZONE_W = CHAIN_B_W - 44
ZONE_GAP = 8

PROVE_X = POVI_X + 30
PROVE_Y = POVI_Y + 130
PROVE_W = 200
PROVE_H = 96

COMMITTEE_X = POVI_X + 300
COMMITTEE_Y = POVI_Y + 130
COMMITTEE_W = 220
COMMITTEE_H = 96

DISPATCH_X = POVI_X + 140
DISPATCH_Y = POVI_Y + 340
DISPATCH_W = 260
DISPATCH_H = 96


@dataclass(frozen=True)
class TxPacket:
    idx: int
    zone_idx: int
    zone: str
    tx_hash: str
    begin_s: float
    dur_s: float
    backend: str
    src_y: int
    speed_var: float
    action: str = ""
    vehicle: int = 0


ZONE_INDEX = {name: i for i, name in enumerate(ZONES)}

EV_STEPS: Tuple[Tuple[str, str], ...] = (
    ("Identity", "Xác thực xe"),
    ("Energy", "Đo điện năng"),
    ("Finance", "Thanh toán"),
    ("Traffic", "Tín dụng phí đỗ"),
)


def _det_byte(seed: str, label: str, idx: int) -> int:
    return hashlib.sha256(f"{seed}|{label}|{idx}".encode("utf-8")).digest()[0]


def _det_unit(seed: str, label: str, idx: int) -> float:
    h = hashlib.sha256(f"{seed}|{label}|{idx}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") / (2 ** 32)


def _hash_short(seed: str, idx: int) -> str:
    h = hashlib.sha256(f"TX|{seed}|{idx}".encode("utf-8")).digest()
    return "0x" + h[:4].hex()


def build_batch(
    seed: str,
    batch_size: int,
    base_dur_s: float = 4.5,
    spawn_window_s: float = 1.2,
) -> List[TxPacket]:
    out: List[TxPacket] = []
    rows = max(batch_size, 1)
    for i in range(batch_size):
        z = _det_byte(seed, "zone", i) % len(ZONES)
        backend = "STARK" if (_det_byte(seed, "be", i) % 7 == 0) else "Groth16"
        spawn = (_det_unit(seed, "spawn", i)) * spawn_window_s
        speed_var = (_det_unit(seed, "speed", i) - 0.5) * 0.5
        dur = max(2.4, base_dur_s * (1.0 + speed_var))
        row_band = CHAIN_A_H - 160
        row_step = row_band / max(rows, 1)
        src_y = int(CHAIN_A_Y + 130 + (i % rows) * row_step)
        out.append(
            TxPacket(
                idx=i,
                zone_idx=z,
                zone=ZONES[z],
                tx_hash=_hash_short(seed, i),
                begin_s=round(spawn, 3),
                dur_s=round(dur, 3),
                backend=backend,
                src_y=src_y,
                speed_var=round(speed_var, 3),
            )
        )
    return out


def build_ev_session(
    seed: str,
    vehicles: int,
    base_dur_s: float = 4.8,
    spawn_window_s: float = 2.2,
) -> List[TxPacket]:
    """A smart-charging hub: each EV that plugs in emits a small cross-chain
    bundle that settles through Identity -> Energy -> Finance, plus an occasional
    Traffic (parking credit), Environment (carbon ledger) or Governance (subsidy)
    step. Fully deterministic from the seed."""
    out: List[TxPacket] = []
    idx = 0
    for v in range(max(vehicles, 1)):
        steps: List[Tuple[str, str]] = [
            ("Identity", "Xác thực xe"),
            ("Energy", "Đo điện năng"),
            ("Finance", "Thanh toán"),
        ]
        if _det_byte(seed, "park", v) % 2 == 0:
            steps.append(("Traffic", "Tín dụng phí đỗ"))
        if _det_byte(seed, "carbon", v) % 3 == 0:
            steps.append(("Environment", "Ghi nhận carbon"))
        if _det_byte(seed, "subsidy", v) % 5 == 0:
            steps.append(("Governance", "Trợ giá điện sạch"))
        for s, (zname, action) in enumerate(steps):
            z = ZONE_INDEX[zname]
            backend = "STARK" if (_det_byte(seed, "be", idx) % 7 == 0) else "Groth16"
            base_spawn = _det_unit(seed, "spawn", v) * spawn_window_s
            spawn = base_spawn + s * 0.42
            speed_var = (_det_unit(seed, "speed", idx) - 0.5) * 0.4
            dur = max(2.6, base_dur_s * (1.0 + speed_var))
            src_y = int(CHAIN_A_Y + 130 + (v % max(vehicles, 1)) * ((CHAIN_A_H - 200) / max(vehicles, 1)))
            out.append(
                TxPacket(
                    idx=idx,
                    zone_idx=z,
                    zone=zname,
                    tx_hash=_hash_short(seed, idx),
                    begin_s=round(spawn, 3),
                    dur_s=round(dur, 3),
                    backend=backend,
                    src_y=src_y,
                    speed_var=round(speed_var, 3),
                    action=action,
                    vehicle=v + 1,
                )
            )
            idx += 1
    return out


def zone_tally(packets: Sequence[TxPacket]) -> List[int]:
    counts = [0] * len(ZONES)
    for p in packets:
        counts[p.zone_idx] += 1
    return counts


def _zone_box_y(i: int) -> Tuple[float, float]:
    n = len(ZONES)
    inner_h = CHAIN_B_H - 130
    h = (inner_h - (n - 1) * ZONE_GAP) / n
    return ZONE_Y + i * (h + ZONE_GAP), h


def _zone_center(i: int) -> Tuple[float, float]:
    y, h = _zone_box_y(i)
    return ZONE_X + ZONE_W / 2, y + h / 2


def _zone_landing(i: int) -> Tuple[float, float]:
    y, h = _zone_box_y(i)
    return ZONE_X + 34, y + h / 2


def _stage_centers() -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    return (
        (PROVE_X + PROVE_W / 2, PROVE_Y + PROVE_H / 2),
        (COMMITTEE_X + COMMITTEE_W / 2, COMMITTEE_Y + COMMITTEE_H / 2),
        (DISPATCH_X + DISPATCH_W / 2, DISPATCH_Y + DISPATCH_H / 2),
    )


def _packet_path_d(packet: TxPacket) -> str:
    src = (CHAIN_A_X + CHAIN_A_W - 8, packet.src_y)
    prove, committee, dispatch = _stage_centers()
    land = _zone_landing(packet.zone_idx)
    c1 = (src[0] + 90, src[1])
    c2 = (prove[0] - 60, prove[1])
    c3 = (prove[0] + 80, prove[1] - 18)
    c4 = (committee[0] - 70, committee[1] - 12)
    c5 = (committee[0] - 10, committee[1] + 70)
    c6 = (dispatch[0] + 40, dispatch[1] - 24)
    c7 = (dispatch[0] + 140, dispatch[1] + 6)
    c8 = (land[0] - 80, land[1])
    return (
        f"M {src[0]:.1f} {src[1]:.1f} "
        f"C {c1[0]:.1f} {c1[1]:.1f}, {c2[0]:.1f} {c2[1]:.1f}, {prove[0]:.1f} {prove[1]:.1f} "
        f"C {c3[0]:.1f} {c3[1]:.1f}, {c4[0]:.1f} {c4[1]:.1f}, {committee[0]:.1f} {committee[1]:.1f} "
        f"C {c5[0]:.1f} {c5[1]:.1f}, {c6[0]:.1f} {c6[1]:.1f}, {dispatch[0]:.1f} {dispatch[1]:.1f} "
        f"C {c7[0]:.1f} {c7[1]:.1f}, {c8[0]:.1f} {c8[1]:.1f}, {land[0]:.1f} {land[1]:.1f}"
    )


def _key_pacing(backend: str) -> Tuple[str, str]:
    if backend == "STARK":
        kt = "0;0.20;0.36;0.52;0.60;0.76;0.84;1"
    else:
        kt = "0;0.22;0.30;0.50;0.56;0.74;0.80;1"
    kp = "0;0.25;0.25;0.50;0.50;0.75;0.75;1"
    return kt, kp


def _packet_svg(packet: TxPacket, loop: bool) -> str:
    color = "#38f0d4" if packet.backend == "Groth16" else "#b56cff"
    repeat = "indefinite" if loop else "1"
    fill = "freeze" if not loop else "remove"
    begin = f"{packet.begin_s:.2f}s"
    dur = f"{packet.dur_s:.2f}s"
    kt, kp = _key_pacing(packet.backend)
    path_d = _packet_path_d(packet)
    trail_begin_1 = f"{packet.begin_s + 0.08:.2f}s"
    trail_begin_2 = f"{packet.begin_s + 0.18:.2f}s"
    return f"""
<g>
  <path d='{path_d}' fill='none' stroke='{color}' stroke-opacity='0.10' stroke-width='1.2'/>
  <circle r='10' fill='{color}' opacity='0.95' style='filter: drop-shadow(0 0 14px {color});'>
    <animate attributeName='opacity'
             values='0;0.4;1;1;1;1;1;0.95;0'
             keyTimes='0;0.03;0.06;0.43;0.51;0.63;0.71;0.92;1'
             dur='{dur}' begin='{begin}' repeatCount='{repeat}' fill='{fill}'/>
    <animate attributeName='r'
             values='5;9;11;7;11;7;11;7;4'
             keyTimes='0;0.03;0.06;0.43;0.51;0.63;0.71;0.92;1'
             dur='{dur}' begin='{begin}' repeatCount='{repeat}' fill='{fill}'/>
    <animateMotion path='{path_d}' dur='{dur}' begin='{begin}' repeatCount='{repeat}' rotate='auto'
                   calcMode='linear' keyTimes='{kt}' keyPoints='{kp}' fill='{fill}'/>
  </circle>
  <circle r='5' fill='{color}' opacity='0.5' style='filter: drop-shadow(0 0 8px {color});'>
    <animate attributeName='opacity'
             values='0;0;0.45;0.6;0.45;0'
             keyTimes='0;0.05;0.20;0.5;0.85;1'
             dur='{dur}' begin='{trail_begin_1}' repeatCount='{repeat}' fill='{fill}'/>
    <animateMotion path='{path_d}' dur='{dur}' begin='{trail_begin_1}' repeatCount='{repeat}' rotate='auto'
                   calcMode='linear' keyTimes='{kt}' keyPoints='{kp}' fill='{fill}'/>
  </circle>
  <circle r='3' fill='{color}' opacity='0.4' style='filter: drop-shadow(0 0 5px {color});'>
    <animate attributeName='opacity'
             values='0;0;0.30;0.40;0.30;0'
             keyTimes='0;0.05;0.20;0.5;0.85;1'
             dur='{dur}' begin='{trail_begin_2}' repeatCount='{repeat}' fill='{fill}'/>
    <animateMotion path='{path_d}' dur='{dur}' begin='{trail_begin_2}' repeatCount='{repeat}' rotate='auto'
                   calcMode='linear' keyTimes='{kt}' keyPoints='{kp}' fill='{fill}'/>
  </circle>
</g>
"""


def _scan_bar(x: float, y: float, w: float, color: str, dur: float) -> str:
    bar_w = 60.0
    return f"""
<rect x='{x:.0f}' y='{y:.0f}' width='{bar_w:.0f}' height='3' rx='2' fill='{color}' opacity='0.7' style='filter: drop-shadow(0 0 6px {color});'>
  <animate attributeName='x' values='{x};{x + w - bar_w};{x}' dur='{dur:.2f}s' repeatCount='indefinite'/>
  <animate attributeName='opacity' values='0.4;1;0.4' dur='{dur:.2f}s' repeatCount='indefinite'/>
</rect>
"""


def _ring(cx: float, cy: float, color: str, begin: float, dur: float, r_from: float, r_to: float) -> str:
    return f"""
<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{r_from:.0f}' stroke='{color}' stroke-width='2' fill='none' opacity='0'>
  <animate attributeName='r'       values='{r_from};{r_to};{r_from}' dur='{dur:.2f}s' begin='{begin:.2f}s' repeatCount='indefinite'/>
  <animate attributeName='opacity' values='0;0.55;0'                  dur='{dur:.2f}s' begin='{begin:.2f}s' repeatCount='indefinite'/>
</circle>
"""


def _heartbeat_dot(cx: float, cy: float, color: str, begin: float, dur: float, r: float = 5.0) -> str:
    return f"""
<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{r}' fill='{color}' opacity='0.5' style='filter: drop-shadow(0 0 8px {color});'>
  <animate attributeName='opacity' values='0.3;1;0.3' dur='{dur:.2f}s' begin='{begin:.2f}s' repeatCount='indefinite'/>
  <animate attributeName='r'       values='{r-1};{r+2};{r-1}' dur='{dur:.2f}s' begin='{begin:.2f}s' repeatCount='indefinite'/>
</circle>
"""


def _label(x: float, y: float, text: str, size: int = 13, fill: str = "#cfd6ea", weight: int = 600, anchor: str = "start") -> str:
    return f"<text x='{x:.0f}' y='{y:.0f}' text-anchor='{anchor}' fill='{fill}' font-family='Inter, system-ui' font-size='{size}' font-weight='{weight}'>{text}</text>"


def _box(x: float, y: float, w: float, h: float, stroke: str, fill: str = "#0c1224", radius: int = 14, opacity: float = 1.0) -> str:
    return f"<rect x='{x:.0f}' y='{y:.0f}' width='{w:.0f}' height='{h:.0f}' rx='{radius}' fill='{fill}' stroke='{stroke}' stroke-width='1.5' opacity='{opacity}'/>"


def _starfield(seed: str = "stars") -> str:
    cells: List[str] = []
    for i in range(60):
        x = int(_det_unit(seed, "x", i) * STAGE_W)
        y = int(_det_unit(seed, "y", i) * STAGE_H)
        r = 0.6 + _det_unit(seed, "r", i) * 0.9
        begin = _det_unit(seed, "b", i) * 3.0
        op_a = 0.05 + _det_unit(seed, "oa", i) * 0.20
        op_b = 0.15 + _det_unit(seed, "ob", i) * 0.30
        cells.append(
            f"<circle cx='{x}' cy='{y}' r='{r:.1f}' fill='#cfd6ea'>"
            f"<animate attributeName='opacity' values='{op_a:.2f};{op_b:.2f};{op_a:.2f}' dur='3.6s' begin='{begin:.2f}s' repeatCount='indefinite'/>"
            f"</circle>"
        )
    return "".join(cells)


def render_stage_svg(packets: Sequence[TxPacket], loop: bool = True) -> str:
    prove, committee, dispatch = _stage_centers()
    chain_a_pulse = (CHAIN_A_X + CHAIN_A_W / 2, CHAIN_A_Y + 90)
    zone_centers = [_zone_center(i) for i in range(len(ZONES))]

    queue_rows: List[str] = []
    show_n = min(len(packets), 9)
    for i, p in enumerate(packets[:show_n]):
        y = CHAIN_A_Y + 130 + i * 36
        zvn = ZONE_VN.get(p.zone, p.zone)
        left = p.action if p.action else p.tx_hash
        right = ("xe " + str(p.vehicle) + " → " + zvn) if p.action else ("→ " + zvn)
        queue_rows.append(_box(CHAIN_A_X + 14, y - 15, CHAIN_A_W - 28, 31, "#1f405e", "#0a1d33", 7, 0.85))
        queue_rows.append(_label(CHAIN_A_X + 26, y + 0, left, size=11, fill="#cfd6ea", weight=600))
        queue_rows.append(_label(CHAIN_A_X + 26, y + 13, right, size=9, fill="#7d8aa6", weight=500))

    if len(packets) > show_n:
        queue_rows.append(_label(CHAIN_A_X + CHAIN_A_W / 2, CHAIN_A_Y + CHAIN_A_H - 16, f"+ {len(packets) - show_n} giao dịch khác", size=11, fill="#7d8aa6", anchor="middle", weight=600))

    zone_blocks: List[str] = []
    for i, zname in enumerate(ZONES):
        y, h = _zone_box_y(i)
        zone_blocks.append(_box(ZONE_X, y, ZONE_W, h, "#6d8bff", "#0c1532", 10, 0.95))
        zone_blocks.append(_label(ZONE_X + 60, y + h / 2 - 4, "VÙNG", size=9, fill="#7d8cc4", weight=700))
        zone_blocks.append(_label(ZONE_X + 60, y + h / 2 + 14, ZONE_VN.get(zname, zname), size=15, fill="#fff", weight=700))
        zone_blocks.append(_ring(ZONE_X + 34, y + h / 2, "#6d8bff", 0.2 * i, 2.6, 8, 20))
        zone_blocks.append(_heartbeat_dot(ZONE_X + 34, y + h / 2, "#6d8bff", 0.15 * i, 2.4, r=5))

    stage_rings: List[str] = [
        _ring(chain_a_pulse[0], chain_a_pulse[1], "#38f0d4", 0.0, 3.0, 14, 40),
        _heartbeat_dot(chain_a_pulse[0], chain_a_pulse[1], "#38f0d4", 0.0, 2.4),
        _ring(prove[0], prove[1], "#b56cff", 0.4, 2.4, 18, 50),
        _heartbeat_dot(prove[0], prove[1], "#b56cff", 0.2, 2.4),
        _ring(committee[0], committee[1], "#b56cff", 0.8, 2.4, 18, 52),
        _heartbeat_dot(committee[0], committee[1], "#b56cff", 0.5, 2.4),
        _ring(dispatch[0], dispatch[1], "#6d8bff", 1.2, 2.6, 18, 54),
        _heartbeat_dot(dispatch[0], dispatch[1], "#6d8bff", 0.7, 2.4),
    ]

    arrow_paths: List[str] = []
    arrow_paths.append(
        f"<path d='M {PROVE_X + PROVE_W:.0f} {prove[1]:.0f} C {prove[0] + 90:.0f} {prove[1] - 10:.0f}, {committee[0] - 80:.0f} {committee[1] + 6:.0f}, {COMMITTEE_X:.0f} {committee[1]:.0f}' fill='none' stroke='rgba(181,108,255,0.20)' stroke-width='2' stroke-dasharray='6 5'/>"
    )
    arrow_paths.append(
        f"<path d='M {committee[0]:.0f} {COMMITTEE_Y + COMMITTEE_H:.0f} C {committee[0]:.0f} {committee[1] + 100:.0f}, {dispatch[0] + 30:.0f} {dispatch[1] - 80:.0f}, {dispatch[0]:.0f} {DISPATCH_Y:.0f}' fill='none' stroke='rgba(109,139,255,0.22)' stroke-width='2' stroke-dasharray='6 5'/>"
    )

    packet_svgs = [_packet_svg(p, loop) for p in packets]

    return f"""
<svg viewBox='0 0 {STAGE_W} {STAGE_H}' xmlns='http://www.w3.org/2000/svg' preserveAspectRatio='xMidYMid meet'>
  <defs>
    <linearGradient id='gradA' x1='0' x2='0' y1='0' y2='1'>
      <stop offset='0' stop-color='#0e2a44'/><stop offset='1' stop-color='#06121f'/>
    </linearGradient>
    <linearGradient id='gradP' x1='0' x2='1'>
      <stop offset='0' stop-color='#180b2a'/><stop offset='1' stop-color='#11061f'/>
    </linearGradient>
    <linearGradient id='gradZ' x1='0' x2='0' y1='0' y2='1'>
      <stop offset='0' stop-color='#0c1532'/><stop offset='1' stop-color='#070d24'/>
    </linearGradient>
    <radialGradient id='vignette' cx='50%' cy='50%' r='75%'>
      <stop offset='60%' stop-color='rgba(0,0,0,0)'/>
      <stop offset='100%' stop-color='rgba(0,0,0,0.7)'/>
    </radialGradient>
  </defs>

  <rect x='0' y='0' width='{STAGE_W}' height='{STAGE_H}' fill='#04050d'/>
  {_starfield()}

  <rect x='{CHAIN_A_X}' y='{CHAIN_A_Y}' width='{CHAIN_A_W}' height='{CHAIN_A_H}' rx='18' fill='url(#gradA)' stroke='#38f0d4' stroke-opacity='0.55'/>
  {_label(CHAIN_A_X + CHAIN_A_W / 2, CHAIN_A_Y + 34, "CHUỖI NGUỒN", size=10, fill="#88f0d4", weight=700, anchor="middle")}
  {_label(CHAIN_A_X + CHAIN_A_W / 2, CHAIN_A_Y + 62, "Xe &amp; thiết bị IoT", size=18, fill="#ffffff", weight=800, anchor="middle")}
  {_label(CHAIN_A_X + CHAIN_A_W / 2, CHAIN_A_Y + 88, "trạm sạc · cảm biến biên", size=11, fill="#9bb2c6", anchor="middle")}
  {''.join(queue_rows)}

  <rect x='{POVI_X}' y='{POVI_Y}' width='{POVI_W}' height='{POVI_H}' rx='18' fill='url(#gradP)' stroke='#b56cff' stroke-opacity='0.5'/>
  {_label(POVI_X + POVI_W / 2, POVI_Y + 34, "LÕI XÁC MINH LIÊN CHUỖI", size=10, fill="#d9bcff", weight=700, anchor="middle")}
  {_label(POVI_X + POVI_W / 2, POVI_Y + 62, "Xác minh lai · Đồng thuận danh tiếng · Smart Zone", size=15, fill="#ffffff", weight=700, anchor="middle")}
  {_label(POVI_X + POVI_W / 2, POVI_Y + 88, "tạo chứng cứ bất đồng bộ · xác minh hằng số trên thiết bị biên · định tuyến theo vùng", size=11, fill="#bcb0d4", anchor="middle")}

  {''.join(arrow_paths)}

  {_box(PROVE_X, PROVE_Y, PROVE_W, PROVE_H, "#b56cff")}
  {_label(PROVE_X + 14, PROVE_Y + 24, "BƯỚC 1", size=10, fill="#d9bcff", weight=700)}
  {_label(PROVE_X + 14, PROVE_Y + 50, "Trích gói bằng chứng", size=15, fill="#fff", weight=700)}
  {_label(PROVE_X + 14, PROVE_Y + 72, "ZKP + Merkle + mã vùng", size=11, fill="#bcb0d4")}
  {_label(PROVE_X + 14, PROVE_Y + 88, "nằm ngoài đường tới hạn", size=10, fill="#7d6a98")}

  {_box(COMMITTEE_X, COMMITTEE_Y, COMMITTEE_W, COMMITTEE_H, "#b56cff")}
  {_label(COMMITTEE_X + 14, COMMITTEE_Y + 24, "BƯỚC 2", size=10, fill="#d9bcff", weight=700)}
  {_label(COMMITTEE_X + 14, COMMITTEE_Y + 50, "Ủy ban VRF xác minh", size=15, fill="#fff", weight=700)}
  {_label(COMMITTEE_X + 14, COMMITTEE_Y + 72, "danh tiếng quyết định cỡ ủy ban", size=11, fill="#bcb0d4")}
  {_label(COMMITTEE_X + 14, COMMITTEE_Y + 88, "luân chuyển mỗi epoch", size=10, fill="#7d6a98")}

  {_box(DISPATCH_X, DISPATCH_Y, DISPATCH_W, DISPATCH_H, "#6d8bff")}
  {_label(DISPATCH_X + 14, DISPATCH_Y + 24, "BƯỚC 3", size=10, fill="#aab8ff", weight=700)}
  {_label(DISPATCH_X + 14, DISPATCH_Y + 50, "Bộ điều phối Smart Zone", size=15, fill="#fff", weight=700)}
  {_label(DISPATCH_X + 14, DISPATCH_Y + 72, "mã vùng gắn cứng vào bằng chứng", size=11, fill="#aab8ff")}
  {_label(DISPATCH_X + 14, DISPATCH_Y + 88, "không định tuyến lại · cô lập sự cố", size=10, fill="#5d75b0")}

  {_scan_bar(PROVE_X + 12,     PROVE_Y     + PROVE_H     - 12, PROVE_W     - 24, "#b56cff", 3.4)}
  {_scan_bar(COMMITTEE_X + 12, COMMITTEE_Y + COMMITTEE_H - 12, COMMITTEE_W - 24, "#b56cff", 2.6)}
  {_scan_bar(DISPATCH_X + 12,  DISPATCH_Y  + DISPATCH_H  - 12, DISPATCH_W  - 24, "#6d8bff", 2.0)}

  {''.join(stage_rings)}

  <rect x='{CHAIN_B_X}' y='{CHAIN_B_Y}' width='{CHAIN_B_W}' height='{CHAIN_B_H}' rx='18' fill='url(#gradZ)' stroke='#6d8bff' stroke-opacity='0.55'/>
  {_label(CHAIN_B_X + CHAIN_B_W / 2, CHAIN_B_Y + 34, "CHUỖI DỊCH VỤ THÀNH PHỐ", size=10, fill="#aab8ff", weight=700, anchor="middle")}
  {_label(CHAIN_B_X + CHAIN_B_W / 2, CHAIN_B_Y + 62, "Smart City Services", size=18, fill="#ffffff", weight=800, anchor="middle")}
  {_label(CHAIN_B_X + CHAIN_B_W / 2, CHAIN_B_Y + 88, "6 Smart Zone · quyết toán cô lập theo vùng", size=11, fill="#9bb2c6", anchor="middle")}
  {''.join(zone_blocks)}

  {''.join(packet_svgs)}

  <rect x='0' y='0' width='{STAGE_W}' height='{STAGE_H}' fill='url(#vignette)' pointer-events='none'/>
</svg>
"""


def stage_legend_html() -> str:
    return (
        "<div class='stage-legend'>"
        "<span><span class='dot acc'></span>Giao dịch Groth16</span>"
        "<span><span class='dot pri'></span>Giao dịch STARK</span>"
        "<span><span class='dot p2'></span>Đã quyết toán tại một Smart Zone</span>"
        "<span style='color:#7d8aa6;'>· Mỗi chấm sáng là một bước trong phiên sạc xe đang được xử lý xuyên chuỗi.</span>"
        "</div>"
    )


def zone_tally_html(counts: Sequence[int]) -> str:
    cells = []
    for name, n in zip(ZONES, counts):
        empty = " empty" if n == 0 else ""
        cells.append(
            f"<div class='z{empty}'><div class='nm'>{name}</div><div class='ct'>{n}</div></div>"
        )
    return "<div class='zone-tally'>" + "".join(cells) + "</div>"


def stage_kpi_html(items: Sequence[Tuple[str, str, str]]) -> str:
    blocks = "".join(
        f"<div class='stage-kpi'><div class='k'>{k}</div><div class='v'>{v}</div><div class='s'>{s}</div></div>"
        for k, v, s in items
    )
    return f"<div class='stage-controls'>{blocks}</div>"
