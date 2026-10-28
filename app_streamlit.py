"""
Streamlit - Automasi Import Data (PZ Cussons, NPURE, Blood)
================================================================================
Login Google (@warnaemasindonesia.com) -> pilih brand -> import Raw TAP / Raw SC /
Live Streaming / Video Bank. Logika import-nya modul yang sama dengan app_gui.py
(import_*_unified.py); halaman ini cuma bungkus: upload file, set konfigurasi, jalankan main().

CARA PAKAI (folder Streamlit_Import):
1. Salin .streamlit/secrets.toml.example -> .streamlit/secrets.toml, isi bagian [auth].
2. pip install "streamlit>=1.42" Authlib
3. Klik dua kali jalankan.bat (atau: cd Streamlit_Import, lalu streamlit run app_streamlit.py)
"""

import base64
import contextlib
import datetime
import importlib
import io
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
# deploy (Streamlit_Deploy): modul import_* ada di folder ini; dev (Streamlit_Import): di folder induk (Automasi)
PROJECT_DIR = HERE if (HERE / 'import_raw_tap_unified.py').exists() else HERE.parent
sys.path.insert(0, str(PROJECT_DIR))

import blood_rules
import import_raw_tap_unified
import npure_rules

ASSETS = HERE / 'assets' if (HERE / 'assets').exists() else PROJECT_DIR / 'Dashboard_Cussons'
ALLOWED_DOMAIN = '@warnaemasindonesia.com'

BRANDS = {
    'CUSSONS': dict(name='PZ Cussons', logo='logo-cussons.webp', logo_h=112, accent='#e31b23',
                    sheet_id=import_raw_tap_unified.PROFILES['CUSSONS']['spreadsheet_id']),
    'NPURE': dict(name='NPURE', logo='logo-npure.png', logo_h=150, accent='#1e5631',
                  sheet_id=npure_rules.SPREADSHEET_ID),
    'BLOOD': dict(name='Blood', logo=None, logo_h=0, accent='#7a1020',
                  sheet_id=blood_rules.SPREADSHEET_ID),
}
ALL_BRAND_WORDS = ('ELLIPS',) + tuple(BRANDS)  # Ellips tidak ada di halaman ini, tapi file-nya tetap harus ditolak

IMPORTS = {
    'Raw TAP': dict(sub='dari file TAP_GMV', module='import_raw_tap_unified', types=['xlsx'], auto_brand=True, zip_only=True,
                    note='Baris GMV ≠ 0 ditambah di bawah data yang ada, tanpa cek duplikat. Jangan import file '
                         'yang rentang tanggalnya tumpang tindih dengan yang sudah masuk.'),
    'Raw SC': dict(sub='dari file SC_GMV', module='import_raw_data_sc_unified', types=['xlsx', 'csv'], auto_brand=True,
                   zip_only=False,  # modul SC sendiri bisa baca CSV walau namanya .xlsx
                   note='Semua order ditambah di bawah data yang ada, tanpa cek duplikat. Jangan import file '
                        'yang rentang tanggalnya tumpang tindih dengan yang sudah masuk.'),
    'Live Streaming': dict(sub='dari file TAP_LS', module='import_live_streaming_unified', types=['xlsx'], auto_brand=False,
                           zip_only=True,
                           note='Room yang sudah ada dilewati; room lama hanya diperbarui GMV-nya kalau angka terbaru lebih besar.'),
    'Video Bank': dict(sub='dari file TAP_SV / SC_SV', module='import_video_bank_unified', types=['xlsx'], auto_brand=False,
                       zip_only=True,
                       note='Video yang sudah ada dilewati; video lama hanya diperbarui GMV-nya kalau angka terbaru lebih besar.'),
}
TARGET_ID_MODULES = ('import_live_streaming_unified', 'import_video_bank_unified')

