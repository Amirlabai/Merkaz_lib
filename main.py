import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from waitress import serve
from datetime import datetime, timedelta

import config
from utils import create_file_with_header
from mailer import mail

# Import and register blueprints
from routes.auth import auth_bp
from routes.files import files_bp
from routes.uploads import uploads_bp
from routes.admin import admin_bp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = config.SUPER_SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

    # --- Logging Configuration ---
    if not app.debug:
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_file = 'server.log'
        # Rotate logs after 5MB, keep 2 backup files
        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=2)
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        
        # Configure Werkzeug's logger (for HTTP requests)
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.INFO)
        werkzeug_logger.addHandler(file_handler)
        
        # Configure the app's logger
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Merkaz_lib application starting up...')


    # --- Mail Configuration ---
    app.config['MAIL_SERVER'] = config.MAIL_SERVER
    app.config['MAIL_PORT'] = config.MAIL_PORT
    app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
    app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = config.MAIL_USE_SSL
    mail.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == "__main__":
    # --- Directory and File Initialization ---
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.SHARE_FOLDER)
    trash_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.TRASH_FOLDER)
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.UPLOAD_FOLDER)

    if not os.path.exists(share_dir): os.makedirs(share_dir)
    if not os.path.exists(trash_dir): os.makedirs(trash_dir)
    if not os.path.exists(upload_dir): os.makedirs(upload_dir)

    # Create necessary CSV files with headers if they don't exist
    create_file_with_header(config.AUTH_USER_DATABASE, ["email", "password", "role", "status"])
    create_file_with_header(config.NEW_USER_DATABASE, ["email", "password", "role"])
    create_file_with_header(config.DENIED_USER_DATABASE, ["email", "password", "role"])
    create_file_with_header(config.PASSWORD_RESET_DATABASE, ["email", "token", "timestamp"])
    create_file_with_header(config.SESSION_LOG_FILE, ["timestamp", "email", "event"])
    create_file_with_header(config.DOWNLOAD_LOG_FILE, ["timestamp", "email", "type", "path"])
    create_file_with_header(config.SUGGESTION_LOG_FILE, ["timestamp", "email", "suggestion"])
    create_file_with_header(config.UPLOAD_LOG_FILE, ["timestamp", "email", "filename", "path"])
    create_file_with_header(config.DECLINED_UPLOAD_LOG_FILE, ["timestamp", "email", "filename"])

    app = create_app()

    app.logger.info("Starting server with Waitress on host 0.0.0.0, port 8000...")
    serve(app, host="0.0.0.0", port=8000)