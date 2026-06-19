"""Role-based views for the demo, beyond the end-user citizen perspective.

  * Operator console  — how a city administrator runs & monitors the network.
                        Access is gated: only an account with the admin role
                        may open this console (see ACCOUNTS / authenticate).
  * Access & privacy  — the data requester asks a yes/no question answered by a
                        zero-knowledge proof; the data subject sees & consents.
                        The query data is entered by the user at run time and
                        evaluated by a small deterministic verification engine,
                        so requests can come back valid, invalid or ineligible.

All motion is CSS/JS on a fixed deterministic timeline (no random).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple


ACCOUNTS: Dict[str, Dict] = {
    "admin":    {"pw": "admin@2026", "role": "admin",     "name": "Quản trị viên Thành phố"},
    "operator": {"pw": "op@2026",    "role": "admin",     "name": "Vận hành viên mạng lưới"},
    "dan":      {"pw": "dan123",     "role": "citizen",   "name": "Người dân"},
    "dvtx":     {"pw": "dvtx@2026",  "role": "requester", "name": "Dịch vụ truy xuất thông tin"},
}


def authenticate(username: str, password: str) -> Dict | None:
    a = ACCOUNTS.get((username or "").strip().lower())
    if a and a["pw"] == password:
        return a
    return None


_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
  :root { --bg:#04050d; --line:#1d2740; --teal:#38f0d4;
          --ink:#eef2ff; --dim:#8492b4; --warn:#ffb454; --bad:#ff6b8b; --good:#34d399; }
  * { box-sizing:border-box; }
  html,body { margin:0; padding:0; background:var(--bg); font-family:'Outfit',Inter,system-ui,sans-serif; color:var(--ink); overflow:hidden; }
  .wrap { max-width:920px; margin:0 auto; padding:12px 8px; }
  .scr { background:linear-gradient(180deg,#0c1326,#070b16); border:1px solid var(--line); border-radius:20px; padding:16px 18px 18px; box-shadow:0 24px 60px rgba(0,0,0,.5); }
  .top { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
  .brand { display:flex; align-items:center; gap:10px; }
  .logo { width:32px;height:32px;border-radius:9px; background:rgba(56,240,212,0.12); border:1px solid rgba(56,240,212,0.25); display:flex;align-items:center;justify-content:center;font-size:17px; }
  .brand b { font-size:13px; }
  .brand small { display:block; font-size:9px; letter-spacing:2.5px; color:var(--teal); font-weight:700; }
  .live { font-size:10.5px; color:var(--teal); display:flex; align-items:center; gap:6px; font-weight:600; }
  .live .d { width:8px;height:8px;border-radius:50%;background:var(--teal); box-shadow:0 0 10px var(--teal); animation:pulse 1.6s infinite; }
  @keyframes pulse { 0%,100%{opacity:.45;transform:scale(.85)} 50%{opacity:1;transform:scale(1.15)} }
"""


_ZONES6 = (("Định danh", 54), ("Tài chính", 81), ("Giao thông", 73),
           ("Năng lượng", 66), ("Môi trường", 38), ("Quản trị", 47))

_KPIS = (("Validator hoạt động", "500", ""),
         ("Ủy ban hiện tại", "32", "/ 500 · luân chuyển mỗi epoch"),
         ("Epoch", "1.240", ""),
         ("Thông lượng xuyên chuỗi", "320", "giao dịch/giây"),
         ("Độ trễ giao thức", "295", "mili-giây"))

_NODES = (("Node #047", "Đề xuất khối không hợp lệ", "bad", "đã phạt danh tiếng sau 3.8 vòng"),
          ("Node #218", "Bỏ phiếu mâu thuẫn (equivocation)", "warn", "đang theo dõi · giảm trọng số"),
          ("Node #312", "Hoạt động bình thường", "good", "danh tiếng ổn định"),
          ("Node #455", "Hoạt động bình thường", "good", "trong ủy ban epoch này"))

