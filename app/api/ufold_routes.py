"""
UFold API Routes
Fast and Accurate RNA Secondary Structure Prediction with Deep Learning
"""

from flask import Blueprint, request, jsonify, send_file
import tempfile
import os
import logging
from pathlib import Path

from app.utils.wrappers import UFoldWrapper
from app.utils.input import validate_rna_sequence, parse_fasta_file

logger = logging.getLogger(__name__)

# Create blueprint
ufold_bp = Blueprint('ufold', __name__, url_prefix='/api/ufold')

# UFold wrapper instance
ufold_wrapper = None

def get_ufold_wrapper():
    """Get or create UFold wrapper instance"""
    global ufold_wrapper
    if ufold_wrapper is None:
        ufold_wrapper = UFoldWrapper()
    return ufold_wrapper

@ufold_bp.route('/status', methods=['GET'])
def get_status():
    """Get UFold model status"""
    try:
        wrapper = get_ufold_wrapper()
        model_info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "model_info": model_info,
            "status": "ready" if model_info["available"] else "not_available"
        })
    except Exception as e:
        logger.error(f"Failed to get UFold status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@ufold_bp.route('/predict', methods=['POST'])
def predict_sequences():
    """Predict RNA secondary structures from sequences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        sequences = data.get('sequences', [])
        predict_nc = data.get('predict_nc', False)
        
        if not sequences:
            return jsonify({"success": False, "error": "No sequences provided"}), 400
        
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
        
        # Get wrapper and predict
        wrapper = get_ufold_wrapper()
        result = wrapper.predict(validated_sequences, predict_nc)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"UFold prediction failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@ufold_bp.route('/predict/file', methods=['POST'])
def predict_from_file():
    """Predict RNA secondary structures from uploaded file"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Get additional parameters
        predict_nc = request.form.get('predict_nc', 'false').lower() == 'true'
        
        # Parse file
        try:
            sequences = parse_fasta_file(file)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        
        if not sequences:
            return jsonify({"success": False, "error": "No valid sequences found in file"}), 400
        
        # Get wrapper and predict
        wrapper = get_ufold_wrapper()
        result = wrapper.predict(sequences, predict_nc)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"UFold file prediction failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@ufold_bp.route('/download/<format>', methods=['POST'])
def download_results(format):
    """Download prediction results in specified format"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({"success": False, "error": "No results provided"}), 400
        
        results = data['results']
        if not results:
            return jsonify({"success": False, "error": "No results to download"}), 400
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False) as tmp_file:
            if format == 'ct':
                _write_ct_format(tmp_file, results)
            elif format == 'bpseq':
                _write_bpseq_format(tmp_file, results)
            elif format == 'fasta':
                _write_fasta_format(tmp_file, results)
            else:
                return jsonify({"success": False, "error": f"Unsupported format: {format}"}), 400
            
            tmp_file.flush()
            
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=f'ufold_results.{format}',
                mimetype='text/plain'
            )
            
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def _write_ct_format(file, results):
    """Write results in CT format"""
    for i, result in enumerate(results):
        file.write(f"{len(result['sequence'])} sequence_{i+1}\n")
        # CT format: position, base, prev, next, pair, position
        for j, base in enumerate(result['sequence']):
            pair = 0  # Default no pair
            if 'ct_data' in result:
                # Parse CT data to find pairs
                lines = result['ct_data'].strip().split('\n')
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 6 and int(parts[0]) == j + 1:
                        pair = int(parts[4])
                        break
            
            file.write(f"{j+1} {base} {j} {j+2} {pair} {j+1}\n")

def _write_bpseq_format(file, results):
    """Write results in BPSEQ format"""
    for i, result in enumerate(results):
        file.write(f"# BPSEQ format for sequence_{i+1}\n")
        # BPSEQ format: position, base, pair
        for j, base in enumerate(result['sequence']):
            pair = 0  # Default no pair
            if 'bpseq_data' in result:
                # Parse BPSEQ data to find pairs
                lines = result['bpseq_data'].strip().split('\n')
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 3 and int(parts[0]) == j + 1:
                        pair = int(parts[2])
                        break
            
            file.write(f"{j+1} {base} {pair}\n")

def _write_fasta_format(file, results):
    """Write results in FASTA format"""
    for i, result in enumerate(results):
        file.write(f">sequence_{i+1}\n")
        file.write(f"{result['sequence']}\n")
