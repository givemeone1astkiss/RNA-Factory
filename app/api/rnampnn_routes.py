"""
RNAMPNN API Routes
API endpoints for RNAMPNN RNA sequence prediction from 3D structure
"""

import logging
from flask import Blueprint, request, jsonify, send_file
import tempfile
import os
from pathlib import Path

from app.utils.wrappers import RNAMPNNWrapper

logger = logging.getLogger(__name__)

# Create blueprint
rnampnn_bp = Blueprint('rnampnn', __name__, url_prefix='/api/rnampnn')

# Global RNAMPNN wrapper instance
rnampnn_wrapper = None

def get_rnampnn_wrapper():
    """Get or initialize RNAMPNN wrapper"""
    global rnampnn_wrapper
    if rnampnn_wrapper is None:
        rnampnn_wrapper = RNAMPNNWrapper()
    return rnampnn_wrapper

@rnampnn_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get RNAMPNN model information"""
    try:
        wrapper = get_rnampnn_wrapper()
        info = wrapper.get_model_info()
        return jsonify({
            "success": True,
            "model_info": info
        })
    except Exception as e:
        logger.error(f"Failed to get RNAMPNN model info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnampnn_bp.route('/predict', methods=['POST'])
def predict_sequence():
    """Predict RNA sequence from PDB file"""
    try:
        # Check if file is uploaded
        if 'pdb_file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file uploaded"
            }), 400
        
        file = request.files['pdb_file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        if not file.filename.lower().endswith('.pdb'):
            return jsonify({
                "success": False,
                "error": "File must be a PDB file (.pdb extension)"
            }), 400
        
        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        try:
            # Get wrapper and validate file
            wrapper = get_rnampnn_wrapper()
            
            # Validate PDB file
            validation_result = wrapper.validate_pdb_file(temp_file_path)
            if not validation_result.get("valid", False):
                return jsonify({
                    "success": False,
                    "error": validation_result.get("error", "Invalid PDB file")
                }), 400
            
            # Perform prediction
            result = wrapper.predict_sequence(temp_file_path)
            
            if result.get("success", False):
                return jsonify({
                    "success": True,
                    "prediction": {
                        "predicted_sequence": result["predicted_sequence"],
                        "confidence_scores": result["confidence_scores"],
                        "sequence_length": result["sequence_length"],
                        "input_file": result["input_file"],
                        "model_info": result["model_info"]
                    },
                    "validation": validation_result
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Prediction failed")
                }), 500
                
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except:
                pass
        
    except Exception as e:
        logger.error(f"RNAMPNN prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnampnn_bp.route('/validate', methods=['POST'])
def validate_pdb():
    """Validate PDB file for RNAMPNN processing"""
    try:
        # Check if file is uploaded
        if 'pdb_file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file uploaded"
            }), 400
        
        file = request.files['pdb_file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        if not file.filename.lower().endswith('.pdb'):
            return jsonify({
                "success": False,
                "error": "File must be a PDB file (.pdb extension)"
            }), 400
        
        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        try:
            # Get wrapper and validate file
            wrapper = get_rnampnn_wrapper()
            validation_result = wrapper.validate_pdb_file(temp_file_path)
            
            return jsonify({
                "success": True,
                "validation": validation_result
            })
            
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except:
                pass
        
    except Exception as e:
        logger.error(f"PDB validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnampnn_bp.route('/predict/coordinates', methods=['POST'])
def predict_from_coordinates():
    """Predict RNA sequence from coordinate array"""
    try:
        data = request.get_json()
        
        if not data or 'coordinates' not in data:
            return jsonify({
                "success": False,
                "error": "No coordinates provided"
            }), 400
        
        coordinates = data['coordinates']
        
        # Validate coordinates format
        if not isinstance(coordinates, list):
            return jsonify({
                "success": False,
                "error": "Coordinates must be a list"
            }), 400
        
        try:
            import numpy as np
            coords_array = np.array(coordinates, dtype=np.float32)
            
            # Check dimensions
            if coords_array.ndim != 3:
                return jsonify({
                    "success": False,
                    "error": "Coordinates must be 3D array (seq_len, num_atoms, 3)"
                }), 400
            
            if coords_array.shape[2] != 3:
                return jsonify({
                    "success": False,
                    "error": "Coordinates must have 3 dimensions (x, y, z)"
                }), 400
            
            # Get wrapper and perform prediction
            wrapper = get_rnampnn_wrapper()
            result = wrapper.predict_sequence_from_coords(coords_array)
            
            if result.get("success", False):
                return jsonify({
                    "success": True,
                    "prediction": {
                        "predicted_sequence": result["predicted_sequence"],
                        "confidence_scores": result["confidence_scores"],
                        "sequence_length": result["sequence_length"],
                        "model_info": result["model_info"]
                    }
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Prediction failed")
                }), 500
                
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid coordinates format: {str(e)}"
            }), 400
        
    except Exception as e:
        logger.error(f"Coordinate prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnampnn_bp.route('/status', methods=['GET'])
def get_status():
    """Get RNAMPNN service status"""
    try:
        wrapper = get_rnampnn_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "ready" if info.get("model_loaded", False) else "not_loaded",
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get RNAMPNN status: {e}")
        return jsonify({
            "success": False,
            "status": "error",
            "error": str(e)
        }), 500