def render_admin_html(run_id: int) -> str:
    kpi_html = "".join(
        f"<div class='kpi'><div class='kl'>{k}</div><div class='kv'>{v}</div><div class='ks'>{s}</div></div>"
        for k, v, s in _KPIS
    )
    zone_html = ""
    for i, (name, load) in enumerate(_ZONES6):
        col = "var(--bad)" if load >= 80 else ("var(--warn)" if load >= 70 else "var(--teal)")
        zone_html += (
            f"<div class='zrow'><div class='zn'>{name}</div>"
            f"<div class='zbar'><div class='zfill' style='width:{load}%;background:{col};animation-delay:{i*0.12:.2f}s'></div></div>"
            f"<div class='zpc'>{load}%</div></div>"
        )
    node_html = ""
    for nid, what, sev, note in _NODES:
        dot = {"bad": "var(--bad)", "warn": "var(--warn)", "good": "var(--good)"}[sev]
        node_html += (
            f"<div class='node'><span class='ndot' style='background:{dot};box-shadow:0 0 8px {dot}'></span>"
            f"<div class='ninfo'><div class='nid'>{nid} · <span style='color:var(--dim)'>{what}</span></div>"
            f"<div class='nnote'>{note}</div></div></div>"
        )

    return f"""<!DOCTYPE html><html data-run='{run_id}'><head><meta charset='utf-8'><style>
  {_CSS}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:8px; margin-bottom:13px; }}
  .kpi {{ background:#0a1124; border:1px solid var(--line); border-radius:12px; padding:9px 10px; }}
  .kl {{ font-size:9.5px; color:var(--dim); letter-spacing:.3px; }}
  .kv {{ font-size:23px; font-weight:800; letter-spacing:-.5px; margin-top:3px; }}
  .ks {{ font-size:8.5px; color:var(--dim); margin-top:2px; min-height:11px; }}
  .card {{ background:#0a1124; border:1px solid var(--line); border-radius:13px; padding:12px 13px; }}
  .ch {{ font-size:9.5px; color:var(--dim); font-weight:600; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:10px; display:flex; gap:7px; align-items:center; }}
  .zrow {{ display:flex; align-items:center; gap:9px; margin-bottom:8px; }}
  .zn {{ width:78px; font-size:11.5px; font-weight:600; }}
  .zbar {{ flex:1; height:8px; background:#070d1e; border-radius:6px; overflow:hidden; }}
  .zfill {{ height:100%; border-radius:6px; transform-origin:left; animation:grow 1.1s ease both; }}
  @keyframes grow {{ from{{transform:scaleX(0)}} to{{transform:scaleX(1)}} }}
  .zpc {{ width:34px; text-align:right; font-size:10.5px; color:var(--dim); font-weight:600; }}
  .node {{ display:flex; gap:9px; align-items:flex-start; padding:7px 0; border-top:1px solid #11192e; }}
  .node:first-of-type {{ border-top:none; }}
  .ndot {{ width:9px;height:9px;border-radius:50%;margin-top:4px;flex:0 0 auto; }}
  .nid {{ font-size:12px; font-weight:700; }}
  .nnote {{ font-size:10px; color:var(--dim); margin-top:1px; }}

  /* ── realtime log ── */
  .logcard {{ background:#020710; border:1px solid #0e1a30; border-radius:13px;
              padding:11px 13px; margin-top:12px; }}
  .loghead {{ display:flex; align-items:center; justify-content:space-between;
              margin-bottom:8px; }}
  .logtitle {{ font-size:9.5px; color:var(--dim); font-weight:600; letter-spacing:1.2px; text-transform:uppercase;
               display:flex; align-items:center; gap:7px; }}
  .logmeta {{ font-size:10px; color:var(--dim); display:flex; gap:12px; align-items:center; }}
  .txcnt {{ font-size:11px; font-weight:700; color:var(--teal); }}
  .logwrap {{ height:170px; overflow-y:auto; font-family:'Consolas','Courier New',monospace;
              font-size:10.5px; line-height:1.65; padding-right:4px; }}
  .logwrap::-webkit-scrollbar {{ width:3px; }}
  .logwrap::-webkit-scrollbar-track {{ background:transparent; }}
  .logwrap::-webkit-scrollbar-thumb {{ background:#1a2540; border-radius:2px; }}
  .lg {{ display:flex; gap:8px; align-items:flex-start; padding:2px 0;
         opacity:0; animation:slidein .35s ease forwards; }}
  .ts {{ color:#3a4d6e; flex:0 0 62px; font-size:10px; padding-top:1px; }}
  .lvl {{ border-radius:3px; padding:1px 5px; font-size:9px; font-weight:800;
          flex:0 0 38px; text-align:center; margin-top:1px; letter-spacing:.5px; }}
  .lvl-INFO {{ background:rgba(56,240,212,.10); color:var(--teal); }}
  .lvl-OK   {{ background:rgba(56,240,212,.15);  color:var(--teal); }}
  .lvl-WARN {{ background:rgba(255,180,84,.18);  color:var(--warn); }}
  .lvl-ERR  {{ background:rgba(255,107,139,.18); color:var(--bad); }}
  .lmsg {{ flex:1; color:#c8d4f0; word-break:break-word; }}
  .cursor {{ display:inline-block; width:7px; height:12px; background:var(--teal);
             margin-left:2px; vertical-align:middle;
             animation:blink 1.1s step-end infinite; }}
  @keyframes blink {{ 50%{{opacity:0}} }}
  @keyframes slidein {{ from{{opacity:0;transform:translateY(5px)}} to{{opacity:1;transform:none}} }}
</style></head><body>
<div class='wrap'><div class='scr'>
  <div class='top'>
    <div class='brand'><div class='logo'>🛠️</div><div><small>OPERATOR CONSOLE</small><b>Bảng điều khiển vận hành mạng lưới</b></div></div>
    <div class='live'><span class='d'></span>TRỰC TUYẾN</div>
  </div>
  <div class='kpis'>{kpi_html}</div>
  <div class='grid2'>
    <div class='card'>
      <div class='ch'>🌐 Tải 6 Smart Zone theo thời gian thực</div>
      {zone_html}
    </div>
    <div class='card'>
      <div class='ch'>🛡️ Phát hiện bất thường &amp; sổ danh tiếng</div>
      {node_html}
    </div>
  </div>
  <div class='logcard'>
    <div class='loghead'>
      <div class='logtitle'>📜 Nhật ký sự kiện hệ thống</div>
      <div class='logmeta'>
        <span>TXS: <span class='txcnt' id='txcnt'>1920</span></span>
        <span style='color:#1d3a5a'>|</span>
        <span>EPOCH: <span style='color:var(--ink);font-weight:700'>1.240</span></span>
        <span style='color:#1d3a5a'>|</span>
        <span style='color:var(--teal);font-weight:700;font-size:10px;
                     animation:pulse 1.6s infinite'>⬤ LIVE</span>
      </div>
    </div>
    <div class='logwrap' id='logwrap'></div>
  </div>
  <div style='font-size:10px;color:var(--dim);margin-top:10px;line-height:1.5'>
    Tự động phát hiện &amp; xử phạt node sai — không cần can thiệp thủ công.
    Mọi sự kiện được ghi lại tất định và có thể kiểm chứng lại.
  </div>
</div></div>
<script>
(function(){{
  var wrap = document.getElementById('logwrap');
  var txEl = document.getElementById('txcnt');
  var lvlCls = {{INFO:'lvl-INFO',OK:'lvl-OK',WARN:'lvl-WARN',ERR:'lvl-ERR'}};

  /* ── mutable state ── */
  var sec     = 14*3600 + 28*60;   // 14:28:00
  var epoch   = 1240;
  var txTotal = 1920;
  var loads   = [54,81,73,66,38,47];  // zone loads, will drift
  var nodeRep = {{}};                  // node → reputation (lazy init)
  var ZONES   = ['Định danh','Tài chính','Giao thông','Năng lượng','Môi trường','Quản trị'];
  var NODE_IDS= [1,12,47,88,103,147,218,256,312,391,421,455,502,518,563,601];

  function ri(min,max){{ return Math.floor(Math.random()*(max-min+1))+min; }}
  function rf(min,max,dec){{
    var v=Math.random()*(max-min)+min;
    return dec!==undefined ? +v.toFixed(dec) : v;
  }}
  function pick(arr){{ return arr[ri(0,arr.length-1)]; }}
  function ts(){{
    sec += ri(1,4);
    var h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;
    return h+':'+(m<10?'0':'')+m+':'+(s<10?'0':'')+s;
  }}

  function rep(nid){{
    if(nodeRep[nid]===undefined) nodeRep[nid]=rf(0.60,0.95,3);
    return nodeRep[nid];
  }}
  function driftRep(nid,delta){{
    nodeRep[nid]=Math.max(0,Math.min(1, +(rep(nid)+delta).toFixed(3)));
    return nodeRep[nid];
  }}

  /* ── event generators ── */
  function genZone(){{
    var z=ri(0,5);
    var delta=ri(-6,7);
    loads[z]=Math.max(12,Math.min(97,loads[z]+delta));
    var l=loads[z];
    var lvl=l>=88?'ERR':l>=75?'WARN':'INFO';
    var tail=l>=88?' · VƯỢT ngưỡng — điều tiết tải tự động'
                  :l>=75?' · tiệm cận cảnh báo · theo dõi chặt'
                  :l<=30?' · nhàn rỗi · sẵn sàng nhận thêm tải'
                  :' · ổn định';
    return [lvl,'Vùng '+ZONES[z]+': tải '+l+'%'+tail];
  }}

  function genNodeOK(){{
    var nid=pick(NODE_IDS);
    var r=driftRep(nid,+rf(0.002,0.008,3));
    var msgs=[
      'Node #'+nid+' · xác thực khối '+epoch+' thành công · rep→'+r,
      'Node #'+nid+' · relay xuyên chuỗi hoàn tất · '+ri(80,340)+' tx chuyển tiếp',
      'Node #'+nid+' · vào ủy ban epoch '+epoch+' · trọng số '+r,
      'Node #'+nid+' · Merkle proof hợp lệ · '+(ri(10,60)*10)+' tx đối soát',
    ];
    return ['OK',pick(msgs)];
  }}

  function genNodeWarn(){{
    var nid=pick(NODE_IDS);
    var r=driftRep(nid,-rf(0.005,0.015,3));
    var msgs=[
      'Node #'+nid+' · phản hồi chậm +'+ri(180,480)+'ms · rep giảm→'+r,
      'Node #'+nid+' · bỏ phiếu chậm hơn '+rf(1.5,3.5,1)+'σ · giảm trọng số',
      'Node #'+nid+' · mất gói tin '+(ri(1,4))+'/'+(ri(5,10))+' · đang theo dõi',
      'Node #'+nid+' · kết nối không ổn định '+(ri(2,8))+'s · rep→'+r,
    ];
    return ['WARN',pick(msgs)];
  }}

  function genNodeErr(){{
    var nid=pick([47,218,391]);
    var r=driftRep(nid,-rf(0.04,0.12,3));
    var msgs=[
      'Node #'+nid+' · hash khối không khớp → áp hình phạt · rep→'+r,
      'Node #'+nid+' · đề xuất khối sai cấu trúc · loại khỏi ủy ban · rep→'+r,
      'Node #'+nid+' · bỏ phiếu mâu thuẫn (equivocation) · phạt −0.08 · rep→'+r,
    ];
    return ['ERR',pick(msgs)];
  }}

  function genRelay(){{
    var tps=ri(280,420), lat=ri(255,320), zones=ri(5,6);
    return ['INFO','Cross-chain relay: '+tps+' tx/s · latency '+lat+'ms · '+zones+'/6 zone phản hồi'];
  }}

  function genTx(){{
    var n=ri(80,460);
    txTotal+=n;
    if(txEl) txEl.textContent=txTotal.toLocaleString('vi-VN');
    return ['OK','Đối soát epoch '+epoch+': +'+n+' tx · tổng '+txTotal.toLocaleString('vi-VN')];
  }}

  function genService(){{
    var ev=[
      ['OK',  'EV sạc · '+ri(8,52)+' phiên hoàn tất · zone Năng lượng · avg '+rf(12,38,1)+' kWh'],
      ['OK',  'Metro tap-and-go · '+ri(120,680)+' lượt · zone Giao thông · trợ giá HSSV áp dụng'],
      ['OK',  'Đồng hồ nước IoT · '+ri(40,180)+' hộ chốt kỳ · zone Môi trường · 0 dị thường'],
      ['OK',  'Bãi đỗ xe · '+ri(20,90)+' xe · zone Định danh · nhận diện biển số OK'],
      ['OK',  'Điện mặt trời · '+ri(2,18)+'.'+ri(0,9)+' MWh bán lên lưới · zone Năng lượng'],
      ['INFO','Dịch vụ công ZK · '+ri(10,55)+' yêu cầu xác minh · zone Định danh · 0 rò rỉ'],
    ];
    return pick(ev);
  }}

  function genEpoch(){{
    epoch++;
    var v=ri(28,36);
    return ['INFO','Epoch '+epoch+' · VRF chọn '+v+'/500 validator · ủy ban mới bắt đầu phục vụ'];
  }}

  function genMerkle(){{
    return ['OK','Merkle root #'+epoch+' cập nhật · 6/6 zone đồng thuận · '+(ri(1800,2400)+' tx')];
  }}

  /* ── weighted draw ── */
  var GEN=[
    {{fn:genZone,    w:14}},
    {{fn:genNodeOK,  w:12}},
    {{fn:genRelay,   w:8}},
    {{fn:genTx,      w:8}},
    {{fn:genService, w:10}},
    {{fn:genNodeWarn,w:7}},
    {{fn:genMerkle,  w:5}},
    {{fn:genNodeErr, w:2}},
    {{fn:genEpoch,   w:3}},
  ];
  var totalW=GEN.reduce(function(a,g){{return a+g.w;}},0);

  function drawGen(){{
    var r=Math.random()*totalW, cum=0;
    for(var i=0;i<GEN.length;i++){{
      cum+=GEN[i].w;
      if(r<cum) return GEN[i].fn;
    }}
    return GEN[0].fn;
  }}

  /* ── DOM helpers ── */
  function addRow(level,msg,delay){{
    var row=document.createElement('div');
    row.className='lg';
    if(delay) row.style.animationDelay=delay+'s';
    row.innerHTML='<span class="ts">'+ts()+'</span>'
      +'<span class="lvl '+lvlCls[level]+'">'+level+'</span>'
      +'<span class="lmsg">'+msg+'</span>';
    wrap.insertBefore(row, cur);
    wrap.scrollTop=wrap.scrollHeight;
    while(wrap.children.length>80) wrap.removeChild(wrap.firstChild);
  }}

  /* ── blinking cursor (always last) ── */
  var cur=document.createElement('span');
  cur.className='cursor'; wrap.appendChild(cur);

  /* ── seed 10 initial rows quickly ── */
  var seeds=[
    genEpoch(), genZone(), genNodeOK(), genRelay(), genTx(),
    genService(), genZone(), genNodeOK(), genNodeWarn(), genMerkle(),
  ];
  seeds.forEach(function(e,i){{ addRow(e[0],e[1],(i*0.18).toFixed(2)); }});

  /* ── variable-interval stream ── */
  function scheduleNext(){{
    var delay=1200+Math.random()*1400;
    setTimeout(function(){{
      addRow.apply(null, drawGen()());
      scheduleNext();
    }}, delay);
  }}
  setTimeout(scheduleNext, 2400);
}})();
</script>
</body></html>"""


