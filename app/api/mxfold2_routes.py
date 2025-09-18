"""
MXFold2 API Routes
"""

from flask import Blueprint, request, jsonify, send_file
import tempfile
import logging
from app.utils.wrappers.mxfold2_wrapper import MXFold2Wrapper
from app.utils.input import validate_rna_sequence

logger = logging.getLogger(__name__)

mxfold2_bp = Blueprint("mxfold2", __name__)

# Global wrapper instance
_mxfold2_wrapper = None

def get_mxfold2_wrapper():
    """Get or create MXFold2 wrapper instance"""
    global _mxfold2_wrapper
    if _mxfold2_wrapper is None:
        _mxfold2_wrapper = MXFold2Wrapper()
    return _mxfold2_wrapper

@mxfold2_bp.route('/predict', methods=['POST'])
def predict_sequences():
    """Predict RNA secondary structures from sequences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        sequences = data.get('sequences', [])
        if not sequences:
            return jsonify({
                "success": False,
                "error": "No sequences provided"
            }), 400
        
        # Validate sequences
        validated_sequences = []
        for i, seq in enumerate(sequences):
            try:
                if validate_rna_sequence(seq):
                    validated_sequences.append(seq)
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Invalid sequence at index {i}: contains non-RNA characters"
                    }), 400
            except Exception as e:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid sequence at index {i}: {str(e)}"
                }), 400
        
        if not validated_sequences:
            return jsonify({
                "success": False,
                "error": "No valid RNA sequences provided"
            }), 400
        
        # Run prediction
        wrapper = get_mxfold2_wrapper()
        result = wrapper.predict(validated_sequences)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "results": result["results"],
                "model": "MXFold2",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"MXFold2 prediction error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/predict/file', methods=['POST'])
def predict_file():
    """Predict RNA secondary structures from uploaded file"""
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
        
        # Read and parse file content
        content = file.read().decode('utf-8')
        
        # Parse FASTA format
        sequences = []
        current_sequence = ""
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('>'):
                if current_sequence:
                    sequences.append(current_sequence)
                    current_sequence = ""
            elif line and not line.startswith('>'):
                current_sequence += line
        
        if current_sequence:
            sequences.append(current_sequence)
        
        if not sequences:
            return jsonify({
                "success": False,
                "error": "No sequences found in file"
            }), 400
        
        # Validate sequences
        validated_sequences = []
        for i, seq in enumerate(sequences):
            try:
                if validate_rna_sequence(seq):
                    validated_sequences.append(seq)
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Invalid sequence at index {i}: contains non-RNA characters"
                    }), 400
            except Exception as e:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid sequence at index {i}: {str(e)}"
                }), 400
        
        if not validated_sequences:
            return jsonify({
                "success": False,
                "error": "No valid RNA sequences provided"
            }), 400
        
        # Run prediction
        wrapper = get_mxfold2_wrapper()
        result = wrapper.predict(validated_sequences)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "results": result["results"],
                "model": "MXFold2",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"MXFold2 file prediction error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/download/<format>', methods=['POST'])
def download_results(format):
    """Download prediction results in specified format"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({
                "success": False,
                "error": "No results provided"
            }), 400
        
        results = data['results']
        output_format = data.get('format', 'ct')
        
        # Create temporary file with results
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{output_format}', delete=False) as temp_file:
            if output_format == 'ct':
                for i, result in enumerate(results):
                    temp_file.write(f">sequence_{i+1}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n')
            else:
                # Default to dot-bracket format
                for i, result in enumerate(results):
                    temp_file.write(f">sequence_{i+1}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n')
            
            temp_file_path = temp_file.name
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f'mxfold2_results.{output_format}',
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Failed to download results: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/status', methods=['GET'])
def get_status():
    """Get MXFold2 service status"""
    try:
        wrapper = get_mxfold2_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "available",
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get MXFold2 status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
