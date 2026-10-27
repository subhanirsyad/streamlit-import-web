"""Aturan Blood buat import_*_unified: spreadsheet, nama tab roster, rumus WEEK.

Minggu Blood = Selasa-Senin (Okt: 1-5, 6-12, 13-19, 20-26, 27-31). Bulan baru? Tambah 1 baris
di WEEK_ENDS dan (kalau nama tab roster-nya bukan nama bulan penuh) di ROSTER_SUFFIX.
"""

from cussons_month import MONTH_NAME_EN, week_formula

SPREADSHEET_ID = '1BLTC_aaBTNzTjQ06fOke-If-Gi0jo5uWBbLlVIxRZ3o'  # [INT] Blood - Community Performance 2026

# Tanggal terakhir minggu 1-4 tiap bulan (minggu 5 = sisa bulan).
WEEK_ENDS = {10: (5, 12, 19, 26)}
ROSTER_SUFFIX = {10: 'Okt'}
# Data roster ("CreatorUsername" di kolom B) mulai baris 14; di atasnya ada ringkasan berisi angka 0.
ROSTER_FIRST_ROW = 14


def roster_name(year, month):
    return f'Creator Performance-{ROSTER_SUFFIX.get(month, MONTH_NAME_EN[month])}'


def week_ends(year, month):
    if month not in WEEK_ENDS:
        raise ValueError(f'Batas minggu {MONTH_NAME_EN[month]} belum diisi -- tambah di WEEK_ENDS (blood_rules.py).')
    return WEEK_ENDS[month]


def week(d, year, month):
    """Rumus WEEK buat sel tanggal `d`, contoh: OKT W2 (6-12)."""
    return week_formula(d, month, week_ends(year, month))


if __name__ == '__main__':
    assert roster_name(2026, 10) == 'Creator Performance-Okt'
    assert week_ends(2026, 10) == (5, 12, 19, 26)
    assert week('A2', 2026, 10).startswith('=UPPER(TEXT(A2;"MMM"))&" W"&IF(DAY(A2)<=5;1;')
    try:
        week_ends(2026, 11)
        raise SystemExit('harusnya error: November belum diisi')
    except ValueError:
        pass
    print('OK')