RESIDENTS = {"A-1203", "B-0907", "C-1511", "D-0420"}

# Each type: title, requester, subject, hidden (data NOT revealed), and a list
VERIFY_TYPES: Dict[str, Dict] = {
    "insurance": dict(
        title="Bảo hiểm xe còn hiệu lực?", requester="Trạm sạc EVN / CSGT", subject="Chủ xe",
        hidden="ngày hết hạn, số hợp đồng, công ty bảo hiểm, mức phí",
        fields=[dict(key="plate", label="Biển số xe", kind="select",
                     options=["51K-123.45", "43B-001.23", "77C-456.78", "29A-888.88"])]),
    "subsidy": dict(
        title="Đủ điều kiện trợ giá vé metro (HSSV)?", requester="Cổng vé Metro", subject="Hành khách",
        hidden="trường, ngày sinh, mã số sinh viên, địa chỉ thường trú",
        fields=[dict(key="student_id", label="Mã thẻ HSSV / Mã sinh viên", kind="select",
                     options=["SV-2021-04512", "SV-2019-11203", "SV-2001-00034", "HS-2022-00871"])]),
    "age18": dict(
        title="Công dân đã đủ 18 tuổi?", requester="Dịch vụ công trực tuyến", subject="Công dân",
        hidden="ngày sinh, địa chỉ, thông tin cá nhân khác",
        fields=[dict(key="cccd", label="Số CCCD / Mã công dân", kind="select",
                     options=["079201004523", "079208012341", "092209001122", "001199503127"])]),
    "resident": dict(
        title="Có phải cư dân toà nhà?", requester="Bãi đỗ khu dân cư", subject="Cư dân",
        hidden="địa chỉ căn hộ, số CCCD, hợp đồng thuê",
        fields=[dict(key="code", label="Mã cư dân / số căn hộ", kind="select",
                     options=["A-1203", "X-9090", "B-0907", "Z-0001"])]),
    "balance": dict(
        title="Số dư ví đủ thanh toán dịch vụ?", requester="Cổng thanh toán dịch vụ", subject="Chủ ví",
        hidden="số dư chính xác, lịch sử giao dịch, nguồn tiền",
        fields=[dict(key="wallet_id", label="Mã ví / Số điện thoại", kind="select",
                     options=["VI-0084912", "VI-0099001", "0912345678", "VI-0031205"]),
                dict(key="need", label="Số tiền cần (₫)", kind="number", default=182000)]),
}


