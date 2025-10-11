from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, ForeignKey
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Stock.db'
db = SQLAlchemy(app)

class Stock(db.Model):
    idPrefix = 'STK'
    id = db.Column(db.String(5), primary_key=True)
    idCabang = db.Column(db.String(5), ForeignKey('cabang.id', ondelete='CASCADE'), nullable=False,)
    idBahan = db.Column(db.String(5), ForeignKey('bahan.id', ondelete='CASCADE'), nullable=False)
    namaBahan = db.Column(db.String(200), nullable=False)
    jmlhBahan = db.Column(db.Integer, nullable=False)

class Bahan(db.Model):
    idPrefix = 'BHN'
    id = db.Column(db.String(5), primary_key=True)
    namaBahan = db.Column(db.String(25), nullable=False)
    satuan = db.Column(db.String(8), nullable=False)
    hargaPerSatuan = db.Column(db.Integer, nullable=False)
    stocks = db.relationship('Stock', backref='bahan', lazy=True, cascade="all, delete-orphan")

    def __repr__ (self):
        return '<Bahan %r>' % self.idBahan
    
class Cabang(db.Model):
    idPrefix = 'CBG'
    id = db.Column(db.String(5), primary_key=True)
    namaCabang = db.Column(db.String(25), nullable=False)
    stocks = db.relationship('Stock', backref='cabang', lazy=True, cascade="all, delete-orphan")

    def __repr__ (self):
        return '<Cabang %r>' % self.idCabang
    
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
    if request.method == "POST":
        selected_bahan = request.form["dropdownBahan"]
        selected_cabang = request.form["dropdownCabang"]
        jumlah = int(request.form["jmlhBahan"])

        stock_entry = Stock.query.filter_by(idCabang=selected_cabang, idBahan=selected_bahan).first()

        if stock_entry:
            stock_entry.jmlhBahan += jumlah
        else:
            bahan = Bahan.query.filter_by(id=selected_bahan).first()
            if not bahan:
                return "Error: bahan not found."

            new_stock = Stock(
                idCabang=selected_cabang,
                idBahan=selected_bahan,
                namaBahan=bahan.namaBahan,
                jmlhBahan=jumlah
            )
            db.session.add(new_stock)

        db.session.commit()
        return redirect("/stok")
    stocks = Stock.query.order_by(Stock.id).all()
    dropdownCabang = {stock.idCabang for stock in stocks}
    dropdownBahan = {stock.idBahan for stock in stocks}
    return render_template('pengiriman.html', stocks = stocks, cabangs = dropdownCabang, bahans = dropdownBahan)

@app.route("/order", methods=['POST', 'GET'])
def order():
    if request.method == 'POST':
        
    return render_template('order.html')
    
if __name__ == "__main__":
    app.run(debug=True)