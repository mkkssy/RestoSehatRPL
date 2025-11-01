from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, ForeignKey
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import csv
from io import StringIO
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash,check_password_hash

app = Flask(__name__)
app.secret_key = 'a7f9b1c2d3e4_secure_key_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Stock.db'
db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    idPrefix = 'USR'
    id = db.Column(db.String(5), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='User')
    namaPanjang = db.Column(db.String(200), unique=True)
    email = db.Column(db.String(100), unique=True)
    noTelp = db.Column(db.String(12), unique=True)
    alamat = db.Column(db.String(150), unique=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirects to this view if user not logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # ✅ Store login info in session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['dropdownAkses']
        confirm = request.form['confirm']

        # basic validation
        if password != confirm:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        # create and save new user
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    return render_template("index.html", username=username)

@app.route("/stok", methods=['POST', 'GET'])
@login_required
def stok():
    selected_cabang = request.args.get("cabang")  

    if selected_cabang:
        stocks = Stock.query.filter_by(idCabang=selected_cabang).order_by(Stock.idCabang).all()
    else:
        stocks = Stock.query.order_by(Stock.idCabang).all()

    cabangs = Cabang.query.order_by(Cabang.id).all()  
    return render_template('stok.html', stocks=stocks, cabangs=cabangs, selected_cabang=selected_cabang)

@app.route("/tambah_bahan", methods=['POST', 'GET'])
@login_required
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
@login_required
def bahan():
    items = Bahan.query.order_by(Bahan.id).all()
    return render_template('bahan.html', items=items)

@app.route("/tambah_cabang", methods=['POST', 'GET'])
@login_required
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
@login_required
def cabang():
    chains = Cabang.query.order_by(Cabang.id).all()
    return render_template('cabang.html', chains=chains)

@app.route("/karyawan")
@login_required
def karyawan():
    employees = User.query.order_by(User.id).all()
    return render_template('karyawan.html', employees=employees)

@app.route("/delete_bahan/<string:id>")
@login_required
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
@login_required
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
@login_required
def pengiriman():
    pusat_cabang_id = "CBG0001"
    bahans = Bahan.query.order_by(Bahan.id).all()
    cabangs = Cabang.query.filter(Cabang.id != pusat_cabang_id).all()

    if request.method == "POST":
        selected_bahan_id = request.form["dropdownBahan"]
        selected_cabang_id = request.form["dropdownCabang"]
        jumlah = int(request.form["jmlhBahan"])

        bahan = Bahan.query.filter_by(id=selected_bahan_id).first()
        if not bahan:
            return "Error: bahan not found."

        pusat_stock = Stock.query.filter_by(idCabang=pusat_cabang_id, idBahan=selected_bahan_id).first()
        target_stock = Stock.query.filter_by(idCabang=selected_cabang_id, idBahan=selected_bahan_id).first()

        if not pusat_stock or pusat_stock.jmlhBahan < jumlah:
            return "Error: Stok pusat tidak cukup."

        pusat_stock.jmlhBahan -= jumlah

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
@login_required
def order():
    bahans = Bahan.query.order_by(Bahan.id).all()
    pusat_cabang_id = "CBG0001" 

    if request.method == "POST":
        selected_bahan_id = request.form["dropdownBahan"]
        jumlah = int(request.form["jmlhBahan"])

        for s in Stock.query.filter_by(idCabang='CBG0001').all():
            print(s.id, s.idBahan, repr(s.idBahan))
            print(f"'{selected_bahan_id}'")

        bahan = Bahan.query.filter_by(id=selected_bahan_id).first()
        if not bahan:
            return "Error: bahan not found"

        total_cost = bahan.hargaPerSatuan * jumlah

        stock_entry = Stock.query.filter_by(idCabang=pusat_cabang_id, idBahan=selected_bahan_id).first()
        print("Queried stock entry:", stock_entry)
        print(f"'{bahan.id}'")

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
        
        print("Selected bahan id:", repr(selected_bahan_id))
        print("Existing stock entry:", stock_entry)

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
@login_required
def update_stok(idCabang):
    cabang = Cabang.query.get_or_404(idCabang)
    stok_list = Stock.query.filter_by(idCabang=idCabang).all()
    bahans = Bahan.query.all()

    if request.method == "POST":
        idBahan = request.form["idBahan"]
        jumlah_update = int(request.form["jumlah"])
        tipe = request.form["tipe"]  

        stok = Stock.query.filter_by(idCabang=idCabang, idBahan=idBahan).first()
        if not stok:
            return "Error: stok bahan tidak ditemukan."

        if tipe == "keluar":
            if stok.jmlhBahan < jumlah_update:
                return "Error: stok tidak cukup untuk dikurangi."
            stok.jmlhBahan -= jumlah_update

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

@app.route("/update_bahan/<string:id>", methods=['POST', 'GET'])
@login_required
def update_bahan(id):
    bahan = Bahan.query.get_or_404(id)
    if request.method == "POST":
        bahan.namaBahan = request.form["namaBahan"]
        bahan.satuan = request.form["satuan"]
        bahan.hargaPerSatuan = int(request.form["hargaPerSatuan"])
        db.session.commit()
        return redirect("/bahan")
    return render_template("update_bahan.html", bahan=bahan)

@app.route("/update_karyawan/<string:id>", methods=['POST', 'GET'])
@login_required
def update_karyawan(id):
    user = User.query.get_or_404(id)
    if request.method == "POST":
        # Capture submitted data
        new_username = request.form["username"]
        new_role = request.form["dropdownAkses"]

        # Check if another user already has the submitted username
        with db.session.no_autoflush:
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                flash('Username already exists!', 'danger')
                return redirect(url_for('update_karyawan', id=id))

        # Update the user object after check
        user.username = new_username
        user.role = new_role
        
        try:
            db.session.commit()
            flash('User successfully updated!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A database error occurred. Please try again.', 'danger')

        return redirect("/karyawan")
    
    return render_template("update_karyawan.html", user=user)

@app.route("/change_password/<string:id>", methods=['POST', 'GET'])
@login_required
def change_password(id):
    user = User.query.get_or_404(id)
    if request.method == "POST":
        # Capture submitted data
        new_password = request.form["password"]
        confirm = request.form["confirm"]

        # basic validation
        if new_password != confirm:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('change_password', id=id))
        
        if check_password_hash(user.password_hash, new_password):
            flash('New password cannot be the same as the old password!', 'danger')
            return redirect(url_for('change_password', id=id))
        
        user.password = generate_password_hash(new_password)

        try:
            db.session.commit()
            flash('Password successfully updated!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A database error occurred. Please try again.', 'danger')

        return redirect("/home")
    
    return render_template("change_password.html", user=user)

