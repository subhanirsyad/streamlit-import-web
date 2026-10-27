"""Update GMV baris yang sudah ada di sheet kalau raw data terbaru lebih besar.

Dipakai import_video_bank_unified & import_live_streaming_unified: ID yang udah
ada tetap gak ditambah lagi, tapi GMV-nya dibandingin -- yang lebih besar menang
(GMV TikTok cuma bisa naik seiring waktu, jadi angka yang lebih kecil = raw lama).
"""

BATCH = 1000


def read_gmv_column(service, spreadsheet_id, sheet, col, first_data_row):
    """Isi kolom GMV apa adanya (angka / rumus). None kalau header kolom itu bukan GMV
    atau kolomnya berisi rumus -- kolom kayak gitu jangan ditimpa."""
    r = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{sheet}'!{col}:{col}", valueRenderOption='FORMULA'
    ).execute()
    vals = [row[0] if row else '' for row in r.get('values', [])]
    header = vals[first_data_row - 2] if len(vals) >= first_data_row - 1 else ''
    if 'gmv' not in str(header).lower():
        print(f'  GMV dilewati: header kolom {col} di baris {first_data_row - 1} = "{header}", bukan GMV.')
        return None
    if any(isinstance(v, str) and v.startswith('=') for v in vals[first_data_row - 1:]):
        print(f'  GMV dilewati: kolom {col} berisi rumus, gak ditimpa.')
        return None
    return vals


def plan_updates(col_vals, items):
    """items: [(nomor baris sheet, GMV baru)]. Return ([(baris, lama, baru)], jumlah sel teks yang dilewati).
    Sel kosong dianggap 0 dan diisi (GMV 0 pun ditulis 0, biar gak kosong). Sel yang udah
    keisi cuma diupdate kalau baru > lama."""
    updates, skipped_text = [], 0
    for row, new in items:
        if not row or not isinstance(new, (int, float)) or new < 0:
            continue
        old = col_vals[row - 1] if row <= len(col_vals) else ''
        blank = old == ''
        if blank:
            old = 0.0
        elif not isinstance(old, (int, float)):
            skipped_text += 1
            continue
        if new > old or blank:
            updates.append((row, old, new))
    return updates, skipped_text


def update_existing_gmv(service, spreadsheet_id, sheet, col, first_data_row, items):
    """Return True kalau kolom GMV aman dipakai (updatenya jalan), False kalau dilewati."""
    vals = read_gmv_column(service, spreadsheet_id, sheet, col, first_data_row)
    if vals is None:
        return False
    updates, skipped_text = plan_updates(vals, items)
    print(f'  GMV: {len(items)} baris lama dicek, {len(updates)} naik di raw terbaru'
          + (f', {skipped_text} sel berisi teks dilewati' if skipped_text else '') + '.')
    for row, old, new in updates[:10]:
        print(f'    baris {row}: {old:,.0f} -> {new:,.0f}')
    if len(updates) > 10:
        print(f'    ... dan {len(updates) - 10} lainnya.')
    data = [{'range': f"'{sheet}'!{col}{row}", 'values': [[new]]} for row, _, new in updates]
    for i in range(0, len(data), BATCH):
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body={'valueInputOption': 'USER_ENTERED', 'data': data[i:i + BATCH]}
        ).execute()
    return True


if __name__ == '__main__':
    vals = ['', 'GMV', 100, '', 500, 'abc']  # baris 1..6
    ups, sk = plan_updates(vals, [(3, 150), (3, 100), (4, 80), (5, 400), (6, 999), (7, 10), (1, 0), (None, 5)])
    assert ups == [(3, 100, 150), (4, 0.0, 80), (7, 0.0, 10), (1, 0.0, 0)], ups  # (1, 0): sel kosong diisi 0
    assert sk == 1
    print('OK')
