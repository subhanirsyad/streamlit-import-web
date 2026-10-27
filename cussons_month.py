"""Aturan per-bulan Cussons buat import_raw_tap_unified & import_raw_data_sc_unified:
nama tab, nama roster, rumus WEEK. Bulan baru? Tambah 1 baris di WEEK_ENDS."""

import calendar
from collections import Counter

MONTH_NAME_EN = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December',
}

# Tanggal terakhir minggu 1-4 tiap bulan (minggu 5 = sisa bulan).
WEEK_ENDS = {
    9: (6, 13, 20, 27),
    10: (5, 12, 19, 26),
}


def target_month(year, month, found):
    """month dari pilihan user; kalau None, ambil bulan terbanyak di data (found = list of (year, month))."""
    if not month:
        if not found:
            raise ValueError('Gak ada tanggal valid di data, gak bisa nentuin bulan. Pilih bulannya manual.')
        year, month = Counter(found).most_common(1)[0][0]
        print(f'Bulan dipilih otomatis dari data: {MONTH_NAME_EN[month]} {year}.')
    if month not in WEEK_ENDS:
        raise ValueError(f'Batas minggu {MONTH_NAME_EN[month]} belum diisi -- tambah di WEEK_ENDS (cussons_month.py).')
    return year, month


def tab_name(prefix, year, month):
    """prefix 'TAP' / 'SC' -> 'TAP Cussons (1-31 October)'"""
    return f'{prefix} Cussons (1-{calendar.monthrange(year, month)[1]} {MONTH_NAME_EN[month]})'


# Tab hasil gabungan TAP+SC per bulan (combine_tap_sc_cussons.py). Bulan baru? Tambah di sini.
GABUNGAN_TABS = {9: 'Gabungan TAP&SC Sep', 10: 'Gabungan TAP&SC Oct'}


def gabungan_name(month):
    if month not in GABUNGAN_TABS:
        raise ValueError(f'Nama tab Gabungan {MONTH_NAME_EN[month]} belum diisi -- tambah di GABUNGAN_TABS (cussons_month.py).')
    return GABUNGAN_TABS[month]


def roster_name(year, month):
    return f"Creator Performance PZ Cussons {MONTH_NAME_EN[month]}'{str(year)[-2:]}"


def week_formula(d, month, ends=None):
    """Rumus WEEK buat sel tanggal `d` (misal 'A5'), contoh: OCT W2 (6-12).
    `ends` = (e1..e4) kalau batas minggunya bukan dari WEEK_ENDS (dipakai NPURE)."""
    e1, e2, e3, e4 = ends or WEEK_ENDS[month]
    w = f'IF(DAY({d})<={e1};1;IF(DAY({d})<={e2};2;IF(DAY({d})<={e3};3;IF(DAY({d})<={e4};4;5))))'
    s = (f'IF(DAY({d})<={e1};1;IF(DAY({d})<={e2};{e1 + 1};IF(DAY({d})<={e3};{e2 + 1};'
         f'IF(DAY({d})<={e4};{e3 + 1};{e4 + 1}))))')
    e = (f'IF(DAY({d})<={e1};{e1};IF(DAY({d})<={e2};{e2};IF(DAY({d})<={e3};{e3};'
         f'IF(DAY({d})<={e4};{e4};DAY(EOMONTH({d};0))))))')
    return f'=UPPER(TEXT({d};"MMM"))&" W"&{w}&" ("&{s}&"-"&{e}&")"'
