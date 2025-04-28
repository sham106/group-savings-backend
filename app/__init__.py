from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # App configuration
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY'),
        'TINYPESA_API_KEY': os.getenv('TINYPESA_API_KEY')
    })
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS
    allowed_origins = [
        os.getenv("FRONTEND_URL").rstrip('/'),  # Remove trailing slash
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]
    
    CORS(app,
         origins=allowed_origins,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    # Dynamic preflight handler
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')
            if origin and any(origin.rstrip('/') == allowed.rstrip('/') for allowed in allowed_origins):
                response = app.make_response("")
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
    
    # Initialize scheduler
    # if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    #     with app.app_context():
    #         from app.schedulers.loan_scheduler import init_loan_scheduler
    #         init_loan_scheduler(app)
            
    # Register blueprints
    from .routes import auth_routes, group_routes, transaction_routes, withdrawal_routes
    from .routes import payment_routes, notification_routes, userSearch_route, loan_routes

    app.register_blueprint(auth_routes.auth_bp, url_prefix='/api/auth')
    app.register_blueprint(group_routes.group_bp, url_prefix='/api/groups')  # Ensure this matches the group routes
    app.register_blueprint(transaction_routes.transaction_bp, url_prefix='/api/transactions')
    app.register_blueprint(withdrawal_routes.withdrawal_bp, url_prefix='/api/withdrawals')
    app.register_blueprint(payment_routes.payment_routes, url_prefix='/api/payments')  # Add missing prefix if needed
    app.register_blueprint(notification_routes.notification_bp, url_prefix='/api/notifications')
    app.register_blueprint(userSearch_route.user_bp, url_prefix='/api/users')
    app.register_blueprint(loan_routes.loan_bp, url_prefix='/api/loans')  # Ensure loan routes are registered correctly

    @app.route("/")
    def health_check():
        return "Backend is live!"

    return app