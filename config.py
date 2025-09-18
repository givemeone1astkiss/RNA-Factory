import os
from pathlib import Path


class Config:
    """Application Configuration Class"""

    # Base paths
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
    MODEL_FOLDER = BASE_DIR / "models"


class DevelopmentConfig(Config):
    """Development Environment Configuration"""
    DEBUG = False
    TESTING = False


class ProductionConfig(Config):
    """Production Environment Configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing Environment Configuration"""
    TESTING = False
    DEBUG = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
