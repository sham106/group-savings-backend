# from flask import Flask, request
# from flask_sqlalchemy import SQLAlchemy
# from flask_bcrypt import Bcrypt
# from flask_jwt_extended import JWTManager
# from flask_migrate import Migrate
# from flask_cors import CORS
# from dotenv import load_dotenv
# import os

# # Load environment variables
# load_dotenv()

# # Initialize extensions
# db = SQLAlchemy()
# bcrypt = Bcrypt()
# jwt = JWTManager()
# migrate = Migrate()

# def create_app():
#     app = Flask(__name__)
    
#     # Configuration
#     app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
#     app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#     app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#     app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
#     app.config['TINYPESA_API_KEY'] = os.getenv('TINYPESA_API_KEY')  # Add this line



    
#     # Enable CORS
#     CORS(app, origins=["http://localhost:5173"], 
#          methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
#          allow_headers=["Content-Type", "Authorization"],
#          supports_credentials=True)
    
#     # Handle preflight requests
#     @app.before_request
#     def handle_preflight():
#         if request.method == "OPTIONS":
#             response = app.make_response("")
#             response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
#             response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
#             response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
#             response.headers["Access-Control-Allow-Credentials"] = "true"
#             return response

#     # Initialize extensions
#     db.init_app(app)
#     bcrypt.init_app(app)
#     jwt.init_app(app)
#     migrate.init_app(app, db)
    
#     # Import and register blueprints
#     from .routes.auth_routes import auth_bp
#     from .routes.group_routes import group_bp
#     from .routes.transaction_routes import transaction_bp
#     from .routes.withdrawal_routes import withdrawal_bp
#     from .routes.payment_routes import payment_routes
#     from .routes.notification_routes import notification_bp  # New import
#     from .routes.userSearch_route import user_bp


#     app.register_blueprint(auth_bp, url_prefix='/api/auth')
#     app.register_blueprint(group_bp, url_prefix='/api/groups')
#     app.register_blueprint(transaction_bp, url_prefix='/api/transactions')
#     app.register_blueprint(withdrawal_bp, url_prefix='/api/withdrawals')
#     app.register_blueprint(payment_routes)
#     app.register_blueprint(notification_bp, url_prefix='/api/notifications')# New registration
#     app.register_blueprint(user_bp, url_prefix='/api/users')


#     return app

# app/__init__.py

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # App configuration from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['TINYPESA_API_KEY'] = os.getenv('TINYPESA_API_KEY')
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Enable CORS with frontend URL from env
    CORS(app, origins=[os.getenv("FRONTEND_URL")],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_response("")
            response.headers["Access-Control-Allow-Origin"] = os.getenv("FRONTEND_URL")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

    # Register Blueprints
    from .routes.auth_routes import auth_bp
    from .routes.group_routes import group_bp
    from .routes.transaction_routes import transaction_bp
    from .routes.withdrawal_routes import withdrawal_bp
    from .routes.payment_routes import payment_routes
    from .routes.notification_routes import notification_bp
    from .routes.userSearch_route import user_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(group_bp, url_prefix='/api/groups')
    app.register_blueprint(transaction_bp, url_prefix='/api/transactions')
    app.register_blueprint(withdrawal_bp, url_prefix='/api/withdrawals')
    app.register_blueprint(payment_routes)  # assuming already prefixed inside file
    app.register_blueprint(notification_bp, url_prefix='/api/notifications')
    app.register_blueprint(user_bp, url_prefix='/api/users')

    # Health check route
    @app.route("/")
    def health_check():
        return "Backend is live!"

    return app
