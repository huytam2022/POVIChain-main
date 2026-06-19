"""Smart-city demo — login-gated, role-routed.

  admin / operator  →  🛠️  Operator console
  dan               →  👤  Citizen services  +  🔔 Thông báo truy xuất
  dvtx              →  🔐  Privacy requester (ZK query)
"""
from __future__ import annotations

from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from dashboard.kiosk_stage import (
    ChargeSession, WaterSession, ServiceSession, SolarSession,
    render_kiosk_html, render_water_html, render_service_html, render_solar_html,
    SERVICE_CFG,
)
from dashboard.roles_stage import (
    render_admin_html, render_privacy_html, render_subject_html,
    VERIFY_TYPES, verify, authenticate,
)
from dashboard.theme import inject_cinematic

st.set_page_config(page_title="Smart City · Dịch vụ liên chuỗi", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")
inject_cinematic()

SCENARIOS = {
    "⚡ Trạm sạc xe điện": "ev",
    "💧 Đồng hồ nước":     "water",
    "🚇 Metro tap-and-go": "metro",
    "🅿️ Bãi đỗ xe":        "parking",
    "☀️ Điện mặt trời":    "solar",
}
DMIN, DMAX = date(1950, 1, 1), date(2100, 1, 1)

_ZONES_LIST = ["Định danh", "Tài chính", "Giao thông", "Năng lượng", "Môi trường", "Quản trị"]

_DEFAULT_NODES = [
    {"id": "Node #001", "rep": 0.94, "zone": "Định danh",  "status": "active",    "note": "Hoạt động bình thường"},
    {"id": "Node #047", "rep": 0.31, "zone": "Năng lượng", "status": "penalized", "note": "Đề xuất khối không hợp lệ — đã bị phạt"},
    {"id": "Node #218", "rep": 0.58, "zone": "Tài chính",  "status": "watch",     "note": "Bỏ phiếu mâu thuẫn — đang theo dõi"},
    {"id": "Node #312", "rep": 0.89, "zone": "Giao thông", "status": "active",    "note": "Hoạt động bình thường"},
    {"id": "Node #455", "rep": 0.91, "zone": "Môi trường", "status": "active",    "note": "Trong ủy ban epoch này"},
    {"id": "Node #502", "rep": 0.77, "zone": "Quản trị",   "status": "active",    "note": "Hoạt động bình thường"},
]

_STATUS_ICON  = {"active": "🟢", "penalized": "🔴", "watch": "🟡", "removed": "⚫"}
_STATUS_LABEL = {"active": "Hoạt động", "penalized": "Bị phạt", "watch": "Theo dõi", "removed": "Đã xóa"}

for k, d in (
    ("auth_role", None), ("auth_name", None),
    ("scn", list(SCENARIOS)[0]),
    ("started", False), ("run_id", 0),
    ("query_log", []), ("_last_query_run_id", -1),
    ("_last_scn", None), ("_last_vtype", list(VERIFY_TYPES)[0]),
    ("network_nodes", None), ("penalty_log", []), ("_node_counter", 600),
):
    st.session_state.setdefault(k, d)

if st.session_state["network_nodes"] is None:
    st.session_state["network_nodes"] = [dict(n) for n in _DEFAULT_NODES]


def _start():
    st.session_state["started"] = True
    st.session_state["run_id"] += 1


def _logout():
    for k in ("auth_role", "auth_name", "started", "scn", "run_id",
              "_last_scn", "_last_vtype"):
        st.session_state[k] = {"started": False, "run_id": 0,
                                "scn": list(SCENARIOS)[0],
                                "_last_vtype": list(VERIFY_TYPES)[0],
                                "_last_scn": None,
                                "auth_role": None,
                                "auth_name": None}.get(k)


def _banner(icon, parts):
    st.markdown(
        f"<div class='tx-banner'>{icon}&nbsp; {parts}</div>",
        unsafe_allow_html=True)


def _vnd(n):
    return f"{int(n):,}".replace(",", ".") + " ₫"


if not st.session_state["auth_role"]:
    st.markdown(
        """<style>
        section[data-testid="stMain"] .block-container {
          max-width: 430px !important;
          min-height: 90vh;
          display: flex; flex-direction: column; justify-content: center;
          padding-top: 0 !important; padding-bottom: 0 !important;
        }
        </style>""",
        unsafe_allow_html=True)

    st.markdown(
        "<div class='login-mark'>◈</div>"
        "<div class='login-eyebrow'>Smart City · Nền tảng liên chuỗi</div>"
        "<div class='login-title'>Đăng nhập hệ thống</div>"
        "<div class='login-sub'>Chọn vai trò để truy cập dịch vụ tương ứng</div>",
        unsafe_allow_html=True)

    with st.form("login_main"):
        u = st.text_input("Tài khoản", placeholder="username")
        p = st.text_input("Mật khẩu", type="password", placeholder="••••••••")
        submitted = st.form_submit_button(
            "Đăng nhập", type="primary", use_container_width=True)
    if submitted:
        acc = authenticate(u, p)
        if acc:
            st.session_state["auth_role"] = acc["role"]
            st.session_state["auth_name"] = acc["name"]
            st.rerun()
        else:
            st.error("Sai tài khoản hoặc mật khẩu.")

    st.markdown(
        "<div class='login-hint'>"
        "admin / admin@2026 &nbsp;·&nbsp; operator / op@2026<br>"
        "dan / dan123 &nbsp;·&nbsp; dvtx / dvtx@2026"
        "</div>",
        unsafe_allow_html=True)
    st.stop()


role = st.session_state["auth_role"]
name = st.session_state["auth_name"]

_ROLE_ICON = {"admin": "🛠️", "citizen": "👤", "requester": "🔐"}
_ROLE_LABEL = {
    "admin":     "Quản trị viên",
    "citizen":   "Người dân",
    "requester": "Dịch vụ truy xuất",
}

hL, hR = st.columns([5, 1])
hL.markdown(
    f"<div class='app-bar'>"
    f"<div class='app-bar-left'>"
    f"<div class='app-bar-mark'>◈</div>"
    f"<div>"
    f"<div class='app-bar-eyebrow'>Smart City · Nền tảng liên chuỗi</div>"
    f"<div class='app-bar-name'>{_ROLE_ICON[role]} {name}"
    f"<span class='app-bar-role'>{_ROLE_LABEL[role]}</span></div>"
    f"</div></div></div>",
    unsafe_allow_html=True)
if hR.button("Đăng xuất", use_container_width=True):
    _logout()
    st.rerun()


if role == "admin":
    t_overview, t_members, t_penalty = st.tabs([
        "📊 Tổng quan mạng",
        "👥 Quản lý thành viên",
        "⚠️ Xử phạt thủ công",
    ])

    with t_overview:
        components.html(render_admin_html(st.session_state["run_id"]),
                        height=640, scrolling=False)

    with t_members:
        nodes = st.session_state["network_nodes"]
        visible = [n for n in nodes if n["status"] != "removed"]

        active_cnt    = sum(1 for n in visible if n["status"] == "active")
        penalized_cnt = sum(1 for n in visible if n["status"] == "penalized")
        st.markdown(
            f"<div style='font-size:12.5px;color:var(--text-2);margin:4px 0 14px;'>"
            f"<b style='color:var(--text)'>{len(visible)}</b> node trong mạng"
            + (f" · <span style='color:var(--good)'>{active_cnt} hoạt động</span>" if active_cnt else "")
            + (f" · <span style='color:var(--bad)'>{penalized_cnt} đang bị phạt</span>" if penalized_cnt else "")
            + "</div>",
            unsafe_allow_html=True)

        def _rep_color(r):
            return "var(--good)" if r >= 0.7 else ("var(--warn)" if r >= 0.5 else "var(--bad)")
        def _node_row(n):
            rep = n["rep"]; rc = _rep_color(rep)
            icon = _STATUS_ICON.get(n["status"], "⚪")
            label = _STATUS_LABEL.get(n["status"], n["status"])
            return (
                "<tr>"
                f"<td><span class='id-chip'>{n['id']}</span></td>"
                f"<td style='color:var(--text);font-size:13px'>{n['zone']}</td>"
                f"<td><span class='rep-bar'><span class='rep-fill' style='width:{min(rep,1)*100:.0f}%;background:{rc}'></span></span>"
                f"<b style='color:{rc};font-variant-numeric:tabular-nums;font-size:13px'>{rep:.2f}</b></td>"
                f"<td style='font-size:13px'>{icon} <span style='color:var(--text)'>{label}</span></td>"
                f"<td style='color:var(--text-2);font-size:12px'>{n['note']}</td>"
                "</tr>"
            )
        rows_html = "".join(_node_row(n) for n in visible)
        st.markdown(
            f"<table class='node-tbl'><thead><tr>"
            f"<th>Node ID</th><th>Smart Zone</th><th>Danh tiếng</th><th>Trạng thái</th><th>Ghi chú</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table>",
            unsafe_allow_html=True)

        st.markdown("<div class='inner-sect'>Xóa node</div>", unsafe_allow_html=True)
        del_ids = [n["id"] for n in visible]
        dc1, dc2 = st.columns([3, 1])
        del_pick = dc1.selectbox("Chọn node cần xóa", del_ids, label_visibility="collapsed")
        if dc2.button("Xóa khỏi mạng", type="secondary", use_container_width=True):
            for n in nodes:
                if n["id"] == del_pick:
                    n["status"] = "removed"
                    st.rerun()

        st.markdown("<div class='inner-sect'>Thêm node mới</div>", unsafe_allow_html=True)
        with st.expander("Cấu hình & thêm vào mạng", expanded=False):
            with st.form("add_node_form", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                new_zone = col1.selectbox("Smart Zone phụ trách", _ZONES_LIST)
                new_rep  = col2.slider("Danh tiếng ban đầu", 0.50, 1.00, 0.75, 0.01)
                new_note = col3.text_input("Ghi chú", placeholder="Mô tả node")
                if st.form_submit_button("Thêm vào mạng", type="primary"):
                    ctr = st.session_state["_node_counter"] + 1
                    st.session_state["_node_counter"] = ctr
                    st.session_state["network_nodes"].append({
                        "id":     f"Node #{ctr}",
                        "rep":    new_rep,
                        "zone":   new_zone,
                        "status": "active",
                        "note":   new_note.strip() or "Vừa tham gia mạng",
                    })
                    st.rerun()

    with t_penalty:
        nodes = st.session_state["network_nodes"]
        candidates = [n for n in nodes if n["status"] != "removed"]

        st.markdown(
            "<div style='font-size:12.5px;color:var(--text-2);margin:4px 0 10px;'>"
            "Chọn node vi phạm, nhập lý do và xác nhận — danh tiếng giảm ngay lập tức.</div>",
            unsafe_allow_html=True)

        if not candidates:
            st.info("Không có node nào trong mạng.")
        else:
            with st.form("penalty_form"):
                p1, p2 = st.columns([1.5, 2])
                selected_id = p1.selectbox(
                    "Node cần xử phạt",
                    [f"{n['id']} (rep={n['rep']:.2f}, {_STATUS_LABEL[n['status']]})"
                     for n in candidates],
                )
                reason = p2.text_input("Lý do xử phạt",
                                       placeholder="VD: Đề xuất khối không hợp lệ lần 2")
                penalty_pct = st.slider(
                    "Mức phạt (giảm danh tiếng)", 0.05, 0.50, 0.20, 0.05,
                    format="%.2f",
                    help="0.20 = giảm 20 điểm danh tiếng")
                submitted_p = st.form_submit_button("⚠️ Áp dụng hình phạt", type="primary")

            if submitted_p:
                if not reason.strip():
                    st.error("Vui lòng nhập lý do xử phạt.")
                else:
                    node_id = selected_id.split(" ")[0] + " " + selected_id.split(" ")[1]
                    for n in nodes:
                        if n["id"] == node_id:
                            old_rep = n["rep"]
                            n["rep"] = max(0.0, round(old_rep - penalty_pct, 3))
                            n["status"] = "penalized"
                            n["note"] = reason.strip()
                            st.session_state["penalty_log"].insert(0, {
                                "node":   node_id,
                                "reason": reason.strip(),
                                "before": old_rep,
                                "after":  n["rep"],
                                "delta":  penalty_pct,
                            })
                            st.success(
                                f"Đã phạt **{node_id}**: danh tiếng "
                                f"`{old_rep:.2f}` → `{n['rep']:.2f}` "
                                f"(−{penalty_pct:.2f}). Lý do: {reason.strip()}"
                            )
                            break

        plog = st.session_state["penalty_log"]
        if plog:
            st.markdown("<div class='inner-sect'>Lịch sử xử phạt phiên này</div>", unsafe_allow_html=True)
            prows = "".join(
                f"<tr>"
                f"<td><span class='id-chip'>{p['node']}</span></td>"
                f"<td style='color:var(--text)'>{p['reason']}</td>"
                f"<td class='rep-before'>{p['before']:.2f}</td>"
                f"<td><span class='rep-after'>{p['after']:.2f}</span>"
                f"<span class='delta-chip'>−{p['delta']:.2f}</span></td>"
                f"</tr>"
                for p in plog
            )
            st.markdown(
                f"<table class='plog-tbl'><thead><tr>"
                f"<th>Node</th><th>Lý do xử phạt</th><th>Trước</th><th>Sau khi phạt</th>"
                f"</tr></thead><tbody>{prows}</tbody></table>",
                unsafe_allow_html=True)


elif role == "citizen":
    fresh = len(st.session_state["query_log"])
    notif_label = f"🔔 Thông báo ({fresh})" if fresh else "🔔 Thông báo"
    tab_svc, tab_notif = st.tabs(["🏙️ Dịch vụ thành phố", notif_label])

    with tab_svc:
        scn_label = st.radio("Dịch vụ", list(SCENARIOS),
                             horizontal=True, key="scn")
        scn = SCENARIOS[scn_label]
        if st.session_state.get("_last_scn") != scn:
            st.session_state["started"] = False
            st.session_state["_last_scn"] = scn
        _SVC_CTX = {
            "ev":      ("⚡", "Nhập <b>mẫu xe</b> và <b>biển số</b> — hệ thống tra cứu ví liên kết và tính kWh cần nạp từ pin hiện tại."),
            "water":   ("💧", "Nhập <b>mã đồng hồ</b> — chỉ số kỳ trước/hiện tại được đọc tự động, tính khối lượng tiêu thụ và trừ phí vào ví liên kết."),
            "metro":   ("🚇", "Nhập <b>mã thẻ</b> và <b>tuyến đi</b> — hệ thống kiểm tra quyền trợ giá HSSV và ghi chuyến lên chuỗi."),
            "parking": ("🅿️", "Nhập <b>biển số</b> và <b>thời gian đỗ</b> — phí tính theo biểu giá khu vực và trừ tự động."),
            "solar":   ("☀️", "Nhập <b>sản lượng</b> điện mặt trời — bù trừ với lưới điện và ghi nhận tín chỉ carbon theo thời gian thực."),
        }
        _ctx_icon, _ctx_desc = _SVC_CTX.get(scn, ("ℹ️", "Chọn dịch vụ để tiếp tục."))
        st.markdown(
            f"<div class='svc-ctx'><span class='svc-icon'>{_ctx_icon}</span>"
            f"<span class='svc-desc'>{_ctx_desc}</span></div>",
            unsafe_allow_html=True)

        if scn == "ev":
            c1, c2 = st.columns(2)
            model = c1.text_input("Mẫu xe", "VinFast VF 8")
            plate = c2.text_input("Biển số", "51K-123.45")
            s1, s2, s3 = st.columns([2, 2, 1])
            current_pct = s1.slider("Mức pin hiện tại (%)", 0, 95, 32)
            target_pct = s2.slider("Muốn nạp đến (%)", current_pct + 1, 100,
                                   min(current_pct + 50, 100))
            s3.write(""); s3.write("")
            s3.button("⚡  Bắt đầu sạc", type="primary",
                      use_container_width=True, on_click=_start)
            session = ChargeSession(model, plate, current_pct, target_pct)
            if not st.session_state["started"]:
                st.caption(
                    f"Pin {session.battery_kwh:.0f} kWh · cần nạp ~{session.add_kwh:.1f} kWh"
                    f" · ~{_vnd(session.cost)} · Ví: {session.wallet} ({session.owner})"
                )
            if st.session_state["started"]:
                _banner("⚡", f"{model} · {plate} · {current_pct}%→{target_pct}%"
                        f" · {session.add_kwh:.1f} kWh · {_vnd(session.cost)}"
                        f" · Ví {session.wallet}")
            components.html(
                render_kiosk_html(session, st.session_state["run_id"],
                                  st.session_state["started"]),
                height=620, scrolling=False)

        elif scn == "water":
            w1, w2 = st.columns([3, 1])
            meter_id = w1.text_input("Mã đồng hồ nước",
                                     "ĐH-0427",
                                     help="Xem trên mặt đồng hồ hoặc hoá đơn kỳ trước")
            w2.write(""); w2.write("")
            w2.button("💧  Chốt kỳ & đối soát", type="primary",
                      use_container_width=True, on_click=_start)
            session = WaterSession(meter_id)
            if not st.session_state["started"]:
                if session.found:
                    st.caption(
                        f"{session.device} · {session.location} · "
                        f"Kỳ trước {session.reading_prev:.1f} m³ → Hiện tại {session.reading_curr:.1f} m³"
                        f" (+{session.period_m3:.1f} m³) · ~{_vnd(session.cost)} · Ví: {session.wallet}"
                    )
                else:
                    st.warning(f"Mã '{meter_id}' chưa có trong hệ thống. Thử: ĐH-0427, ĐH-1185, ĐH-3390")
            if st.session_state["started"]:
                _banner("💧", f"{session.device} · {session.period_m3:.1f} m³"
                        f" · {_vnd(session.cost)} · Ví {session.wallet}")
            components.html(
                render_water_html(session, st.session_state["run_id"],
                                  st.session_state["started"]),
                height=620, scrolling=False)

        elif scn == "solar":
            _SOLAR_SITES = {
                "PV-5520 · Hệ mái 5.5 kWp": ("PV-5520", "Nhà phố, Gò Vấp", 5.5),
                "PV-1003 · Hệ mái 10 kWp":  ("PV-1003", "Biệt thự, TP. Thủ Đức", 10.0),
                "PV-0307 · Hệ mái 3 kWp":   ("PV-0307", "Nhà dân, Bình Chánh", 3.0),
            }
            sp1, sp2 = st.columns([1.5, 1.5])
            site_label = sp1.selectbox("Hệ thống điện mặt trời", list(_SOLAR_SITES))
            sys_id, def_addr, def_kwp = _SOLAR_SITES[site_label]
            addr = sp2.text_input("Địa chỉ lắp đặt", def_addr)

            g1, g2, g3, g4 = st.columns([1.3, 1.3, 1.3, 1])
            kwp = g1.slider("Công suất hệ mái (kWp)", 1.0, 20.0, float(def_kwp), 0.5)
            sun = g2.slider("Giờ nắng đỉnh hôm nay (h)", 2.0, 6.5, 4.6, 0.1,
                            help="TP.HCM trung bình ~4.5–5h nắng đỉnh/ngày")
            export = g3.slider("Bán lên lưới (%)", 0, 100, 65, 5,
                               help="Phần điện dư bán lên lưới; phần còn lại tự dùng trong nhà")
            g4.write(""); g4.write("")
            g4.button("☀️  Chốt sản lượng ngày", type="primary",
                      use_container_width=True, on_click=_start)

            session = SolarSession(sys_id, addr, float(kwp), float(sun), int(export))
            if not st.session_state["started"]:
                st.caption(
                    f"Phát ~{session.generated_kwh:.1f} kWh"
                    f" · tự dùng {session.self_use_kwh:.1f} kWh"
                    f" · bán lên lưới {session.export_kwh:.1f} kWh"
                    f" · nhận ~{_vnd(session.cost)}"
                    f" · giảm {session.co2_kg:.1f} kg CO₂ · Ví {session.wallet}"
                )
            if st.session_state["started"]:
                _banner("☀️", f"{sys_id} · {kwp:g} kWp · phát {session.generated_kwh:.1f} kWh"
                        f" · bán {session.export_kwh:.1f} kWh · {_vnd(session.cost)}")
            components.html(
                render_solar_html(session, st.session_state["run_id"],
                                  st.session_state["started"]),
                height=620, scrolling=False)

        else:
            cfg = SERVICE_CFG[scn]
            d_name, d_sub, d_amt = cfg["presets"][0]
            c1, c2, c3, c4 = st.columns([1.4, 1.4, 1, 1])
            name_val = c1.text_input("Tên / mã đối tượng", d_name)
            sub = c2.text_input("Mô tả / địa điểm", d_sub)
            amt = c3.number_input(cfg["amount_label"],
                                  float(cfg["amount_min"]),
                                  float(cfg["amount_max"]) * 3,
                                  float(d_amt), 1.0)
            c4.write(""); c4.write("")
            c4.button(cfg["action_btn"], type="primary",
                      use_container_width=True, on_click=_start)
            session = ServiceSession(scn, name_val, sub, float(amt), int(cfg["price"]))
            if st.session_state["started"]:
                unit = cfg["primary_unit"].split()[0]
                _banner(cfg["brand_icon"],
                        f"{name_val} · {amt:g} {unit} · {_vnd(session.cost)}")
            components.html(
                render_service_html(session, st.session_state["run_id"],
                                    st.session_state["started"]),
                height=620, scrolling=False)

    with tab_notif:
        st.markdown(
            "<div class='svc-ctx'><span class='svc-icon'>🔔</span>"
            "<span class='svc-desc'>Mỗi lần tổ chức bên ngoài hỏi thông tin của bạn,"
            " hệ thống ghi nhận và thông báo tại đây — bạn biết <b>ai hỏi gì</b>,"
            " nhưng dữ liệu gốc không bị tiết lộ.</span></div>",
            unsafe_allow_html=True)
        components.html(
            render_subject_html(st.session_state["query_log"],
                                st.session_state["run_id"],
                                st.session_state["auth_name"]),
            height=520, scrolling=False)


elif role == "requester":
    vlabels = {f"{v['requester']} — {v['title']}": k for k, v in VERIFY_TYPES.items()}
    vpick = st.selectbox("Tình huống truy xuất", list(vlabels), index=0)
    vtype = vlabels[vpick]
    if st.session_state.get("_last_vtype") != vtype:
        st.session_state["started"] = False
        st.session_state["_last_vtype"] = vtype
    meta = VERIFY_TYPES[vtype]

    tags_html = "".join(f"<span class='zk-tag'>{t.strip()}</span>" for t in meta["hidden"].split(","))
    st.markdown(
        f"<div class='zk-scenario'>"
        f"<div class='zk-icon'>🔐</div>"
        f"<div style='flex:1'>"
        f"<div class='zk-ttl'>{meta['title']}</div>"
        f"<div class='zk-sub'>Bên hỏi: <b style='color:var(--text)'>{meta['requester']}</b>"
        f" &nbsp;·&nbsp; Đối tượng: {meta['subject']}</div>"
        f"<div class='zk-hidden'>Dữ liệu được bảo vệ: {tags_html}</div>"
        f"</div></div>",
        unsafe_allow_html=True)

    inp, summary = {}, []
    cols = st.columns(max(len(meta["fields"]), 1) + 1)
    for i, f in enumerate(meta["fields"]):
        with cols[i]:
            if f["kind"] == "text":
                val = st.text_input(f["label"], value=f["default"])
                summary.append(f"{f['label']}: <b>{val}</b>")
            elif f["kind"] == "select":
                val = st.selectbox(f["label"], f["options"])
                summary.append(f"{f['label']}: <b>{val}</b>")
            elif f["kind"] == "date":
                val = st.date_input(f["label"], value=f["default"],
                                    min_value=DMIN, max_value=DMAX,
                                    format="DD/MM/YYYY")
                summary.append(f"{f['label']}: <b>{val:%d/%m/%Y}</b>")
            elif f["kind"] == "number":
                val = int(st.number_input(f["label"], value=int(f["default"]),
                                          step=1000, min_value=0))
                summary.append(f"{f['label']}: <b>{_vnd(val)}</b>")
            elif f["kind"] == "check":
                val = st.checkbox(f["label"], value=f["default"])
                summary.append(f"{f['label']}: <b>{'Co' if val else 'Khong'}</b>")
            inp[f["key"]] = val
    with cols[-1]:
        st.write(""); st.write("")
        st.button("🔐  Gửi yêu cầu xác minh", type="primary",
                  use_container_width=True, on_click=_start)

    result = verify(vtype, inp, date.today())

    if (st.session_state["started"]
            and st.session_state["run_id"] != st.session_state["_last_query_run_id"]):
        st.session_state["query_log"].insert(0, {
            "requester": meta["requester"],
            "question":  meta["title"],
            "answer":    result[1],
            "ok":        result[0],
            "kind":      vtype,
            "subject":   meta["subject"],
        })
        st.session_state["_last_query_run_id"] = st.session_state["run_id"]

    components.html(
        render_privacy_html(meta, result, " · ".join(summary),
                            st.session_state["run_id"],
                            st.session_state["started"]),
        height=500, scrolling=False)
