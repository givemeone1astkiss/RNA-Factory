"""
CoPRA API Routes
Protein-RNA Binding Affinity Prediction
"""

from flask import Blueprint, request, jsonify
import logging
import os
import sys
import json
import tempfile
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

copra_bp = Blueprint("copra", __name__)

@copra_bp.route('/predict', methods=['POST'])
def predict_binding_affinity():
    """Predict protein-RNA binding affinity using CoPRA"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No input data provided"
            }), 400
        
        # Extract input parameters
        protein_sequence = data.get('protein_sequence', '').strip()
        rna_sequence = data.get('rna_sequence', '').strip()
        
        if not protein_sequence or not rna_sequence:
            return jsonify({
                "success": False,
                "error": "Both protein_sequence and rna_sequence are required"
            }), 400
        
        # Validate sequences
        if not is_valid_protein_sequence(protein_sequence):
            return jsonify({
                "success": False,
                "error": "Invalid protein sequence. Only standard amino acid codes are allowed."
            }), 400
        
        if not is_valid_rna_sequence(rna_sequence):
            return jsonify({
                "success": False,
                "error": "Invalid RNA sequence. Only A, U, G, C are allowed."
            }), 400
        
        # Import CoPRA inference
        try:
            from models.CoPRA.copra_inference import CoPRAInference
        except ImportError as e:
            logger.error(f"Failed to import CoPRA inference: {e}")
            return jsonify({
                "success": False,
                "error": "CoPRA model not available"
            }), 500
        
        # Initialize CoPRA
        try:
            copra = CoPRAInference()
        except Exception as e:
            logger.error(f"Failed to initialize CoPRA: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to initialize CoPRA model: {str(e)}"
            }), 500
        
        # Check dependencies
        deps = copra.check_dependencies()
        if not deps.get("available", False):
            return jsonify({
                "success": False,
                "error": f"CoPRA dependencies not available: {deps.get('error', 'Unknown error')}"
            }), 500
        
        # Run prediction
        try:
            result = copra.predict_binding_affinity(
                protein_sequence=protein_sequence,
                rna_sequence=rna_sequence
            )
            
            if result.get("success", False):
                return jsonify({
                    "success": True,
                    "model": "CoPRA",
                    "prediction": {
                        "binding_affinity": result.get("binding_affinity"),
                        "confidence": result.get("confidence"),
                        "unit": "kcal/mol"
                    },
                    "input": {
                        "protein_sequence": protein_sequence,
                        "rna_sequence": rna_sequence
                    },
                    "metadata": {
                        "method": result.get("method", "CoPRA"),
                        "raw_output": result.get("raw_output", "")
                    }
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Prediction failed"),
                    "details": result.get("raw_error", "")
                }), 500
                
        except Exception as e:
            logger.error(f"CoPRA prediction failed: {e}")
            return jsonify({
                "success": False,
                "error": f"Prediction failed: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"CoPRA API error: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@copra_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get CoPRA model information"""
    try:
        from models.CoPRA.copra_inference import CoPRAInference
        
        copra = CoPRAInference()
        info = copra.get_model_info()
        
        return jsonify({
            "success": True,
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get CoPRA info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@copra_bp.route('/status', methods=['GET'])
def get_model_status():
    """Get CoPRA model status and dependencies"""
    try:
        from models.CoPRA.copra_inference import CoPRAInference
        
        copra = CoPRAInference()
        status = copra.check_dependencies()
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get CoPRA status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def is_valid_protein_sequence(sequence):
    """Validate protein sequence"""
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    return all(aa.upper() in valid_aa for aa in sequence)

def is_valid_rna_sequence(sequence):
    """Validate RNA sequence"""
    valid_bases = set('AUCG')
    return all(base.upper() in valid_bases for base in sequence)
