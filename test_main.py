import unittest
from main import app, db, Bahan

class FlaskAppTests(unittest.TestCase):

    def setUp(self):
        # Setup isolated app context & database for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()

        with app.app_context():
            db.create_all()
            db.session.add(Bahan(id='BHN01', namaBahan='Gula', satuan='kg', hargaPerSatuan=15000))
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    # 🧩 Statement Coverage: ensures / route executes every line
    def test_home_page_loads(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Home', response.data)

    # 🧩 Branch Coverage: test both valid and invalid branches of /tambah_bahan
    def test_add_bahan_valid_and_invalid(self):
        # Valid input branch
        response = self.app.post('/tambah_bahan', data={
            'namaBahan': 'Tepung',
            'satuan': 'kg',
            'hargaPerSatuan': 12000
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Tepung', response.data)

        # Invalid input branch (missing hargaPerSatuan)
        response = self.app.post('/tambah_bahan', data={
            'namaBahan': 'Minyak',
            'satuan': 'liter'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 400)  # or whatever your app returns
        # This ensures the "else" branch in your route executes

    # 🧩 Path Coverage: test /hapus_bahan for both success and failure
    def test_delete_bahan(self):
        with app.app_context():
            bahan = Bahan.query.first()
            response = self.app.get(f'/hapus_bahan/{bahan.id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b'Gula', response.data)

        # Try deleting non-existent ID (alternate path)
        response = self.app.get('/hapus_bahan/BHN9999', follow_redirects=True)
        self.assertEqual(response.status_code, 404)

    # 🧩 Loop Testing: if you have loops iterating over bahan list
    def test_bahan_list_loop(self):
        with app.app_context():
            # Add multiple bahan to simulate multi-iteration loop
            for i in range(3):
                db.session.add(Bahan(id=f'BHN0{i+2}', namaBahan=f'Item{i}', satuan='kg', hargaPerSatuan=10000))
            db.session.commit()

        response = self.app.get('/bahan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Item0', response.data)
        self.assertIn(b'Item1', response.data)
        self.assertIn(b'Item2', response.data)

    # 🧩 Data Flow Testing: ensure DB values change after update
    def test_update_bahan(self):
        with app.app_context():
            bahan = Bahan.query.first()
            old_price = bahan.hargaPerSatuan

            response = self.app.post(f'/edit_bahan/{bahan.id}', data={
                'namaBahan': 'Gula Pasir',
                'satuan': 'kg',
                'hargaPerSatuan': old_price + 5000
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            updated = Bahan.query.filter_by(id=bahan.id).first()
            self.assertEqual(updated.hargaPerSatuan, old_price + 5000)
