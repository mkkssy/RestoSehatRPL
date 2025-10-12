from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, ForeignKey
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Stock.db'
db = SQLAlchemy(app)

class Riwayat(db.Model):
    idPrefix = 'RWT'
    id = db.Column(db.String(5), primary_key=True)
    idCabang = db.Column(db.String(5), db.ForeignKey('cabang.id'), nullable=False)
    idBahan = db.Column(db.String(5), db.ForeignKey('bahan.id'), nullable=False)
    tanggal = db.Column(db.DateTime, default=datetime.utcnow)
    jmlhMasuk = db.Column(db.Integer, default=0)
    jmlhKeluar = db.Column(db.Integer, default=0)

    def __repr__ (self):
        return f'<Riwayat {self.id}>'

class Stock(db.Model):
    idPrefix = 'STK'
    id = db.Column(db.String(5), primary_key=True)
    idCabang = db.Column(db.String(5), ForeignKey('cabang.id', ondelete='CASCADE'), nullable=False,)
    idBahan = db.Column(db.String(5), ForeignKey('bahan.id', ondelete='CASCADE'), nullable=False)
    namaBahan = db.Column(db.String(200), nullable=False)
    jmlhBahan = db.Column(db.Integer, nullable=False)

    def __repr__ (self):
        return '<Stock %r>' % self.id

class Bahan(db.Model):
    idPrefix = 'BHN'
    id = db.Column(db.String(5), primary_key=True)
    namaBahan = db.Column(db.String(25), nullable=False)
    satuan = db.Column(db.String(8), nullable=False)
    hargaPerSatuan = db.Column(db.Integer, nullable=False)
    stocks = db.relationship('Stock', backref='bahan', lazy=True, cascade="all, delete-orphan")
    riwayat = db.relationship('Riwayat', backref='bahan', lazy=True)

    def __repr__ (self):
        return '<Bahan %r>' % self.id
    
    
class Cabang(db.Model):
    idPrefix = 'CBG'
    id = db.Column(db.String(5), primary_key=True)
    namaCabang = db.Column(db.String(25), nullable=False)
    stocks = db.relationship('Stock', backref='cabang', lazy=True, cascade="all, delete-orphan")
    riwayat = db.relationship('Riwayat', backref='cabang', lazy=True)

    def __repr__ (self):
        return '<Cabang %r>' % self.id

def generate_custom_id(model):
    prefix = getattr(model, 'idPrefix', '')
    last_entry = model.query.order_by(model.id.desc()).first()
    if last_entry:
        num = int(last_entry.id.replace(prefix, ""))
    else:
        num = 0
    return f"{prefix}{num+1:04d}"

