"""
Input validation and processing utilities for RNA-Factory platform.

This module provides functions for validating and processing various input formats
including FASTA files and raw RNA sequence text.
"""

import re
import os
import tempfile
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Valid RNA nucleotides
VALID_RNA_NUCLEOTIDES = {'A', 'U', 'C', 'G'}

# Valid protein amino acids (20 standard amino acids)
VALID_PROTEIN_AMINO_ACIDS = {'A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 
                            'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V'}

# FASTA header pattern
FASTA_HEADER_PATTERN = re.compile(r'^>.*$')

# RNA sequence pattern (only A, U, C, G characters, no whitespace)
RNA_SEQUENCE_PATTERN = re.compile(r'^[AUCG]+$')

# Protein sequence pattern (only standard amino acids, no whitespace)
PROTEIN_SEQUENCE_PATTERN = re.compile(r'^[ARNDCQEGHILKMFPSTWYV]+$')

# SMILES pattern (basic validation - contains only valid SMILES characters)
SMILES_PATTERN = re.compile(r'^[A-Za-z0-9@+\-\[\]()=#\\/]+$')


class InputValidationError(Exception):
    """Exception raised for input validation errors."""
    pass


class FASTAValidationError(InputValidationError):
    """Exception raised for FASTA format validation errors."""
    pass


class RNASequenceError(InputValidationError):
    """Exception raised for RNA sequence validation errors."""
    pass


class ProteinSequenceError(InputValidationError):
    """Exception raised for protein sequence validation errors."""
    pass


def validate_rna_sequence(sequence: str) -> bool:
    """
    Validate if a string contains only valid RNA nucleotides.
    Automatically converts lowercase letters to uppercase before validation.
    
    Args:
        sequence: RNA sequence string to validate
        
    Returns:
        bool: True if sequence is valid, False otherwise
    """
    if not sequence or not isinstance(sequence, str):
        return False
    
    # Convert to uppercase for validation
    sequence = sequence.upper()
    
    # Check if sequence contains only valid nucleotides (no whitespace allowed)
    # First check if it matches the pattern, then verify no whitespace
    if not RNA_SEQUENCE_PATTERN.match(sequence):
        return False
    
    # Additional check: ensure no whitespace characters
    return not any(c.isspace() for c in sequence)