def _age(birth: date, today: date) -> float:
    return (today - birth).days / 365.25


_INSURANCE_DB: Dict[str, Tuple[bool, str]] = {
    "51K-123.45": (True,  "Bảo Việt, hết hạn 01/09/2026"),
    "29A-888.88": (True,  "PVI, hết hạn 15/03/2027"),
    "43B-001.23": (False, "Hết hạn 01/03/2025, quá 15 tháng"),
    "77C-456.78": (False, "Chưa mua bảo hiểm bắt buộc"),
    "51F-999.00": (True,  "MIC, hết hạn 30/11/2026"),
}

_AGE18_DB: Dict[str, Tuple[bool, str]] = {
    "079201004523": (True,  "Sinh 2000, hiện 24 tuổi — đủ 18"),
    "001199503127": (True,  "Sinh 1995, hiện 29 tuổi — đủ 18"),
    "048202209811": (True,  "Sinh 2002, hiện 22 tuổi — đủ 18"),
    "079208012341": (False, "Sinh 2008, hiện 16 tuổi — chưa đủ"),
    "092209001122": (False, "Sinh 2009, hiện 15 tuổi — chưa đủ"),
}

_SUBSIDY_DB: Dict[str, Tuple[bool, str]] = {
    "SV-2021-04512": (True,  "Sinh viên UIT, 21 tuổi — đủ điều kiện"),
    "HS-2022-00871": (True,  "Học sinh THPT, 17 tuổi — đủ điều kiện"),
    "SV-2019-11203": (False, "Đã tốt nghiệp, thẻ hết hiệu lực"),
    "SV-2001-00034": (False, "26 tuổi, quá tuổi trợ giá (> 22)"),
    "SV-2023-07756": (True,  "Sinh viên Bách Khoa, 19 tuổi — đủ điều kiện"),
}

