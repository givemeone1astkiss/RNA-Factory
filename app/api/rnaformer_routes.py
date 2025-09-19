"""
RNAformer API Routes
Handles RNA secondary structure prediction requests
"""

from flask import Blueprint, request, jsonify, current_app, send_file, send_from_directory
import os
import tempfile
import logging
from werkzeug.utils import secure_filename
import json

from app.utils.wrappers.rnaformer_wrapper import RNAformerWrapper
from app.utils.input import validate_rna_sequence
from app.utils.output import generate_ct_content, generate_multiple_ct_files, create_ct_zip_file, cleanup_temp_files

logger = logging.getLogger(__name__)

# Create blueprint
rnaformer_bp = Blueprint("rnaformer", __name__, url_prefix='/api/rnaformer')

# Global wrapper instance
_rnaformer_wrapper = None

def get_rnaformer_wrapper():
    """Get or create RNAformer wrapper instance"""
    global _rnaformer_wrapper
    if _rnaformer_wrapper is None:
        _rnaformer_wrapper = RNAformerWrapper()
    return _rnaformer_wrapper

@rnaformer_bp.route('/predict', methods=['POST'])
def predict_structure():
    """Predict RNA secondary structure using RNAformer"""
    try:
        # Get input data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No input data provided"}), 400
        
        # Extract sequences
        sequences = []
        
        # Check for text input
        if 'sequences' in data and data['sequences']:
            sequences.extend(data['sequences'])
        
        # Check for file input
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # Read and parse file content
                content = file.read().decode('utf-8')
                file_sequences = parse_fasta_file(content)
                sequences.extend(file_sequences)
        
        if not sequences:
            return jsonify({"success": False, "error": "No sequences provided"}), 400
        
        # Validate sequences
        validated_sequences = []
        for seq in sequences:
            if validate_rna_sequence(seq):
                # Convert to uppercase and add to validated sequences
                validated_sequences.append(seq.upper())
        
        if not validated_sequences:
            return jsonify({"success": False, "error": "No valid RNA sequences found"}), 400
        
        # Get wrapper and predict
        wrapper = get_rnaformer_wrapper()
        result = wrapper.predict(validated_sequences)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"RNAformer prediction error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Prediction failed: {str(e)}"
        }), 500

@rnaformer_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        wrapper = get_rnaformer_wrapper()
        is_healthy = wrapper.test_model()
        
        return jsonify({
            "status": "healthy" if is_healthy else "unhealthy",
            "model": "RNAformer",
            "version": "32M_biophysical"
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"RNAformer health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

def parse_fasta_file(content):
    """Parse FASTA file content and extract sequences"""
    sequences = []
    current_sequence = ""
    
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('>'):
            # Header line
            if current_sequence:
                sequences.append(current_sequence)
                current_sequence = ""
        elif line:
            # Sequence line
            current_sequence += line
    
    # Add last sequence
    if current_sequence:
        sequences.append(current_sequence)
    
    return sequences

@rnaformer_bp.route('/download_ct', methods=['POST'])
def download_ct_files():
    """Download CT files for RNAformer results"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({"success": False, "error": "No results data provided"}), 400
        
        results = data['results']
        if not results:
            return jsonify({"success": False, "error": "No results to download"}), 400
        
        # Generate CT files
        ct_files = generate_multiple_ct_files(results, "rnaformer_structures")
        
        if not ct_files:
            return jsonify({"success": False, "error": "Failed to generate CT files"}), 500
        
        try:
            # Create ZIP file if multiple sequences
            if len(ct_files) > 1:
                zip_path = create_ct_zip_file(ct_files, "rnaformer_structures.zip")
                return send_file(
                    zip_path,
                    as_attachment=True,
                    download_name="rnaformer_structures.zip",
                    mimetype="application/zip"
                )
            else:
                # Send single CT file
                return send_file(
                    ct_files[0],
                    as_attachment=True,
                    download_name=os.path.basename(ct_files[0]),
                    mimetype="text/plain"
                )
        finally:
            # Clean up temporary files after sending
            cleanup_temp_files(ct_files)
            
    except Exception as e:
        logger.error(f"CT file download error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Download failed: {str(e)}"
        }), 500

@rnaformer_bp.route('/generate_ct', methods=['POST'])
def generate_single_ct():
    """Generate CT content for a single sequence"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        sequence = data.get('sequence', '')
        dot_bracket = data.get('dot_bracket', '')
        
        if not sequence or not dot_bracket:
            return jsonify({"success": False, "error": "Sequence and dot_bracket are required"}), 400
        
        if len(sequence) != len(dot_bracket):
            return jsonify({"success": False, "error": "Sequence and dot_bracket lengths must match"}), 400
        
        # Generate CT content with sequence name
        ct_content = generate_ct_content(sequence, dot_bracket, "sequence 1")
        
        return jsonify({
            "success": True,
            "ct_content": ct_content,
            "filename": f"rna_structure_{len(sequence)}bp.ct"
        })
        
    except Exception as e:
        logger.error(f"CT generation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"CT generation failed: {str(e)}"
        }), 500