@app.route("/update_cabang/<string:id>", methods=['POST', 'GET'])
@login_required
def update_cabang(id):
    cabang = Cabang.query.get_or_404(id)
    if request.method == "POST":
        cabang.namaCabang = request.form["namaCabang"]
        db.session.commit()
        return redirect("/cabang")
    return render_template("update_cabang.html", cabang=cabang)

@app.route("/riwayatstok", methods=["GET"])
@login_required
def riwayat():
    records = Riwayat.query.order_by(Riwayat.tanggal.desc()).all()
    cabangs = {c.id: c.namaCabang for c in Cabang.query.all()}
    bahans = {b.id: b.namaBahan for b in Bahan.query.all()}
    return render_template("riwayatstok.html", records=records, cabangs=cabangs, bahans=bahans)

@app.route("/riwayat/export_csv")
@login_required
def export_riwayat_csv():
    records = Riwayat.query.order_by(Riwayat.tanggal.desc()).all()
    cabangs = {c.id: c.namaCabang for c in Cabang.query.all()}
    bahans = {b.id: b.namaBahan for b in Bahan.query.all()}

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow(["Tanggal", "Cabang", "Bahan", "Masuk", "Keluar"])

    for r in records:
        writer.writerow([
            r.tanggal.strftime('%Y-%m-%d %H:%M:%S'),
            cabangs.get(r.idCabang, 'Unknown'),
            bahans.get(r.idBahan, 'Unknown'),
            r.jmlhMasuk,
            r.jmlhKeluar
        ])

    output = si.getvalue()
    response = Response(output, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=riwayat.csv"
    return response

if __name__ == "__main__":
    app.run(debug=True)