def validate_rna_sequences(sequences: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate a list of RNA sequences.
    Automatically converts lowercase letters to uppercase before validation.
    
    Args:
        sequences: List of RNA sequence strings
        
    Returns:
        Tuple of (valid_sequences, invalid_sequences)
    """
    valid_sequences = []
    invalid_sequences = []
    
    for i, sequence in enumerate(sequences):
        # Clean the sequence for validation (strip whitespace and convert to uppercase)
        clean_sequence = sequence.strip().upper()
        
        if validate_rna_sequence(clean_sequence):
            valid_sequences.append(clean_sequence)
        else:
            invalid_sequences.append(f"Sequence {i+1}: {sequence[:50]}{'...' if len(sequence) > 50 else ''}")
    
    return valid_sequences, invalid_sequences


def parse_text_input(text: str) -> List[str]:
    """
    Parse text input containing RNA sequences.
    Automatically converts lowercase letters to uppercase.
    
    Args:
        text: Raw text input containing RNA sequences
        
    Returns:
        List of valid RNA sequences (all uppercase)
        
    Raises:
        RNASequenceError: If no valid sequences found
    """
    if not text or not isinstance(text, str):
        raise RNASequenceError("Empty or invalid text input")
    
    # Split by newlines and filter out empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        raise RNASequenceError("No sequences found in input text")
    
    # Filter out FASTA headers (lines starting with >)
    sequences = [line for line in lines if not line.startswith('>')]
    
    if not sequences:
        raise RNASequenceError("No sequences found after filtering FASTA headers")
    
    # Validate sequences (this will automatically convert to uppercase)
    valid_sequences, invalid_sequences = validate_rna_sequences(sequences)
    
    if not valid_sequences:
        error_msg = "No valid RNA sequences found. "
        if invalid_sequences:
            error_msg += f"Invalid sequences: {'; '.join(invalid_sequences[:3])}"
            if len(invalid_sequences) > 3:
                error_msg += f" and {len(invalid_sequences) - 3} more"
        raise RNASequenceError(error_msg)
    
    if invalid_sequences:
        logger.warning(f"Found {len(invalid_sequences)} invalid sequences: {'; '.join(invalid_sequences[:3])}")
    
    return valid_sequences


def validate_fasta_file(file_path: Union[str, Path]) -> bool:
    """
    Validate if a file is a proper FASTA format file.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        bool: True if file is valid FASTA format
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FASTAValidationError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise FASTAValidationError(f"Path is not a file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        raise FASTAValidationError(f"Error reading file: {e}")
    
    if not content:
        raise FASTAValidationError("File is empty")
    
    lines = content.split('\n')
    has_header = False
    has_sequence = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('>'):
            has_header = True
        else:
            has_sequence = True
            # Check if sequence line contains only valid characters (convert to uppercase first)
            if not RNA_SEQUENCE_PATTERN.match(line.upper()):
                raise FASTAValidationError(f"Invalid sequence line: {line[:50]}{'...' if len(line) > 50 else ''}")
    
    if not has_header:
        raise FASTAValidationError("No FASTA headers found (lines starting with '>')")
    
    if not has_sequence:
        raise FASTAValidationError("No sequence data found")
    
    return True


def parse_fasta_file(file_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Parse a FASTA file and extract sequences.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        List of dictionaries containing 'header' and 'sequence' keys
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    file_path = Path(file_path)
    
    # Validate file first
    validate_fasta_file(file_path)
    
    sequences = []
    current_header = None
    current_sequence = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line:
                    continue
                
                if line.startswith('>'):
                    # Save previous sequence if exists
                    if current_header and current_sequence:
                        sequence = ''.join(current_sequence).upper()
                        if validate_rna_sequence(sequence):
                            sequences.append({
                                'header': current_header,
                                'sequence': sequence
                            })
                        else:
                            logger.warning(f"Invalid sequence in {current_header}: {sequence[:50]}...")
                    
                    # Start new sequence
                    current_header = line[1:].strip()  # Remove '>' prefix
                    current_sequence = []
                
                else:
                    # Add to current sequence (convert to uppercase)
                    if not current_header:
                        raise FASTAValidationError(f"Sequence data found before header at line {line_num}")
                    
                    current_sequence.append(line.upper())
        
        # Handle last sequence
        if current_header and current_sequence:
            sequence = ''.join(current_sequence).upper()
            if validate_rna_sequence(sequence):
                sequences.append({
                    'header': current_header,
                    'sequence': sequence
                })
            else:
                logger.warning(f"Invalid sequence in {current_header}: {sequence[:50]}...")
    
    except Exception as e:
        raise FASTAValidationError(f"Error parsing FASTA file: {e}")
    
    if not sequences:
        raise FASTAValidationError("No valid sequences found in FASTA file")
    
    return sequences


def extract_sequences_from_fasta(file_path: Union[str, Path]) -> List[str]:
    """
    Extract RNA sequences from a FASTA file.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        List of RNA sequence strings
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    parsed_sequences = parse_fasta_file(file_path)
    return [seq['sequence'] for seq in parsed_sequences]


def create_fasta_file(sequences: List[str], headers: Optional[List[str]] = None) -> str:
    """
    Create a temporary FASTA file from sequences.
    
    Args:
        sequences: List of RNA sequences
        headers: Optional list of headers for sequences
        
    Returns:
        Path to the created temporary file
    """
    if not sequences:
        raise ValueError("No sequences provided")
    
    if headers and len(headers) != len(sequences):
        raise ValueError("Number of headers must match number of sequences")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False)
    
    try:
        for i, sequence in enumerate(sequences):
            # Validate sequence
            if not validate_rna_sequence(sequence):
                raise RNASequenceError(f"Invalid sequence {i+1}: {sequence[:50]}...")
            
            # Write header
            header = headers[i] if headers else f"sequence_{i+1}"
            temp_file.write(f">{header}\n")
            
            # Write sequence (split into lines of 80 characters)
            clean_sequence = sequence.strip().upper()
            for j in range(0, len(clean_sequence), 80):
                temp_file.write(clean_sequence[j:j+80] + '\n')
        
        temp_file.close()
        return temp_file.name
    
    except Exception as e:
        # Clean up on error
        temp_file.close()
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise


def process_input(input_data: Union[str, Path], input_type: str = 'auto') -> Dict[str, Union[List[str], str]]:
    """
    Process input data and return standardized format.
    
    Args:
        input_data: Input data (text string or file path)
        input_type: Type of input ('text', 'file', or 'auto')
        
    Returns:
        Dictionary containing:
        - 'sequences': List of RNA sequences
        - 'input_type': Type of input processed
        - 'file_path': Path to temporary file (if created)
        - 'headers': List of sequence headers (if from FASTA)
    """
    result = {
        'sequences': [],
        'input_type': input_type,
        'file_path': None,
        'headers': None
    }
    
    if input_type == 'auto':
        # Auto-detect input type
        if isinstance(input_data, (str, Path)) and Path(input_data).exists():
            input_type = 'file'
        else:
            input_type = 'text'
    
    if input_type == 'text':
        # Process text input
        sequences = parse_text_input(str(input_data))
        result['sequences'] = sequences
        result['input_type'] = 'text'
        
        # Create temporary FASTA file for downstream processing
        temp_file = create_fasta_file(sequences)
        result['file_path'] = temp_file
    
    elif input_type == 'file':
        # Process file input
        file_path = Path(input_data)
        parsed_sequences = parse_fasta_file(file_path)
        
        sequences = [seq['sequence'] for seq in parsed_sequences]
        headers = [seq['header'] for seq in parsed_sequences]
        
        result['sequences'] = sequences
        result['input_type'] = 'file'
        result['file_path'] = str(file_path)
        result['headers'] = headers
    
    else:
        raise ValueError(f"Invalid input_type: {input_type}")
    
    return result


def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up temporary file.
    
    Args:
        file_path: Path to temporary file to delete
    """
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary file {file_path}: {e}")


def validate_model_input(sequences: List[str], min_length: int = 1, max_length: int = 10000) -> List[str]:
    """
    Validate sequences for model input with length constraints.
    Automatically converts lowercase letters to uppercase.
    
    Args:
        sequences: List of RNA sequences
        min_length: Minimum sequence length
        max_length: Maximum sequence length
        
    Returns:
        List of valid sequences (all uppercase)
        
    Raises:
        RNASequenceError: If no valid sequences found
    """
    if not sequences:
        raise RNASequenceError("No sequences provided")
    
    valid_sequences = []
    invalid_reasons = []
    
    for i, sequence in enumerate(sequences):
        # Convert to uppercase before validation
        sequence = sequence.strip().upper()
        
        if not validate_rna_sequence(sequence):
            invalid_reasons.append(f"Sequence {i+1}: Invalid nucleotides")
            continue
        
        seq_len = len(sequence)
        if seq_len < min_length:
            invalid_reasons.append(f"Sequence {i+1}: Too short ({seq_len} < {min_length})")
            continue
        
        if seq_len > max_length:
            invalid_reasons.append(f"Sequence {i+1}: Too long ({seq_len} > {max_length})")
            continue
        
        valid_sequences.append(sequence)
    
    if not valid_sequences:
        error_msg = "No valid sequences found for model input. "
        if invalid_reasons:
            error_msg += f"Issues: {'; '.join(invalid_reasons[:3])}"
            if len(invalid_reasons) > 3:
                error_msg += f" and {len(invalid_reasons) - 3} more"
        raise RNASequenceError(error_msg)
    
    if invalid_reasons:
        logger.warning(f"Found {len(invalid_reasons)} invalid sequences: {'; '.join(invalid_reasons[:3])}")
    
    return valid_sequences


def validate_protein_sequence(sequence: str) -> bool:
    """
    Validate if a string contains only valid protein amino acids.
    Automatically converts lowercase letters to uppercase before validation.
    
    Args:
        sequence: Protein sequence string to validate
        
    Returns:
        bool: True if sequence is valid, False otherwise
    """
    if not sequence or not isinstance(sequence, str):
        return False
    
    # Convert to uppercase for validation
    sequence = sequence.upper()
    
    # Check if sequence contains only valid amino acids (no whitespace allowed)
    if not PROTEIN_SEQUENCE_PATTERN.match(sequence):
        return False
    
    # Additional check: ensure no whitespace characters
    return not any(c.isspace() for c in sequence)


def validate_protein_sequences(sequences: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate a list of protein sequences.
    Automatically converts lowercase letters to uppercase before validation.
    
    Args:
        sequences: List of protein sequence strings
        
    Returns:
        Tuple of (valid_sequences, invalid_sequences)
    """
    valid_sequences = []
    invalid_sequences = []
    
    for i, sequence in enumerate(sequences):
        # Clean the sequence for validation (strip whitespace and convert to uppercase)
        clean_sequence = sequence.strip().upper()
        
        if validate_protein_sequence(clean_sequence):
            valid_sequences.append(clean_sequence)
        else:
            invalid_sequences.append(f"Sequence {i+1}: {sequence[:50]}{'...' if len(sequence) > 50 else ''}")
    
    return valid_sequences, invalid_sequences


def parse_protein_text_input(text: str) -> List[str]:
    """
    Parse text input containing protein sequences.
    Automatically converts lowercase letters to uppercase.
    
    Args:
        text: Raw text input containing protein sequences
        
    Returns:
        List of valid protein sequences (all uppercase)
        
    Raises:
        ProteinSequenceError: If no valid sequences found
    """
    if not text or not isinstance(text, str):
        raise ProteinSequenceError("Empty or invalid text input")
    
    # Split by newlines and filter out empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        raise ProteinSequenceError("No sequences found in input text")
    
    # Filter out FASTA headers (lines starting with >)
    sequences = [line for line in lines if not line.startswith('>')]
    
    if not sequences:
        raise ProteinSequenceError("No sequences found after filtering FASTA headers")
    
    # Validate sequences (this will automatically convert to uppercase)
    valid_sequences, invalid_sequences = validate_protein_sequences(sequences)
    
    if not valid_sequences:
        error_msg = "No valid protein sequences found. "
        if invalid_sequences:
            error_msg += f"Invalid sequences: {'; '.join(invalid_sequences[:3])}"
            if len(invalid_sequences) > 3:
                error_msg += f" and {len(invalid_sequences) - 3} more"
        raise ProteinSequenceError(error_msg)
    
    if invalid_sequences:
        logger.warning(f"Found {len(invalid_sequences)} invalid protein sequences: {'; '.join(invalid_sequences[:3])}")
    
    return valid_sequences


def validate_protein_fasta_file(file_path: Union[str, Path]) -> bool:
    """
    Validate if a file is a proper FASTA format file for protein sequences.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        bool: True if file is valid FASTA format
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FASTAValidationError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise FASTAValidationError(f"Path is not a file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        raise FASTAValidationError(f"Error reading file: {e}")
    
    if not content:
        raise FASTAValidationError("File is empty")
    
    lines = content.split('\n')
    has_header = False
    has_sequence = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('>'):
            has_header = True
        else:
            has_sequence = True
            # Check if sequence line contains only valid protein characters
            if not PROTEIN_SEQUENCE_PATTERN.match(line.upper()):
                raise FASTAValidationError(f"Invalid protein sequence line: {line[:50]}{'...' if len(line) > 50 else ''}")
    
    if not has_header:
        raise FASTAValidationError("No FASTA headers found (lines starting with '>')")
    
    if not has_sequence:
        raise FASTAValidationError("No sequence data found")
    
    return True


def parse_protein_fasta_file(file_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Parse a FASTA file and extract protein sequences.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        List of dictionaries containing 'header' and 'sequence' keys
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    file_path = Path(file_path)
    
    # Validate file first
    validate_protein_fasta_file(file_path)
    
    sequences = []
    current_header = None
    current_sequence = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line:
                    continue
                
                if line.startswith('>'):
                    # Save previous sequence if exists
                    if current_header and current_sequence:
                        sequence = ''.join(current_sequence).upper()
                        if validate_protein_sequence(sequence):
                            sequences.append({
                                'header': current_header,
                                'sequence': sequence
                            })
                        else:
                            logger.warning(f"Invalid protein sequence in {current_header}: {sequence[:50]}...")
                    
                    # Start new sequence
                    current_header = line[1:].strip()  # Remove '>' prefix
                    current_sequence = []
                
                else:
                    # Add to current sequence (convert to uppercase)
                    if not current_header:
                        raise FASTAValidationError(f"Sequence data found before header at line {line_num}")
                    
                    current_sequence.append(line.upper())
        
        # Handle last sequence
        if current_header and current_sequence:
            sequence = ''.join(current_sequence).upper()
            if validate_protein_sequence(sequence):
                sequences.append({
                    'header': current_header,
                    'sequence': sequence
                })
            else:
                logger.warning(f"Invalid protein sequence in {current_header}: {sequence[:50]}...")
    
    except Exception as e:
        raise FASTAValidationError(f"Error parsing FASTA file: {e}")
    
    if not sequences:
        raise FASTAValidationError("No valid protein sequences found in FASTA file")
    
    return sequences


def extract_protein_sequences_from_fasta(file_path: Union[str, Path]) -> List[str]:
    """
    Extract protein sequences from a FASTA file.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        List of protein sequence strings
        
    Raises:
        FASTAValidationError: If file is invalid
    """
    parsed_sequences = parse_protein_fasta_file(file_path)
    return [seq['sequence'] for seq in parsed_sequences]


def validate_rnamigos2_input(data: Dict) -> Dict[str, Union[bool, str]]:
    """
    Validate RNAmigos2 input data.
    
    Args:
        data: Dictionary containing input data with keys:
            - cif_content: mmCIF structure content (string)
            - residue_list: List of binding site residue identifiers (list)
            - smiles_list: List of SMILES strings (list)
    
    Returns:
        Dictionary with 'valid' boolean and 'error' string if invalid
    """
    try:
        # Check required fields
        if 'cif_content' not in data:
            return {"valid": False, "error": "Missing cif_content field"}
        
        if 'residue_list' not in data:
            return {"valid": False, "error": "Missing residue_list field"}
        
        if 'smiles_list' not in data:
            return {"valid": False, "error": "Missing smiles_list field"}
        
        # Validate CIF content
        cif_content = data['cif_content']
        if not isinstance(cif_content, str) or not cif_content.strip():
            return {"valid": False, "error": "CIF content must be a non-empty string"}
        
        # Check for basic mmCIF structure
        if 'data_' not in cif_content.lower():
            return {"valid": False, "error": "Invalid mmCIF format: missing data_ block"}
        
        # Validate residue list
        residue_list = data['residue_list']
        if not isinstance(residue_list, list) or len(residue_list) == 0:
            return {"valid": False, "error": "residue_list must be a non-empty list"}
        
        # Validate residue format (e.g., "A.20", "B.15")
        residue_pattern = re.compile(r'^[A-Za-z0-9]+\.\d+$')
        for residue in residue_list:
            if not isinstance(residue, str) or not residue_pattern.match(residue):
                return {"valid": False, "error": f"Invalid residue format: {residue}. Expected format: 'A.20'"}
        
        # Validate SMILES list
        smiles_list = data['smiles_list']
        if not isinstance(smiles_list, list) or len(smiles_list) == 0:
            return {"valid": False, "error": "smiles_list must be a non-empty list"}
        
        # Basic SMILES validation (check for common characters)
        smiles_pattern = re.compile(r'^[A-Za-z0-9@\[\]()=#\\/+-]+$')
        for i, smiles in enumerate(smiles_list):
            if not isinstance(smiles, str) or not smiles.strip():
                return {"valid": False, "error": f"SMILES {i+1} must be a non-empty string"}
            
            # Basic character validation
            if not smiles_pattern.match(smiles.strip()):
                return {"valid": False, "error": f"Invalid SMILES format at position {i+1}: {smiles}"}
        
        # Check reasonable limits
        if len(smiles_list) > 1000:
            return {"valid": False, "error": "Too many SMILES strings (maximum 1000)"}
        
        if len(residue_list) > 50:
            return {"valid": False, "error": "Too many residues (maximum 50)"}
        
        return {"valid": True}
        
    except Exception as e:
        logger.error(f"RNAmigos2 input validation error: {e}")
        return {"valid": False, "error": f"Validation error: {str(e)}"}


def validate_smiles(smiles: str) -> bool:
    """
    Validate if a string is a valid SMILES notation.
    
    Args:
        smiles: SMILES string to validate
        
    Returns:
        bool: True if SMILES is valid, False otherwise
    """
    if not smiles or not isinstance(smiles, str):
        return False
    
    # Basic validation - check if it contains only valid SMILES characters
    if not SMILES_PATTERN.match(smiles.strip()):
        return False
    
    # Additional checks for common SMILES patterns
    smiles = smiles.strip()
    
    # Must not be empty
    if not smiles:
        return False
    
    # Must contain at least one letter (element symbol)
    if not re.search(r'[A-Za-z]', smiles):
        return False
    
    return True


def validate_pdb_file(file_path: Union[str, Path]) -> bool:
    """
    Validate if a file is a proper PDB format file.
    
    Args:
        file_path: Path to the PDB file
        
    Returns:
        bool: True if file is valid PDB format
        
    Raises:
        InputValidationError: If file is invalid
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise InputValidationError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise InputValidationError(f"Path is not a file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        raise InputValidationError(f"Error reading file: {e}")
    
    if not content:
        raise InputValidationError("File is empty")
    
    lines = content.split('\n')
    has_atom = False
    has_header = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for ATOM or HETATM records
        if line.startswith('ATOM') or line.startswith('HETATM'):
            has_atom = True
        # Check for HEADER record
        elif line.startswith('HEADER'):
            has_header = True
    
    if not has_atom:
        raise InputValidationError("No ATOM or HETATM records found in PDB file")
    
    return True


