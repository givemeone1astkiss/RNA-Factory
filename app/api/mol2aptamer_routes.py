from flask import Blueprint, request, jsonify
import logging
from app.utils.wrappers.mol2aptamer_wrapper import Mol2AptamerWrapper

# Create blueprint
mol2aptamer_bp = Blueprint('mol2aptamer', __name__)

# Initialize wrapper
mol2aptamer_wrapper = Mol2AptamerWrapper()

@mol2aptamer_bp.route('/predict', methods=['POST'])
def predict():
    """Generate RNA aptamer sequences from SMILES string"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['smiles', 'num_sequences', 'max_length', 'temperature', 'top_k', 'top_p', 'strategy']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Extract parameters
        smiles = data['smiles']
        num_sequences = int(data['num_sequences'])
        max_length = int(data['max_length'])
        temperature = float(data['temperature'])
        top_k = int(data['top_k'])
        top_p = float(data['top_p'])
        strategy = data['strategy']
        
        # Validate parameters
        if num_sequences < 1 or num_sequences > 100:
            return jsonify({
                'success': False,
                'error': 'Number of sequences must be between 1 and 100'
            }), 400
        
        if max_length < 10 or max_length > 200:
            return jsonify({
                'success': False,
                'error': 'Max length must be between 10 and 200'
            }), 400
        
        if temperature < 0.1 or temperature > 2.0:
            return jsonify({
                'success': False,
                'error': 'Temperature must be between 0.1 and 2.0'
            }), 400
        
        if top_k < 1 or top_k > 100:
            return jsonify({
                'success': False,
                'error': 'Top-K must be between 1 and 100'
            }), 400
        
        if top_p < 0.1 or top_p > 1.0:
            return jsonify({
                'success': False,
                'error': 'Top-P must be between 0.1 and 1.0'
            }), 400
        
        if strategy not in ['greedy', 'top_k', 'top_p']:
            return jsonify({
                'success': False,
                'error': 'Strategy must be one of: greedy, top_k, top_p'
            }), 400
        
        # Generate aptamers
        aptamers = mol2aptamer_wrapper.predict_aptamers(
            smiles=smiles,
            num_sequences=num_sequences,
            max_length=max_length,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            strategy=strategy
        )
        
        return jsonify({
            'success': True,
            'results': aptamers,
            'input_smiles': smiles,
            'parameters': {
                'num_sequences': num_sequences,
                'max_length': max_length,
                'temperature': temperature,
                'top_k': top_k,
                'top_p': top_p,
                'strategy': strategy
            }
        })
            
    except Exception as e:
        logging.error(f"Mol2Aptamer prediction failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Prediction failed: {str(e)}'
        }), 500

@mol2aptamer_bp.route('/info', methods=['GET'])
def info():
    """Get model information"""
    try:
        model_info = mol2aptamer_wrapper.get_model_info()
        return jsonify({
            'success': True,
            'model_info': model_info
        })
    except Exception as e:
        logging.error(f"Failed to get Mol2Aptamer model info: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get model info: {str(e)}'
        }), 500
