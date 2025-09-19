"""
RNAmigos2 API Routes
Handles RNA-ligand interaction prediction requests
"""

from flask import Blueprint, request, jsonify, current_app
import os
import tempfile
import logging
from werkzeug.utils import secure_filename
import json

from app.utils.wrappers.rnamigos2_wrapper import RNAmigos2Wrapper
from app.utils.input import validate_rnamigos2_input

logger = logging.getLogger(__name__)

# Create blueprint
rnamigos2_bp = Blueprint("rnamigos2", __name__, url_prefix='/api/rnamigos2')

# Global wrapper instance
_rnamigos2_wrapper = None

def get_rnamigos2_wrapper():
    """Get or create RNAmigos2 wrapper instance"""
    global _rnamigos2_wrapper
    if _rnamigos2_wrapper is None:
        _rnamigos2_wrapper = RNAmigos2Wrapper()
    return _rnamigos2_wrapper

@rnamigos2_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get RNAmigos2 model information"""
    try:
        wrapper = get_rnamigos2_wrapper()
        info = wrapper.get_model_info()
        return jsonify({
            "success": True,
            "model_info": info
        })
    except Exception as e:
        logger.error(f"Failed to get RNAmigos2 model info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnamigos2_bp.route('/predict', methods=['POST'])
def predict_interactions():
    """Predict RNA-ligand interactions"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate input
        validation_result = validate_rnamigos2_input(data)
        if not validation_result["valid"]:
            return jsonify({
                "success": False,
                "error": validation_result["error"]
            }), 400
        
        # Extract parameters
        cif_content = data.get("cif_content", "")
        residue_list = data.get("residue_list", [])
        smiles_list = data.get("smiles_list", [])
        
        # Create temporary CIF file
        temp_dir = tempfile.mkdtemp()
        cif_path = os.path.join(temp_dir, "structure.cif")
        
        try:
            with open(cif_path, 'w') as f:
                f.write(cif_content)
            
            # Get wrapper and run prediction
            wrapper = get_rnamigos2_wrapper()
            result = wrapper.predict_interactions(
                cif_path=cif_path,
                residue_list=residue_list,
                smiles_list=smiles_list
            )
            
            if result["success"]:
                return jsonify({
                    "success": True,
                    "results": result["results"],
                    "model": "rnamigos2"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result["error"]
                }), 500
                
        finally:
            # Cleanup temporary files
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"RNAmigos2 prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Prediction failed: {str(e)}"
        }), 500

@rnamigos2_bp.route('/upload', methods=['POST'])
def upload_structure():
    """Upload mmCIF structure file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        if file and file.filename.lower().endswith(('.cif', '.mmcif')):
            # Read file content
            content = file.read().decode('utf-8')
            
            return jsonify({
                "success": True,
                "content": content,
                "filename": secure_filename(file.filename)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid file type. Please upload a .cif or .mmcif file"
            }), 400
            
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }), 500

@rnamigos2_bp.route('/validate', methods=['POST'])
def validate_input():
    """Validate input data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        validation_result = validate_rnamigos2_input(data)
        return jsonify(validation_result)
        
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Validation failed: {str(e)}"
        }), 500
