#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import math
import pandas as pd
from pathlib import Path

# Prophet import dengan fallback
try:
    from prophet import Prophet
except ModuleNotFoundError:
    try:
        from fbprophet import Prophet
    except ModuleNotFoundError:
        print("ERROR: Prophet belum terpasang. Jalankan: pip install prophet", file=sys.stderr)
        sys.exit(1)


def prepare_series(df, cabang, bahan):
    """Ambil data jmlhKeluar harian untuk (cabang, bahan) -> kolom ds (datetime harian) & y (angka)."""
    sub = df[(df["namaCabang"] == cabang) & (df["namaBahan"] == bahan)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["ds", "y"])

    # Parse ke datetime
    sub["tanggal"] = pd.to_datetime(sub["tanggal"], errors="coerce", infer_datetime_format=True)
    sub = sub.dropna(subset=["tanggal"])

    # Buat kolom 'ds' (tanggal harian tanpa jam)
    sub["ds"] = sub["tanggal"].dt.floor("D")  # atau .dt.normalize()

    # Agregasi per hari pakai kolom 'ds'
    daily = sub.groupby("ds", as_index=False)["jmlhKeluar"].sum()

    # Prophet butuh y = angka
    daily = daily.rename(columns={"jmlhKeluar": "y"})

    # Isi tanggal yang hilang (anggap 0 demand)
    daily = daily.set_index("ds").asfreq("D", fill_value=0).reset_index()

    # Pastikan non-negatif
    daily["y"] = daily["y"].clip(lower=0)
    return daily


def compute_safety_stock(y, z=1.0, window=14):
    """Safety stock sederhana = std rolling * z (ambil terakhir)."""
    if y.empty:
        return 0.0
    if len(y) < window:
        std = y.std()
    else:
        std = y.rolling(window=window).std().iloc[-1]
        if pd.isna(std):
            std = y.std()
    return float(max(0.0, z * std))