MONTHS = ['Semua bulan', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
          'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

CSS = """
<style>
:root{--bg:#f4f4f5;--panel:#fff;--ink:#000;--ink2:#3d3d3d;--muted:#6b6b6b;--line:#e4e4e7;--gold:#ffd700;
  --shadow:0 1px 2px rgba(16,16,16,.05),0 8px 24px rgba(16,16,16,.06)}
html,body,[data-testid="stApp"]{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-variant-numeric:tabular-nums}
[data-testid="stApp"],[data-testid="stAppViewContainer"]{background:var(--bg)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"],[data-testid="stDecoration"],#MainMenu,footer{display:none}
.block-container{max-width:1280px;padding:28px 32px 64px}

/* sidebar */
section[data-testid="stSidebar"]{background:#000;width:250px !important;min-width:250px !important;border-right:1px solid rgba(255,255,255,.18)}
section[data-testid="stSidebar"] *{color:#fff}
section[data-testid="stSidebar"] .side-brand{color:#c6cbc7;font-size:13px;margin:10px 0 12px}
section[data-testid="stSidebar"] .side-label{color:#c6cbc7;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:20px 0 6px}
section[data-testid="stSidebar"] .stButton button{background:transparent;border:1px solid transparent;border-radius:4px;
  justify-content:flex-start;padding:10px 12px;min-height:44px;font-weight:500;text-align:left}
section[data-testid="stSidebar"] .stButton button > div,section[data-testid="stSidebar"] .stButton button p{width:100%;justify-content:flex-start;text-align:left}
section[data-testid="stSidebar"] .stButton button:hover{background:rgba(255,255,255,.12)}
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"]{background:#fff;border-color:#fff}
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] *{color:#000}
section[data-testid="stSidebar"] .st-key-switch button{border:1px solid rgba(255,255,255,.18);border-radius:6px;font-size:13px}
section[data-testid="stSidebar"] .st-key-logout button{border:1px solid rgba(255,255,255,.18);border-radius:6px}
.user{display:flex;gap:10px;align-items:center;min-width:0;padding-top:16px;border-top:1px solid rgba(255,255,255,.18);margin-top:24px}
.avatar{width:32px;height:32px;border-radius:50%;background:#fff;color:#000 !important;display:grid;place-items:center;font-weight:700;flex:none;overflow:hidden}
.avatar img{width:100%;height:100%;object-fit:cover}
.uname{font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.umail{color:#c6cbc7 !important;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* judul halaman */
h1.ptitle{font-size:32px;line-height:1.1;margin:0 0 6px;letter-spacing:-.01em;padding:0}
.psub{margin:0 0 24px;color:var(--muted);font-size:16px}
.pk-eyebrow{margin:0 0 8px;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pk-lead{margin:0 0 32px;color:var(--ink2);max-width:62ch}

/* tombol utama = emas (hanya tombol aksi) */
.stMain .stButton button[data-testid="stBaseButton-primary"]{background:var(--gold);color:#000;border:0;border-radius:6px;
  font-weight:700;min-height:44px}
.stMain .stButton button[data-testid="stBaseButton-primary"]:hover{filter:brightness(.95)}
.stMain .stButton button[data-testid="stBaseButton-primary"]:disabled{opacity:.5}

/* kartu isi */
.st-key-form,.st-key-result{background:var(--panel);border-radius:10px;padding:22px 24px;box-shadow:var(--shadow)}
.st-key-result{margin-top:24px}
.banner{display:flex;gap:10px;align-items:flex-start;border:1px solid #000;background:var(--panel);border-radius:8px;padding:12px 14px;margin:12px 0}
.banner.bad{border-color:#d03b3b;background:#fbe9e9}
.banner.ok{border-color:#0ca30c;background:#e8f6e8}
.tgt{font-size:13px;color:var(--muted);margin:0 0 16px}

/* pilih brand */
[class*="st-key-card_"]{position:relative;background:var(--panel);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;
  gap:0 !important;transition:transform 280ms cubic-bezier(.2,.8,.2,1),box-shadow 280ms}
[class*="st-key-card_"]::before{content:"";position:absolute;inset:0 0 auto;height:5px;background:var(--accent);z-index:2;
  transform-origin:left;transform:scaleX(.2);transition:transform 360ms cubic-bezier(.2,.8,.2,1)}
[class*="st-key-card_"]:hover{transform:translateY(-10px);box-shadow:0 2px 4px rgba(16,16,16,.06),0 24px 48px rgba(16,16,16,.16)}
[class*="st-key-card_"]:hover::before{transform:scaleX(1)}
.pk-logo{height:180px;display:grid;place-items:center;background:#fff;border-bottom:1px solid var(--line)}
.pk-logo img{width:auto;max-width:78%;object-fit:contain}
.pk-logo-txt{font-size:30px;font-weight:700;color:#000}
.pk-name{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:20px 22px 6px}
.pk-name h2{margin:0;font-size:21px;padding:0}
.pk-tag{font-size:13px;color:var(--muted)}
[class*="st-key-card_"] [data-testid="stElementContainer"]:has(.stButton){padding:8px 22px 22px}
[class*="st-key-card_"] .stButton button{background:#000;color:#fff;border:0;border-radius:6px;min-height:44px;font-weight:700}
[class*="st-key-card_"] .stButton button *{color:#fff}
[class*="st-key-card_"] .stButton button:hover{background:var(--accent)}

/* login */
.st-key-login{background:var(--panel);border:1px solid #000;overflow:hidden;gap:0 !important}
.login-head{background:#000;padding:28px 24px}
.login-head img{height:56px;display:block}
.login-body{padding:24px 24px 8px}
.login-body h1{margin:0 0 6px;font-size:22px;padding:0}
.login-body p{margin:0 0 12px;color:var(--ink2)}
.st-key-login [data-testid="stElementContainer"]:has(.stButton){padding:0 24px 24px}
.st-key-login .stButton button{background:#000;color:#fff;border:0;border-radius:6px;min-height:44px;font-weight:700}
.st-key-login .stButton button *{color:#fff}

@media (max-width:720px){.block-container{padding:20px 16px 40px}h1.ptitle{font-size:25px}}
@media (prefers-reduced-motion:reduce){[class*="st-key-card_"],[class*="st-key-card_"]::before{transition:none !important}
  [class*="st-key-card_"]:hover{transform:none !important}}
</style>
"""


@st.cache_data
def data_uri(path):
    p = Path(path)
    mime = {'.png': 'image/png', '.webp': 'image/webp'}.get(p.suffix, 'image/png')
    return f'data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}'


def has_secret(key):
    try:
        return key in st.secrets
    except FileNotFoundError:  # StreamlitSecretNotFoundError: secrets.toml belum ada
        return False


@st.cache_resource
def import_lock():
    # modul import_*_unified pakai variabel global (path file, bulan, dst) + sys.stdout ditangkap -> satu import sekali jalan
    return threading.Lock()


@st.cache_resource
def credentials_file():
    local = PROJECT_DIR / 'credentials.json'
    if local.exists():
        return str(local)
    if has_secret('gcp_service_account'):
        import json
        info = dict(st.secrets['gcp_service_account'])
        info['private_key'] = fix_pem(info.get('private_key', ''))
        path = Path(tempfile.mkdtemp(prefix='sa_')) / 'credentials.json'
        path.write_text(json.dumps(info))
        return str(path)
    return None


def fix_pem(key):
    """Secrets TOML sering merusak baris baru private key (\\n jadi teks biasa, atau jadi spasi) ->
    error 'MalformedFraming'. Bangun ulang PEM yang valid dari isi base64-nya."""
    m = re.search(r'-----BEGIN ([A-Z ]+)-----(.*?)-----END \1-----', key, re.S)
    if not m:
        return key
    body = re.sub(r'\\n|\s', '', m.group(2))
    lines = '\n'.join(body[i:i + 64] for i in range(0, len(body), 64))
    return f'-----BEGIN {m.group(1)}-----\n{lines}\n-----END {m.group(1)}-----\n'


def detect_brand(filename):
    low = filename.lower()
    return next((b for b in ALL_BRAND_WORDS if b.lower() in low), None)


def sniff_xlsx(upload):
    """None kalau isinya memang xlsx (arsip zip); selain itu penjelasan singkat kenapa import bakal gagal
    (BadZipFile: File is not a zip file)."""
    buf = upload.getbuffer()
    head = bytes(buf[:2048])
    if head[:2] == b'PK':
        return None
    mb = f'{upload.size / 1024 ** 2:.1f} MB'
    if head[:4] == b'\xd0\xcf\x11\xe0':
        return f'File ({mb}) bukan .xlsx: formatnya Excel lama (.xls) atau diberi password. Buka di Excel lalu Save As .xlsx.'
    try:
        first = head.decode('utf-8-sig').splitlines()[0]
        if any(c in first for c in ',;\t'):
            return (f'File ({mb}) ternyata CSV yang diberi ekstensi .xlsx. Export ulang sebagai .xlsx, '
                    'atau buka di Excel lalu Save As .xlsx.')
    except (UnicodeDecodeError, IndexError):
        pass
    return f'File ({mb}) bukan .xlsx yang valid: rusak atau upload terpotong. Upload ulang atau export ulang dari TikTok.'


def first_name(user):
    label = user.get('name') or (user.get('email') or '').split('@')[0]
    return label, label.split(' ')[0] if label else ''


# ------------------------------------------------------------------ login ----
def login_page(message=None, can_logout=False):
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown('<div style="height:12vh"></div>', unsafe_allow_html=True)
        with st.container(key='login'):
            st.markdown(
                f'<div class="login-head"><img src="{data_uri(ASSETS / "logo-wei.png")}" alt="WEI"></div>'
                '<div class="login-body"><h1>Masuk</h1>'
                f'<p>Gunakan akun Google {ALLOWED_DOMAIN}.</p>'
                + (f'<div class="banner bad">{message}</div>' if message else '') + '</div>',
                unsafe_allow_html=True)
            if can_logout:
                st.button('Keluar dan coba akun lain', on_click=st.logout, width='stretch')
            else:
                st.button('Masuk dengan Google', on_click=st.login, width='stretch')


def auth_gate():
    """Kembalikan st.user kalau sudah login dengan email WEI yang terverifikasi, selain itu tampilkan layar masuk & berhenti."""
    if not has_secret('auth'):
        st.error('Login Google belum disiapkan: isi bagian [auth] di .streamlit/secrets.toml '
                 '(lihat .streamlit/secrets.toml.example).')
        st.stop()
    if not st.user.is_logged_in:
        login_page()
        st.stop()
    email = (st.user.get('email') or '').lower()
    extra = {str(e).strip().lower() for e in st.secrets.get('allowed_emails', [])}  # akun di luar domain WEI
    if not (st.user.get('email_verified') and (email.endswith(ALLOWED_DOMAIN) or email in extra)):
        login_page(f'Akun {email or "ini"} tidak diizinkan. Hanya email {ALLOWED_DOMAIN} yang terverifikasi Google.',
                   can_logout=True)
        st.stop()
    return st.user


# ----------------------------------------------------------------- sidebar ---
def sidebar(user, brand):
    label, _ = first_name(user)
    pic = user.get('picture')
    avatar = f'<img src="{pic}" alt="" referrerpolicy="no-referrer">' if pic else (label[:1] or '?').upper()
    with st.sidebar:
        st.markdown(f'<img src="{data_uri(ASSETS / "logo-wei.png")}" alt="WEI" style="height:32px">',
                    unsafe_allow_html=True)
        if brand:
            st.markdown(f'<div class="side-brand">{BRANDS[brand]["name"]}</div>', unsafe_allow_html=True)
            if st.button('←  Ganti brand', key='switch', width='stretch'):
                st.query_params.clear()
                st.rerun()
            st.markdown('<div class="side-label">Import</div>', unsafe_allow_html=True)
            for name in IMPORTS:
                if st.button(name, key=f'nav_{name}', width='stretch',
                             type='primary' if st.session_state.page == name else 'secondary'):
                    st.session_state.page = name
                    st.rerun()
        st.markdown(f'<div class="user"><div class="avatar">{avatar}</div><div style="min-width:0">'
                    f'<div class="uname">{label}</div><div class="umail">{user.get("email", "")}</div></div></div>',
                    unsafe_allow_html=True)
        st.button('Keluar', key='logout', on_click=st.logout, width='stretch')


# ------------------------------------------------------------ pilih brand ---
def picker_page(user):
    _, first = first_name(user)
    st.markdown('<p class="pk-eyebrow">Import data</p>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="ptitle">{f"Halo, {first}. " if first else ""}Mau import ke brand mana?</h1>',
                unsafe_allow_html=True)
    st.markdown('<p class="pk-lead">Pilih brand, lalu upload file Raw TAP, Raw SC, Live Streaming, atau Video Bank '
                'dari TikTok.</p>', unsafe_allow_html=True)
    st.markdown('<style>' + ''.join(f'.st-key-card_{k}{{--accent:{b["accent"]}}}' for k, b in BRANDS.items())
                + '</style>', unsafe_allow_html=True)
    for col, (key, b) in zip(st.columns(len(BRANDS), gap='large'), BRANDS.items()):
        with col, st.container(key=f'card_{key}'):
            logo = (f'<img src="{data_uri(ASSETS / b["logo"])}" alt="Logo {b["name"]}" style="height:{b["logo_h"]}px">'
                    if b['logo'] else f'<span class="pk-logo-txt">{b["name"]}</span>')
            st.markdown(f'<div class="pk-logo">{logo}</div>'
                        f'<div class="pk-name"><h2>{b["name"]}</h2><span class="pk-tag">TikTok affiliate</span></div>',
                        unsafe_allow_html=True)
            if st.button(f'Buka import {b["name"]}  →', key=f'pick_{key}', width='stretch'):
                st.query_params['brand'] = key
                st.session_state.page = next(iter(IMPORTS))
                st.rerun()


# ------------------------------------------------------------------ import ---
class LogWriter(io.TextIOBase):
    """Tampung print() dari modul import dan tampilkan live di kotak kode."""

    def __init__(self, box):
        self.box, self.buf, self.t = box, '', 0.0

    def write(self, s):
        self.buf += s
        if time.time() - self.t > 0.3:
            self.flush()
        return len(s)

    def flush(self):
        self.box.code(self.buf[-30000:] or ' ', language=None)
        self.t = time.time()


def run_import(cfg, brand, upload, sheet_name, year, month, box):
    """Jalankan modul import untuk file upload. Kembalikan (berhasil, log)."""
    log = LogWriter(box)
    tmp = Path(tempfile.mkdtemp(prefix='import_'))
    ok = True
    try:
        src = tmp / Path(upload.name).name  # nama asli dipertahankan: brand dideteksi dari nama file
        src.write_bytes(upload.getbuffer())
        module = importlib.import_module(cfg['module'])
        module.CREDENTIALS_FILE = credentials_file()
        module.SOURCE_XLSX_PATH = str(src)
        module.SOURCE_SHEET_NAME = sheet_name or 'Custom report'
        if cfg['module'] in TARGET_ID_MODULES:
            module.TARGET_SPREADSHEET_ID = BRANDS[brand]['sheet_id']
        module.FILTER_YEAR = year
        module.FILTER_MONTH = month
        with contextlib.redirect_stdout(log):
            module.main()
    except Exception:
        log.write(traceback.format_exc())
        ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log.flush()
    return ok and not any(line.startswith('ERROR') for line in log.buf.splitlines()), log.buf


def import_page(brand):
    page = st.session_state.page
    cfg, b = IMPORTS[page], BRANDS[brand]
    st.markdown(f'<h1 class="ptitle">Import {page}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="psub">{b["name"]} · {cfg["sub"]}</p>', unsafe_allow_html=True)

    result_key = f'{brand}:{page}'
    with st.container(key='form'):
        st.markdown(f'<p class="tgt">Tujuan: sheet <b>[INT] {b["name"]}</b> · '
                    f'<a href="https://docs.google.com/spreadsheets/d/{b["sheet_id"]}/edit" target="_blank">buka sheet</a></p>',
                    unsafe_allow_html=True)
        upload = st.file_uploader('File sumber', type=cfg['types'], key=f'file_{result_key}')
        c1, c2 = st.columns(2)
        year = c1.number_input('Tahun', 2024, 2035, datetime.date.today().year, key=f'year_{result_key}')
        month_name = c2.selectbox('Bulan', MONTHS, key=f'month_{result_key}',
                                  help='Hanya baris di bulan ini yang masuk. "Semua bulan" = tanpa filter '
                                       '(Cussons otomatis pakai bulan terbanyak di file).')
        with st.expander('Opsi lanjutan'):
            sheet_name = st.text_input('Nama tab di file sumber', 'Custom report', key=f'tab_{result_key}',
                                       help='Biasanya "Custom report". Raw SC otomatis pakai tab pertama kalau namanya tidak ketemu.')

        detected = detect_brand(upload.name) if upload else None
        mismatch = bool(upload) and ((detected and detected != brand) or (cfg['auto_brand'] and not detected))
        if upload and mismatch:
            msg = (f'File terdeteksi {detected}, tetapi brand yang dipilih {brand}.' if detected
                   else f'Nama file harus memuat kata "{brand.lower()}".')
            st.markdown(f'<div class="banner bad">{msg}</div>', unsafe_allow_html=True)
        problem = sniff_xlsx(upload) if upload and cfg['zip_only'] else None
        if problem:
            st.markdown(f'<div class="banner bad">{problem}</div>', unsafe_allow_html=True)
        mismatch = mismatch or bool(problem)
        st.markdown(f'<div class="banner">{cfg["note"]}</div>', unsafe_allow_html=True)

        confirmed = st.checkbox(f'File dan bulan sudah benar, import langsung menulis ke sheet {b["name"]}.',
                                key=f'ok_{result_key}')
        go = st.button('Jalankan import', type='primary', key=f'go_{result_key}',
                       disabled=not (upload and confirmed) or mismatch)

    if go:
        if credentials_file() is None:
            st.error('credentials.json tidak ketemu dan [gcp_service_account] belum diisi di secrets.')
            return
        lock = import_lock()
        if not lock.acquire(blocking=False):
            st.warning('Ada import lain yang sedang berjalan. Tunggu selesai lalu coba lagi.')
            return
        try:
            with st.status(f'Mengimpor {upload.name}...', expanded=True) as status:
                ok, text = run_import(cfg, brand, upload, sheet_name.strip(), int(year),
                                      None if month_name == MONTHS[0] else MONTHS.index(month_name), st.empty())
                status.update(label='Selesai' if ok else 'Gagal, lihat log', state='complete' if ok else 'error')
        finally:
            lock.release()
        st.session_state.results[result_key] = (ok, upload.name, text)
        st.rerun()

    if result_key in st.session_state.results:
        ok, name, text = st.session_state.results[result_key]
        with st.container(key='result'):
            st.markdown(f'<div class="banner {"ok" if ok else "bad"}">'
                        f'{"Selesai" if ok else "Gagal"}: {name}</div>', unsafe_allow_html=True)
            st.code(text[-30000:] or ' ', language=None)


# -------------------------------------------------------------------- main ---
def render(user):
    st.session_state.setdefault('page', next(iter(IMPORTS)))
    st.session_state.setdefault('results', {})
    brand = st.query_params.get('brand')
    brand = brand if brand in BRANDS else None
    sidebar(user, brand)
    if brand:
        import_page(brand)
    else:
        picker_page(user)


def main():
    st.set_page_config(page_title='Import Data · WEI', page_icon=str(ASSETS / 'favicon.png'),
                       layout='wide', initial_sidebar_state='expanded')
    st.markdown(CSS, unsafe_allow_html=True)
    render(auth_gate())


if __name__ == '__main__':
    main()