_WALLET_DB: Dict[str, int] = {
    "VI-0084912": 450_000,
    "VI-0031205": 1_200_000,
    "VI-0099001": 85_000,
    "VI-0055678": 2_500_000,
    "0901234567": 320_000,
    "0912345678": 50_000,
}


def _vnd(n: int) -> str:
    return f"{int(n):,}".replace(",", ".") + " ₫"


def verify(kind: str, inp: Dict, today: date) -> Tuple[bool, str, str]:
    """Return (ok, answer_label, reason). Deterministic; reason is for the demo
    viewer, the requester only ever receives the yes/no answer."""
    if kind == "insurance":
        plate = inp["plate"].strip().upper()
        if plate not in _INSURANCE_DB:
            return False, "KHÔNG TÌM THẤY", f"Biển số {plate!r} chưa có trong cơ sở dữ liệu bảo hiểm"
        ok, note = _INSURANCE_DB[plate]
        return ok, ("CÒN HIỆU LỰC" if ok else "ĐÃ HẾT HẠN"), note
    if kind == "subsidy":
        sid = inp["student_id"].strip()
        if sid not in _SUBSIDY_DB:
            return False, "KHÔNG TÌM THẤY", f"Mã {sid!r} không có trong hệ thống HSSV"
        ok, note = _SUBSIDY_DB[sid]
        return ok, ("ĐỦ ĐIỀU KIỆN" if ok else "KHÔNG ĐỦ ĐIỀU KIỆN"), note
    if kind == "age18":
        cccd = inp["cccd"].strip()
        if cccd not in _AGE18_DB:
            return False, "KHÔNG TÌM THẤY", f"Mã CCCD {cccd!r} không có trong hệ thống"
        ok, note = _AGE18_DB[cccd]
        return ok, ("ĐỦ 18 TUỔI" if ok else "CHƯA ĐỦ TUỔI"), note
    if kind == "resident":
        ok = inp["code"].strip().upper() in RESIDENTS
        return ok, ("ĐÚNG CƯ DÂN" if ok else "KHÔNG PHẢI CƯ DÂN"), (
            "Mã có trong danh bạ cư dân" if ok else "Mã không có trong danh bạ cư dân")
    if kind == "balance":
        wid = inp["wallet_id"].strip()
        if wid not in _WALLET_DB:
            return False, "KHÔNG TÌM THẤY", f"Mã ví {wid!r} không tồn tại trong hệ thống"
        bal = _WALLET_DB[wid]
        need = inp["need"]
        ok = bal >= need
        return ok, ("ĐỦ SỐ DƯ" if ok else "KHÔNG ĐỦ SỐ DƯ"), (
            "Số dư đủ chi trả" if ok else f"Thiếu {_vnd(need - bal)}")
    return False, "KHÔNG XÁC ĐỊNH", ""