@event.listens_for(db.session, 'before_flush')
def auto_generate_ids(session, flush_context, instances):
    for obj in session.new:
        if hasattr(obj, 'id') and getattr(obj, 'id', None) is None:
            if hasattr(obj, 'idPrefix'):
                obj.id = generate_custom_id(obj.__class__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stok", methods=['POST', 'GET'])
def stok():
    stocks = Stock.query.order_by(Stock.idCabang).all()
    cabangs = {stock.idCabang for stock in stocks}
    return render_template('stok.html', stocks=stocks, cabangs=cabangs)

@app.route("/tambah_bahan", methods=['POST', 'GET'])
def tambahBahan():
    if request.method == 'POST':
        namaBahan = request.form.getlist('namaBahan')
        satuan = request.form.getlist('satuan')
        hargaPerSatuan = request.form.getlist('hargaPerSatuan')

        for namaBahan, satuan, hargaPerSatuan in zip(namaBahan, satuan, hargaPerSatuan):
            if namaBahan.strip():
                bahan_baru = Bahan(
                    namaBahan=namaBahan,
                    satuan=satuan,
                    hargaPerSatuan=int(hargaPerSatuan)
                )
                db.session.add(bahan_baru)
                db.session.flush()

        for cabang in Cabang.query.all():
                    exists = Stock.query.filter_by(idCabang=cabang.id, idBahan=bahan_baru.id).first()
                    if not exists:
                        stok_baru = Stock(
                            idCabang=cabang.id,
                            idBahan=bahan_baru.id,
                            namaBahan=bahan_baru.namaBahan,
                            jmlhBahan=0
                        )
                        db.session.add(stok_baru)
        try:
            db.session.commit()
            return redirect("/bahan")
        except Exception as e:
            print(e)
            return 'There was a problem saving data'
    else:
        stocks = Bahan.query.order_by(Bahan.id).all()
        return render_template('tambah_bahan.html', stocks=stocks)
    
@app.route("/bahan")
def bahan():
    items = Bahan.query.order_by(Bahan.id).all()
    return render_template('bahan.html', items=items)

@app.route("/tambah_cabang", methods=['POST', 'GET'])
def tambahCabang():
    if request.method == 'POST':
        cabang = request.form['namaCabang']
        cabangBaru = Cabang(namaCabang=cabang)
        db.session.add(cabangBaru)
        db.session.flush()

        for bahan in Bahan.query.all():
            exists = Stock.query.filter_by(idCabang=cabangBaru.id, idBahan=bahan.id).first()
            if not exists:
                stok_baru = Stock(
                    idCabang=cabangBaru.id,
                    idBahan=bahan.id,
                    namaBahan=bahan.namaBahan,
                    jmlhBahan=0
                )
                db.session.add(stok_baru)
        try:
            db.session.commit()
            return redirect("/cabang")
        except:
            return 'There was a problem saving data'
    else:
        chains = Cabang.query.order_by(Cabang.id).all()
        return render_template('tambah_cabang.html', chains=chains)

@app.route("/cabang")
def cabang():
    chains = Cabang.query.order_by(Cabang.id).all()
    return render_template('cabang.html', chains=chains)

@app.route("/delete_bahan/<string:id>")
def deleteBahan(id):
    itemToDelete = Bahan.query.get_or_404(id)

    try:
        db.session.delete(itemToDelete)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        print(e)
        return "There was a problem deleting data"
    
@app.route("/delete_cabang/<string:id>")
def deleteCabang(id):
    chainToDelete = Cabang.query.get_or_404(id)

    try:
        db.session.delete(chainToDelete)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        print(e)
        return "There was a problem deleting data"
    
@app.route("/pengiriman", methods=['POST', 'GET'])
def pengiriman():
    pusat_cabang_id = "CBG0001"
    bahans = Bahan.query.order_by(Bahan.id).all()
    cabangs = Cabang.query.filter(Cabang.id != pusat_cabang_id).all()

    if request.method == "POST":
        selected_bahan_id = request.form["dropdownBahan"]
        selected_cabang_id = request.form["dropdownCabang"]
        jumlah = int(request.form["jmlhBahan"])

        # Get bahan and stock entries
        bahan = Bahan.query.filter_by(id=selected_bahan_id).first()
        if not bahan:
            return "Error: bahan not found."

        pusat_stock = Stock.query.filter_by(idCabang=pusat_cabang_id, idBahan=selected_bahan_id).first()
        target_stock = Stock.query.filter_by(idCabang=selected_cabang_id, idBahan=selected_bahan_id).first()

        if not pusat_stock or pusat_stock.jmlhBahan < jumlah:
            return "Error: Stok pusat tidak cukup."

        # 🔹 Deduct from pusat
        pusat_stock.jmlhBahan -= jumlah

        # 🔹 Add to branch
        if target_stock:
            target_stock.jmlhBahan += jumlah
        else:
            target_stock = Stock(
                idCabang=selected_cabang_id,
                idBahan=selected_bahan_id,
                namaBahan=bahan.namaBahan,
                jmlhBahan=jumlah
            )
            db.session.add(target_stock)

        # 🔹 Record Riwayat for both pusat & cabang
        riwayat_pusat = Riwayat(
            idCabang=pusat_cabang_id,
            idBahan=selected_bahan_id,
            tanggal=datetime.now(),
            jmlhMasuk=0,
            jmlhKeluar=jumlah
        )
        riwayat_cabang = Riwayat(
            idCabang=selected_cabang_id,
            idBahan=selected_bahan_id,
            tanggal=datetime.now(),
            jmlhMasuk=jumlah,
            jmlhKeluar=0
        )
        db.session.add(riwayat_pusat)
        db.session.flush()
        db.session.add(riwayat_cabang)
        db.session.commit()

        return redirect("/stok")

    return render_template("pengiriman.html", bahans=bahans, cabangs=cabangs)

@app.route("/order", methods=['POST', 'GET'])
def order():
    bahans = Bahan.query.order_by(Bahan.id).all()
    pusat_cabang_id = "CBG0001"  # Cabang pusat default

    if request.method == "POST":
        selected_bahan_id = request.form["dropdownBahan"]
        jumlah = int(request.form["jmlhBahan"])

        bahan = Bahan.query.filter_by(id=selected_bahan_id).first()
        if not bahan:
            return "Error: bahan not found"

        total_cost = bahan.hargaPerSatuan * jumlah

        stock_entry = Stock.query.filter_by(idCabang=pusat_cabang_id, idBahan=selected_bahan_id).first()

        if stock_entry:
            stock_entry.jmlhBahan += jumlah
        else:
            stock_entry = Stock(
                idCabang=pusat_cabang_id,
                idBahan=selected_bahan_id,
                namaBahan=bahan.namaBahan,
                jmlhBahan=jumlah
            )
            db.session.add(stock_entry)

        # 🔹 Record Riwayat (Masuk ke pusat)
        riwayat = Riwayat(
            idCabang=pusat_cabang_id,
            idBahan=selected_bahan_id,
            tanggal=datetime.now(),
            jmlhMasuk=jumlah,
            jmlhKeluar=0
        )
        db.session.add(riwayat)
        db.session.commit()

        return render_template(
            "order_success.html",
            bahan=bahan,
            jumlah=jumlah,
            total=total_cost
        )

    return render_template("order.html", bahans=bahans)

@app.route("/update_stok/<string:idCabang>", methods=["POST", "GET"])
def update_stok(idCabang):
    cabang = Cabang.query.get_or_404(idCabang)
    stok_list = Stock.query.filter_by(idCabang=idCabang).all()
    bahans = Bahan.query.all()

    if request.method == "POST":
        idBahan = request.form["idBahan"]
        jumlah_update = int(request.form["jumlah"])
        tipe = request.form["tipe"]  # "keluar" only (since branch loses item)

        stok = Stock.query.filter_by(idCabang=idCabang, idBahan=idBahan).first()
        if not stok:
            return "Error: stok bahan tidak ditemukan."

        if tipe == "keluar":
            if stok.jmlhBahan < jumlah_update:
                return "Error: stok tidak cukup untuk dikurangi."
            stok.jmlhBahan -= jumlah_update

            # 🔹 Record Riwayat (Keluar dari cabang)
            riwayat = Riwayat(
                idCabang=idCabang,
                idBahan=idBahan,
                tanggal=datetime.now(),
                jmlhMasuk=0,
                jmlhKeluar=jumlah_update
            )
            db.session.add(riwayat)
            db.session.commit()

            return redirect(url_for("stok"))

    return render_template("update_stok.html", cabang=cabang, stok_list=stok_list, bahans=bahans)

@app.route("/riwayat", methods=["GET"])
def riwayat():
    # You can filter or sort if you want, e.g. by latest first
    records = Riwayat.query.order_by(Riwayat.tanggal.desc()).all()
    cabangs = {c.id: c.namaCabang for c in Cabang.query.all()}
    bahans = {b.id: b.namaBahan for b in Bahan.query.all()}
    return render_template("riwayat.html", records=records, cabangs=cabangs, bahans=bahans)
    
if __name__ == "__main__":
    app.run(debug=True)