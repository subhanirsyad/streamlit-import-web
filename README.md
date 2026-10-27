# Import Data WEI (Streamlit)

Import Raw TAP / Raw SC / Live Streaming / Video Bank untuk PZ Cussons, NPURE, dan Blood.
Login Google (@warnaemasindonesia.com + daftar `allowed_emails`).

## Deploy ke Streamlit Community Cloud
1. Push folder ini ke repo GitHub (private).
2. https://share.streamlit.io -> New app -> pilih repo, main file `app_streamlit.py`.
3. Settings -> Secrets: tempel isi `.streamlit/secrets.toml.example` yang sudah diisi.
4. Google Cloud -> client OAuth yang dipakai -> **Authorized redirect URIs**: tambah
   `https://NAMA-APP.streamlit.app/oauth2callback` (bukan JavaScript origins).
5. Pastikan service account punya akses edit ke ketiga sheet.

Folder ini dibuat otomatis oleh `Streamlit_Import/siapkan_deploy.py` -- jangan edit modulnya di sini.