def render_privacy_html(meta: Dict, result: Tuple[bool, str, str],
                        inputs_text: str, run_id: int, started: bool) -> str:
    """Requester-side screen: input summary + ZK yes/no result only."""  # noqa: RUF001
    requester, question = meta["requester"], meta["title"]
    hidden = meta["hidden"]
    ok, answer, reason = result
    autostart = "true" if started else "false"

    if started:
        col = "var(--teal)" if ok else "var(--bad)"
        icon = "✅" if ok else "⛔"
        result_block = (
            f"<div class='answer' id='answer' style='border-color:{col};'>"
            f"<div class='alabel'>KẾT QUẢ XÁC MINH QUA ZK-PROOF</div>"
            f"<div class='aval' style='color:{col}'>{icon}&nbsp;&nbsp;{answer}</div>"
            f"<div class='anote'>Trả về bởi <b>bằng chứng không tiết lộ (ZK)</b>. "
            f"Bên truy xuất <b>không nhìn thấy</b>: {hidden}.</div>"
            f"<div class='areason'>Chi tiết (chỉ hiển thị trong demo): {reason}.</div>"
            f"</div>"
        )
    else:
        result_block = (
            "<div class='answer pending' id='answer'>"
            "<div class='alabel'>KẾT QUẢ</div>"
            "<div class='aval' style='color:var(--dim)'>— nhập dữ liệu rồi bấm Gửi yêu cầu —</div>"
            "</div>"
        )

    return f"""<!DOCTYPE html><html data-run='{run_id}'><head><meta charset='utf-8'><style>
  {_CSS}
  .card {{ background:#0a1124; border:1px solid var(--line); border-radius:14px; padding:16px 18px; }}
  .ask {{ font-size:16px; font-weight:700; line-height:1.45; }}
  .askby {{ font-size:11px; color:var(--dim); margin-top:5px; }}
  .askby b {{ color:var(--ink); }}
  .inq {{ font-size:11px; color:var(--dim); margin-top:12px; background:#070d1e; border:1px dashed #1d2740;
          border-radius:9px; padding:8px 11px; line-height:1.6; }}
  .answer {{ margin-top:14px; background:#070d1e; border:2px solid #16203a; border-radius:13px; padding:14px 16px;
             transition:border-color .4s; }}
  .answer.pending {{ opacity:.65; }}
  .alabel {{ font-size:9px; letter-spacing:2.5px; color:var(--dim); font-weight:700; }}
  .aval {{ font-size:26px; font-weight:800; margin-top:7px; letter-spacing:-.4px; }}
  .anote {{ font-size:11px; color:var(--dim); margin-top:10px; line-height:1.55; }}
  .anote b {{ color:var(--teal); }}
  .areason {{ font-size:10px; color:var(--dim); margin-top:6px; font-style:italic; border-top:1px dashed #16203a; padding-top:6px; }}
  .flow {{ display:flex; align-items:center; gap:8px; font-size:10px; color:var(--dim); margin-top:14px; justify-content:center; flex-wrap:wrap; }}
  .pill {{ background:#0a1124; border:1px solid var(--line); border-radius:20px; padding:4px 11px; white-space:nowrap; }}
  .pill.lit {{ border-color:var(--teal); color:var(--teal); }}
  .notify {{ margin-top:12px; background:rgba(56,240,212,.05);
             border:1px solid rgba(56,240,212,.18); border-radius:10px; padding:9px 12px;
             font-size:10.5px; color:var(--dim); line-height:1.5; }}
  .notify b {{ color:var(--teal); }}
</style></head><body>
<div class='wrap'><div class='scr'>
  <div class='top'>
    <div class='brand'><div class='logo'>🏛️</div><div><small>BÊN TRUY XUẤT · VERIFIABLE QUERY</small><b>Dịch vụ gửi yêu cầu xác minh</b></div></div>
    <div class='live'><span class='d'></span>{"ĐANG XÁC MINH" if started else "SẴN SÀNG"}</div>
  </div>
  <div class='card'>
    <div class='ask'>"{question}"</div>
    <div class='askby'>Yêu cầu bởi: <b>{requester}</b></div>
    <div class='inq'>📋&nbsp; Dữ liệu để kiểm chứng (nhập từ form):<br>{inputs_text}</div>
    {result_block}
    <div class='flow'>
      <span class='pill'>Nhập &amp; gửi</span> →
      <span class='pill'>Dispatch xuyên chuỗi</span> →
      <span class='pill'>Lõi xác minh ZK</span> →
      <span class='pill{'  lit' if started else ''}'>{'✓ ' if started else ''}Chỉ Đúng/Sai</span>
    </div>
  </div>
  <div class='notify'>
    <b>🔔 Ghi nhận phía người dân:</b> Mỗi lần bên truy xuất gửi yêu cầu, hệ thống tự động ghi vào
    nhật ký của <b>chủ thể dữ liệu</b>. Người dân có thể đăng nhập màn hình bên kia để xem thông báo.
    Dữ liệu gốc không bao giờ rời khỏi chuỗi của họ.
  </div>
</div></div>
<script>
(function(){{
  if(!{autostart}) return;
  var a=document.getElementById('answer');
  if(a){{ a.style.opacity='0'; setTimeout(function(){{ a.style.transition='opacity .6s'; a.style.opacity='1'; }},400); }}
}})();
</script>
</body></html>"""