def fit_and_forecast(series_df, days):
    """Latih Prophet & prediksi ke depan (hari)."""
    if series_df.empty:
        return None
    m = Prophet(weekly_seasonality=True, daily_seasonality=False, yearly_seasonality=False)
    m.fit(series_df)
    future = m.make_future_dataframe(periods=days, freq="D", include_history=False)
    forecast = m.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path ke riwayatStok.csv")
    parser.add_argument("--output", required=True, help="Path output CSV detail prediksi")
    parser.add_argument("--days", type=int, default=14, help="Horizon prediksi (hari)")
    parser.add_argument("--z", type=float, default=1.0, help="Z-score untuk safety stock (1.64 ~95%)")
    parser.add_argument("--min_history", type=int, default=14, help="Minimal jumlah hari historis")
    parser.add_argument("--per_cabang_dir", type=str, default=None, help="Folder untuk simpan CSV per cabang (opsional)")
    parser.add_argument("--plot", action="store_true", help="Tampilkan 1 plot contoh di akhir (opsional)")
    parser.add_argument("--ceil", action="store_true", help="Bulatkan stokIdeal selalu ke atas (ceil)")
    args = parser.parse_args()

    # Pastikan path input dapat ditemukan (absolut)
    inp_path_raw = args.input
    inp_path = Path(inp_path_raw).expanduser().resolve()
    if not inp_path.exists():
        # Coba relatif terhadap lokasi script
        script_dir = Path(__file__).resolve().parent
        alt = (script_dir / inp_path_raw).resolve()
        if alt.exists():
            inp_path = alt

    if not inp_path.exists():
        print("❌ File input tidak ditemukan.")
        print("Dicoba:", Path(inp_path_raw).expanduser().resolve())
        sys.exit(1)

    print("✅ Membaca:", str(inp_path))
    df = pd.read_csv(inp_path)

    required_cols = {"namaCabang", "namaBahan", "tanggal", "jmlhKeluar"}
    if not required_cols.issubset(df.columns):
        print(f"❌ Kolom wajib hilang: {required_cols - set(df.columns)}")
        sys.exit(1)

    hasil = []
    per_cabang_frames = {}
    last_data = None
    last_pred = None
    last_cabang = None
    last_bahan = None

    # Loop per cabang-bahan
    for cabang in df["namaCabang"].unique():
        bahan_list = df.loc[df["namaCabang"] == cabang, "namaBahan"].unique()
        for bahan in bahan_list:
            series = prepare_series(df, cabang, bahan)
            if series["ds"].nunique() < args.min_history:
                continue

            safety = compute_safety_stock(series["y"], z=args.z, window=14)

            fc = fit_and_forecast(series, args.days)
            if fc is None or fc.empty:
                continue

            # Prediksi & stok ideal
            fc = fc.copy()
            fc["pred_keluar"] = fc["yhat"].clip(lower=0)
            fc["pred_low"] = fc["yhat_lower"].clip(lower=0)
            fc["pred_high"] = fc["yhat_upper"].clip(lower=0)
            fc["safety_stock"] = safety
            fc["stok_ideal"] = fc["pred_keluar"] + safety

            fc["namaCabang"] = cabang
            fc["namaBahan"] = bahan

            hasil.append(fc)

            # Simpan untuk output per cabang & contoh plot
            per_cabang_frames.setdefault(cabang, [])
            per_cabang_frames[cabang].append(fc)
            last_data, last_pred = series, fc
            last_cabang, last_bahan = cabang, bahan

    # Jika tidak ada model dilatih → tetap buat file stokIdeal=0 agar file jadi
    if not hasil:
        print("⚠️ Model tidak dilatih (historis terlalu pendek untuk semua pasangan).")
        df_ori = pd.read_csv(inp_path)
        df_ori["stokIdeal"] = 0
        out_simple = inp_path.parent / f"{inp_path.stem}_dengan_stokIdeal.csv"
        out_simple.parent.mkdir(parents=True, exist_ok=True)
        df_ori.to_csv(out_simple, index=False, encoding="utf-8-sig")
        print("📄 Tetap dibuat:", str(out_simple.resolve()))
        sys.exit(0)

    # Gabungkan detail & simpan
    out = pd.concat(hasil, ignore_index=True)
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print("✅ Prediksi detail tersimpan di:", str(out_path))

    # Simpan per-cabang jika diminta
    if args.per_cabang_dir:
        per_dir = Path(args.per_cabang_dir).expanduser().resolve()
        per_dir.mkdir(parents=True, exist_ok=True)
        for cabang, frames in per_cabang_frames.items():
            cabang_df = pd.concat(frames, ignore_index=True)
            cabang_file = per_dir / f"prediksi_{cabang}.csv"
            cabang_df.to_csv(cabang_file, index=False, encoding="utf-8-sig")
        print("📁 Output per cabang di:", str(per_dir))

    # ====== Tambahkan 1 atribut 'stokIdeal' ke file input (dibulatkan integer) ======
    # Ambil stok_ideal rata-rata per (cabang, bahan)
    stok_pred = (
        out.groupby(["namaCabang", "namaBahan"], as_index=False)["stok_ideal"]
           .mean()
           .rename(columns={"stok_ideal": "stokIdeal"})
    )
    # Pembulatan: round (default) atau ceil jika --ceil dipakai
    if args.ceil:
        stok_pred["stokIdeal"] = stok_pred["stokIdeal"].apply(lambda x: math.ceil(x)).astype(int)
    else:
        stok_pred["stokIdeal"] = stok_pred["stokIdeal"].round().astype(int)

    # Merge ke CSV asli
    df_ori = pd.read_csv(inp_path)
    merged = df_ori.merge(stok_pred, on=["namaCabang", "namaBahan"], how="left")
    merged["stokIdeal"] = merged["stokIdeal"].fillna(0).astype(int)

    out_simple = inp_path.parent / f"{inp_path.stem}_dengan_stokIdeal.csv"
    out_simple.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_simple, index=False, encoding="utf-8-sig")
    print("✅ File input + 1 kolom 'stokIdeal' tersimpan di:", str(out_simple.resolve()))

    # =============== Opsional: 1 plot contoh terakhir yang dilatih ===============
    if args.plot and last_data is not None and last_pred is not None:
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(8, 4))
            plt.plot(last_data["ds"], last_data["y"], label="Historis keluar")
            plt.plot(last_pred["ds"], last_pred["pred_keluar"], label="Prediksi")
            plt.title(f"{last_cabang} - {last_bahan}")
            plt.legend()
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print("Plot gagal ditampilkan (abaikan jika tidak perlu). Detail:", e)


if __name__ == "__main__":
    main()
