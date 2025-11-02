import pandas as pd 
from datetime import datetime 
from main import app, db 
from main import Bahan, Cabang, Stock, Riwayat, User

def import_csv_to_model(model_class, csv_path):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace(' ', '')

    # Map names → IDs for Riwayat BEFORE filtering
    if model_class.__tablename__ == "riwayat":
        cabang_map = {c.namaCabang.strip(): c.id for c in Cabang.query.all()}
        bahan_map = {b.namaBahan.strip(): b.id for b in Bahan.query.all()}

        if 'namaCabang' in df.columns:
            df['idCabang'] = df['namaCabang'].map(lambda x: cabang_map.get(str(x).strip(), None))
        if 'namaBahan' in df.columns:
            df['idBahan'] = df['namaBahan'].map(lambda x: bahan_map.get(str(x).strip(), None))

        # Debug print after mapping
        print(df[['namaBahan', 'namaCabang', 'idBahan', 'idCabang']])

    # Now filter to only valid table columns
    valid_columns = {c.name for c in model_class.__table__.columns}
    df = df[[col for col in df.columns if col in valid_columns]]

    # Convert tanggal if exists
    if 'tanggal' in df.columns:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')

    imported_count = 0
    skipped_count = 0

    for _, row in df.iterrows():
        clean_row = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

        if model_class.__tablename__ == "riwayat":
            if clean_row.get("idCabang") is None or clean_row.get("idBahan") is None:
                print(f"⚠️ Skipping invalid row (missing FK): {clean_row}")
                skipped_count += 1
                continue

        obj = model_class(**clean_row)
        db.session.merge(obj)
        imported_count += 1

    db.session.commit()
    print(f"✅ Imported {imported_count} rows into {model_class.__tablename__} (skipped {skipped_count})")

if __name__ == "__main__":
    with app.app_context():
        
        db.create_all()
        new_user = User(username='Max', role='Owner', namaPanjang='Max Kennedy Kassy', email='mkennedykassy@gmail.com', noTelp='081371221122', alamat='Jl. Teratai')
        new_user.set_password('testpassword')
        db.session.add(new_user)
        db.session.flush()
        new_user = User(username='Eka', role='Manager')
        new_user.set_password('testpassword')
        db.session.add(new_user)
        db.session.flush()
        new_user = User(username='Hengky', role='Kepala Gudang')
        new_user.set_password('testpassword')
        db.session.add(new_user)
        db.session.flush()
        new_user = User(username='Simon', role='Bendahara')
        new_user.set_password('testpassword')
        db.session.add(new_user)
        db.session.flush()
        new_user = User(username='Rian', role='Staf Pembelian')
        new_user.set_password('testpassword')
        db.session.add(new_user)
        db.session.commit()
        
        print("Starting CSV import...")

        import_csv_to_model(Bahan, "bahan.csv")    # imports Bahan table
        import_csv_to_model(Cabang, "cabang.csv")  # imports Cabang table
        import_csv_to_model(Stock, "stock.csv")    # imports Stock table
        import_csv_to_model(Riwayat, "riwayat.csv")# imports Riwayat table with name→ID mapping

        print("✅ All imports complete! Schema and relations preserved.")