_SAMPLE_SUBJECT_HISTORY: List[Tuple] = [
    ("Cổng vé Metro", "Xác minh điều kiện trợ giá HSSV", "Hôm qua · 09:10", "ĐỦ ĐIỀU KIỆN", True),
    ("Sở Y tế TP", "Xác minh tình trạng tiêm chủng", "2 ngày trước · 14:25", "ĐỦ ĐIỀU KIỆN", True),
]
_TIME_LABELS = ["Vừa xong", "2 phút trước", "5 phút trước", "Hôm nay · vừa rồi"]


def render_subject_html(query_log: List[Dict], run_id: int, subject_name: str = "Người dân") -> str:
    """Data-subject screen: notification log of who queried their data."""
    fresh_count = len(query_log)

    rows = ""
    if not query_log:
        rows = (
            "<div class='empty'>Chưa có yêu cầu truy xuất nào từ phiên này.<br>"
            "<span style='font-size:10px'>Hãy chuyển sang màn hình bên truy xuất, nhập thông tin và gửi yêu cầu.</span></div>"
        )
    else:
        for i, entry in enumerate(query_log):
            time_str = _TIME_LABELS[min(i, len(_TIME_LABELS) - 1)]
            col = "var(--teal)" if entry["ok"] else "var(--bad)"
            new_cls = " new" if i == 0 else ""
            rows += (
                f"<div class='arow{new_cls}'>"
                f"<span class='adot' style='background:{col};box-shadow:0 0 8px {col}'></span>"
                f"<div class='ainfo'>"
                f"<div class='aw'>{entry['requester']}"
                f"<span style='color:var(--dim);font-weight:400'> · {entry['question']}</span></div>"
                f"<div class='am'>{time_str} · <b style='color:var(--teal)'>✓ Bạn đã cho phép</b> · "
                f"kết quả trả về: <b style='color:{col}'>{entry['answer']}</b>"
                f"<span style='color:var(--dim)'> (chỉ Đúng/Sai)</span></div>"
                f"</div></div>"
            )

    for who, what, when, ans, ok in _SAMPLE_SUBJECT_HISTORY:
        col = "var(--teal)" if ok else "var(--bad)"
        rows += (
            f"<div class='arow'>"
            f"<span class='adot old'></span>"
            f"<div class='ainfo'>"
            f"<div class='aw'>{who}<span style='color:var(--dim);font-weight:400'> · {what}</span></div>"
            f"<div class='am'>{when} · ✓ Đã cho phép · "
            f"kết quả: <b style='color:{col}'>{ans}</b></div>"
            f"</div></div>"
        )

    badge = (f"<span class='badge'>{fresh_count}</span>" if fresh_count else "")

    return f"""<!DOCTYPE html><html data-run='{run_id}'><head><meta charset='utf-8'><style>
  {_CSS}
  .card {{ background:#0a1124; border:1px solid var(--line); border-radius:14px; padding:16px 18px; }}
  .greeting {{ display:flex; align-items:center; gap:12px; margin-bottom:14px; }}
  .avatar {{ width:42px;height:42px;border-radius:50%;background:rgba(56,240,212,0.12);
             border:1px solid rgba(56,240,212,0.25);
             display:flex;align-items:center;justify-content:center;font-size:20px;flex:0 0 auto; }}
  .gname {{ font-size:15px; font-weight:700; }}
  .gsub {{ font-size:10px; color:var(--dim); margin-top:2px; letter-spacing:.3px; }}
  .ntitle {{ font-size:11px; font-weight:700; color:var(--teal); display:flex; align-items:center;
             gap:7px; margin-bottom:12px; }}
  .badge {{ background:var(--bad); color:#fff; border-radius:20px; padding:2px 7px;
            font-size:10px; font-weight:700; animation:pulse 1.6s infinite; }}
  .empty {{ font-size:12px; color:var(--dim); text-align:center; padding:22px 10px; line-height:1.7; }}
  .arow {{ display:flex; gap:10px; align-items:flex-start; padding:10px 0; border-top:1px solid #11192e; }}
  .arow:first-of-type {{ border-top:none; }}
  .arow.new {{ background:linear-gradient(90deg,rgba(56,240,212,.08),transparent);
               border-radius:9px; padding:10px; border-top:none;
               opacity:0; animation:popin .6s ease forwards; }}
  @keyframes popin {{ from{{opacity:0;transform:translateY(-8px)}} to{{opacity:1;transform:none}} }}
  .adot {{ width:10px;height:10px;border-radius:50%;margin-top:4px;flex:0 0 auto; }}
  .adot.old {{ background:var(--dim); }}
  .ainfo {{ flex:1; min-width:0; }}
  .aw {{ font-size:12px; font-weight:700; }}
  .am {{ font-size:10.5px; color:var(--dim); margin-top:3px; line-height:1.5; }}
  .footer {{ font-size:10px; color:var(--dim); margin-top:13px; line-height:1.55;
             background:#070d1e; border:1px solid #11192e; border-radius:9px; padding:9px 11px; }}
  .footer b {{ color:var(--teal); }}
</style></head><body>
<div class='wrap'><div class='scr'>
  <div class='top'>
    <div class='brand'><div class='logo'>👤</div><div><small>CHỦ THỂ DỮ LIỆU · DATA SUBJECT</small><b>Nhật ký truy xuất dữ liệu của bạn</b></div></div>
    <div class='live'><span class='d'></span>TRỰC TUYẾN</div>
  </div>
  <div class='greeting'>
    <div class='avatar'>👤</div>
    <div><div class='gname'>Xin chào, {subject_name}</div>
    <div class='gsub'>CÔNG DÂN · HỆ THỐNG THÀNH PHỐ THÔNG MINH</div></div>
  </div>
  <div class='card'>
    <div class='ntitle'>🔔 Thông báo truy xuất thông tin {badge}</div>
    {rows}
  </div>
  <div class='footer'>
    <b>Quyền riêng tư của bạn được bảo vệ:</b> Bên truy xuất <b>chỉ nhận Đúng/Sai</b> —
    họ không thấy dữ liệu gốc, lịch sử hay danh tính chi tiết của bạn.
    Mọi truy xuất đều cần bạn cho phép và được ghi lại minh bạch tại đây.
    Dữ liệu gốc không bao giờ rời khỏi chuỗi của chủ nhân.
  </div>
</div></div>
</body></html>"""
