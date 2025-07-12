from flask import Flask
from flask import Flask
from app.extensions import init_extensions
from app.routes import register_blueprints

def create_app():
    app = Flask(__name__)
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app