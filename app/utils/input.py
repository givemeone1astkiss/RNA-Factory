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


def validate_zhmolgraph_input(rna_sequences: List[str], protein_sequences: List[str], 
                             min_rna_length: int = 1, max_rna_length: int = 10000,
                             min_protein_length: int = 1, max_protein_length: int = 10000) -> Tuple[List[str], List[str]]:
    """
    Validate sequences for ZHMolGraph model input with length constraints.
    
    Args:
        rna_sequences: List of RNA sequences
        protein_sequences: List of protein sequences
        min_rna_length: Minimum RNA sequence length
        max_rna_length: Maximum RNA sequence length
        min_protein_length: Minimum protein sequence length
        max_protein_length: Maximum protein sequence length
        
    Returns:
        Tuple of (valid_rna_sequences, valid_protein_sequences)
        
    Raises:
        InputValidationError: If no valid sequences found
    """
    if not rna_sequences or not protein_sequences:
        raise InputValidationError("Both RNA and protein sequences are required")
    
    if len(rna_sequences) != len(protein_sequences):
        raise InputValidationError("Number of RNA sequences must match number of protein sequences")
    
    valid_rna_sequences = []
    valid_protein_sequences = []
    invalid_reasons = []
    
    for i, (rna_seq, protein_seq) in enumerate(zip(rna_sequences, protein_sequences)):
        # Validate RNA sequence
        if not validate_rna_sequence(rna_seq):
            invalid_reasons.append(f"RNA sequence {i+1}: Invalid nucleotides")
            continue
        
        rna_len = len(rna_seq.strip())
        if rna_len < min_rna_length:
            invalid_reasons.append(f"RNA sequence {i+1}: Too short ({rna_len} < {min_rna_length})")
            continue
        
        if rna_len > max_rna_length:
            invalid_reasons.append(f"RNA sequence {i+1}: Too long ({rna_len} > {max_rna_length})")
            continue
        
        # Validate protein sequence
        if not validate_protein_sequence(protein_seq):
            invalid_reasons.append(f"Protein sequence {i+1}: Invalid amino acids")
            continue
        
        protein_len = len(protein_seq.strip())
        if protein_len < min_protein_length:
            invalid_reasons.append(f"Protein sequence {i+1}: Too short ({protein_len} < {min_protein_length})")
            continue
        
        if protein_len > max_protein_length:
            invalid_reasons.append(f"Protein sequence {i+1}: Too long ({protein_len} > {max_protein_length})")
            continue
        
        valid_rna_sequences.append(rna_seq.strip().upper())
        valid_protein_sequences.append(protein_seq.strip().upper())
    
    if not valid_rna_sequences:
        error_msg = "No valid sequence pairs found for ZHMolGraph input. "
        if invalid_reasons:
            error_msg += f"Issues: {'; '.join(invalid_reasons[:3])}"
            if len(invalid_reasons) > 3:
                error_msg += f" and {len(invalid_reasons) - 3} more"
        raise InputValidationError(error_msg)
    
    if invalid_reasons:
        logger.warning(f"Found {len(invalid_reasons)} invalid sequence pairs: {'; '.join(invalid_reasons[:3])}")
    
    return valid_rna_sequences, valid_protein_sequences
