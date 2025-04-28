from app import create_app, db
from flask_jwt_extended import JWTManager

app = create_app()
jwt = JWTManager(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True, port=5000)
run.py

# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     app.run()
