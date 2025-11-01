from main import app, db, User

with app.app_context():
    db.create_all()

    new_user = User(username='Max', role='Owner')
    new_user.set_password('testpassword')
    db.session.add(new_user)
    db.session.commit()