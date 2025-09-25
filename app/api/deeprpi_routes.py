from flask import Blueprint, request, jsonify, current_app
import os
import tempfile
from app.utils.wrappers.deeprpi_wrapper import DeepRPIWrapper

# Create blueprint
deeprpi_bp = Blueprint('deeprpi', __name__)

@deeprpi_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get DeepRPI model information"""
    try:
        wrapper = DeepRPIWrapper()
        info = wrapper.get_model_info()
        return jsonify({
            "success": True,
            "model_info": info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@deeprpi_bp.route('/predict', methods=['POST'])
def predict_interaction():
    """Predict RNA-protein interaction"""
    try:
        # Get input data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No input data provided"
            }), 400
        
        protein_sequence = data.get('protein_sequence', '').strip()
        rna_sequence = data.get('rna_sequence', '').strip()
        plot_attention = data.get('plot_attention', True)
        
        if not protein_sequence or not rna_sequence:
            return jsonify({
                "success": False,
                "error": "Both protein_sequence and rna_sequence are required"
            }), 400
        
        # Initialize wrapper
        wrapper = DeepRPIWrapper()
        
        # Validate sequences
        validation = wrapper.validate_sequences(protein_sequence, rna_sequence)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": "; ".join(validation['errors']),
                "warnings": validation['warnings']
            }), 400
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Predict interaction
            result = wrapper.predict_interaction(
                protein_sequence=protein_sequence,
                rna_sequence=rna_sequence,
                plot_attention=plot_attention,
                output_dir=temp_dir
            )
            
            if result.get('success'):
                # Clean up attention matrices for response (they're too large for JSON)
                if 'protein_attention' in result:
                    del result['protein_attention']
                if 'rna_attention' in result:
                    del result['rna_attention']
                
                return jsonify(result)
            else:
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'Prediction failed')
                }), 500
                
    except Exception as e:
        current_app.logger.error(f"DeepRPI prediction error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@deeprpi_bp.route('/validate', methods=['POST'])
def validate_sequences():
    """Validate input sequences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No input data provided"
            }), 400
        
        protein_sequence = data.get('protein_sequence', '').strip()
        rna_sequence = data.get('rna_sequence', '').strip()
        
        # Initialize wrapper
        wrapper = DeepRPIWrapper()
        
        # Validate sequences
        validation = wrapper.validate_sequences(protein_sequence, rna_sequence)
        
        return jsonify({
            "success": True,
            "validation": validation
        })
        
    except Exception as e:
        current_app.logger.error(f"DeepRPI validation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Validation error: {str(e)}"
        }), 500

@deeprpi_bp.route('/status', methods=['GET'])
def get_status():
    """Get DeepRPI model status"""
    try:
        wrapper = DeepRPIWrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "ready",
            "model_info": info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "error",
            "error": str(e)
        }), 500
