"""
Model Configuration API Routes
"""

from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

model_config_bp = Blueprint("model_config", __name__)

@model_config_bp.route('/models', methods=['GET'])
def get_models_config():
    """Get all available models configuration"""
    try:
        from flask import current_app
        models_config = current_app.config.get("PREDEFINED_MODELS", [])
        
        return jsonify({
            "success": True,
            "models": models_config
        })
        
    except Exception as e:
        logger.error(f"Failed to get models config: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
