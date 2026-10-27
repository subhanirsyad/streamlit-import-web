"""Aturan NPURE buat import_*_unified: spreadsheet, nama tab roster, rumus WEEK.

Minggu NPURE selalu Kamis-Rabu (Sep: 1-2, 3-9, 10-16, 17-23, 24-30), jadi batas
minggu dihitung dari kalender -- gak perlu tabel per bulan kayak Cussons.
"""

import calendar
import datetime

from cussons_month import MONTH_NAME_EN, week_formula

SPREADSHEET_ID = '1DDTEyL4L1Pyn72PejKN0_rZauyYz9Tjf1-XCD77QE_Q'  # [INT] NPURE - Community Performance 2026

# Tab roster: Agustus 'August', September 'Sept', Oktober 'Oct'; bulan yang gak ada di sini
# dipakai nama penuh. Nama tab bulan baru yang beda? Tambah di sini.
ROSTER_SUFFIX = {9: 'Sept', 10: 'Oct'}


def roster_name(year, month):
    return f'Creator Performance-{ROSTER_SUFFIX.get(month, MONTH_NAME_EN[month])}'


def week_ends(year, month):
    """Rabu pertama sampai keempat di bulan itu = tanggal akhir minggu 1-4 (minggu 5 = sisa bulan)."""
    last = calendar.monthrange(year, month)[1]
    return tuple([d for d in range(1, last + 1) if datetime.date(year, month, d).weekday() == 2][:4])


def week(d, year, month):
    """Rumus WEEK buat sel tanggal `d`, contoh: SEP W5 (24-30)."""
    return week_formula(d, month, week_ends(year, month))


if __name__ == '__main__':
    assert week_ends(2026, 9) == (2, 9, 16, 23)
    assert week_ends(2026, 8) == (5, 12, 19, 26)
    assert roster_name(2026, 9) == 'Creator Performance-Sept'
    assert roster_name(2026, 8) == 'Creator Performance-August'
    assert roster_name(2026, 10) == 'Creator Performance-Oct'
    print('OK. Oktober 2026:', week_ends(2026, 10))
