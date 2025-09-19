"""
Output utilities for RNA structure prediction models
Handles various output formats including CT file generation
"""

import os
import tempfile
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def generate_ct_content(sequence: str, dot_bracket: str, sequence_name: str = None) -> str:
    """
    Generate CT format content from RNA sequence and dot-bracket notation
    
    Args:
        sequence: RNA sequence string
        dot_bracket: Dot-bracket notation string
        sequence_name: Optional sequence name for the CT file
        
    Returns:
        CT format content as string
    """
    if len(sequence) != len(dot_bracket):
        raise ValueError(f"Sequence length ({len(sequence)}) must match dot-bracket length ({len(dot_bracket)})")
    
    length = len(sequence)
    ct_lines = [str(length)]  # Header line with sequence length
    
    # Add sequence name if provided
    if sequence_name:
        ct_lines.append(f"# {sequence_name}")
    
    # Create pairing dictionary from dot-bracket notation
    pairs = {}
    stack = []
    
    for i, char in enumerate(dot_bracket):
        if char == '(':
            stack.append(i)
        elif char == ')':
            if stack:
                j = stack.pop()
                pairs[i] = j
                pairs[j] = i
    
    # Generate CT lines for each nucleotide
    for i in range(length):
        base = sequence[i]
        paired_base = pairs.get(i, 0)
        ct_line = f"{i+1:4d} {base} {i:4d} {i+2:4d} {paired_base:4d} {i+1:4d}"
        ct_lines.append(ct_line)
    
    return '\n'.join(ct_lines)


def generate_ct_file(sequence: str, dot_bracket: str, filename: str = None) -> str:
    """
    Generate CT file from RNA sequence and dot-bracket notation
    
    Args:
        sequence: RNA sequence string
        dot_bracket: Dot-bracket notation string
        filename: Optional filename for the CT file
        
    Returns:
        Path to the generated CT file
    """
    try:
        # Generate CT content
        ct_content = generate_ct_content(sequence, dot_bracket)
        
        # Create temporary file
        if filename is None:
            filename = f"rna_structure_{len(sequence)}bp.ct"
        
        # Ensure filename has .ct extension
        if not filename.endswith('.ct'):
            filename += '.ct'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ct', delete=False) as temp_file:
            temp_file.write(ct_content)
            temp_file_path = temp_file.name
        
        # Rename to desired filename if specified
        if filename != os.path.basename(temp_file_path):
            final_path = os.path.join(os.path.dirname(temp_file_path), filename)
            os.rename(temp_file_path, final_path)
            return final_path
        
        return temp_file_path
        
    except Exception as e:
        logger.error(f"Error generating CT file: {str(e)}")
        raise


def generate_ct_file_with_name(sequence: str, dot_bracket: str, sequence_name: str, filename: str = None) -> str:
    """
    Generate CT file from RNA sequence and dot-bracket notation with sequence name
    
    Args:
        sequence: RNA sequence string
        dot_bracket: Dot-bracket notation string
        sequence_name: Name for the sequence
        filename: Optional filename for the CT file
        
    Returns:
        Path to the generated CT file
    """
    try:
        # Generate CT content with sequence name
        ct_content = generate_ct_content(sequence, dot_bracket, sequence_name)
        
        # Create temporary file
        if filename is None:
            filename = f"rna_structure_{len(sequence)}bp.ct"
        
        # Ensure filename has .ct extension
        if not filename.endswith('.ct'):
            filename += '.ct'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ct', delete=False) as temp_file:
            temp_file.write(ct_content)
            temp_file_path = temp_file.name
        
        # Rename to desired filename if specified
        if filename != os.path.basename(temp_file_path):
            final_path = os.path.join(os.path.dirname(temp_file_path), filename)
            os.rename(temp_file_path, final_path)
            return final_path
        
        return temp_file_path
        
    except Exception as e:
        logger.error(f"Error generating CT file: {str(e)}")
        raise


def generate_multiple_ct_files(results: List[Dict[str, Any]], base_filename: str = "rnaformer_results") -> List[str]:
    """
    Generate multiple CT files from RNAformer results
    
    Args:
        results: List of result dictionaries containing sequence and dot_bracket
        base_filename: Base filename for the CT files
        
    Returns:
        List of paths to generated CT files
    """
    ct_files = []
    
    for i, result in enumerate(results):
        sequence = result.get('sequence', '')
        dot_bracket = result.get('dot_bracket', '')
        
        if not sequence or not dot_bracket:
            logger.warning(f"Skipping result {i+1}: missing sequence or dot_bracket data")
            continue
        
        try:
            sequence_name = f"sequence {i+1}"
            filename = f"{base_filename}_sequence_{i+1}_{len(sequence)}bp.ct"
            ct_file_path = generate_ct_file_with_name(sequence, dot_bracket, sequence_name, filename)
            ct_files.append(ct_file_path)
        except Exception as e:
            logger.error(f"Error generating CT file for sequence {i+1}: {str(e)}")
            continue
    
    return ct_files


def create_ct_zip_file(ct_files: List[str], zip_filename: str = "rnaformer_structures.zip") -> str:
    """
    Create a ZIP file containing multiple CT files
    
    Args:
        ct_files: List of paths to CT files
        zip_filename: Name for the ZIP file
        
    Returns:
        Path to the created ZIP file
    """
    import zipfile
    
    if not ct_files:
        raise ValueError("No CT files provided for ZIP creation")
    
    # Create temporary ZIP file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
        zip_path = temp_zip.name
    
    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for ct_file in ct_files:
            if os.path.exists(ct_file):
                # Add file to ZIP with just the filename (no path)
                zipf.write(ct_file, os.path.basename(ct_file))
    
    # Rename to desired filename
    final_zip_path = os.path.join(os.path.dirname(zip_path), zip_filename)
    os.rename(zip_path, final_zip_path)
    
    return final_zip_path


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files
    
    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Could not delete temporary file {file_path}: {str(e)}")


def validate_dot_bracket(sequence: str, dot_bracket: str) -> bool:
    """
    Validate dot-bracket notation against sequence
    
    Args:
        sequence: RNA sequence string
        dot_bracket: Dot-bracket notation string
        
    Returns:
        True if valid, False otherwise
    """
    if len(sequence) != len(dot_bracket):
        return False
    
    # Check for valid characters
    valid_chars = set('().')
    if not all(c in valid_chars for c in dot_bracket):
        return False
    
    # Check for balanced parentheses
    stack = []
    for char in dot_bracket:
        if char == '(':
            stack.append(char)
        elif char == ')':
            if not stack:
                return False
            stack.pop()
    
    return len(stack) == 0


def format_ct_for_display(ct_content: str, max_lines: int = 20) -> str:
    """
    Format CT content for display in UI (truncated if too long)
    
    Args:
        ct_content: Full CT content
        max_lines: Maximum number of lines to display
        
    Returns:
        Formatted CT content for display
    """
    lines = ct_content.split('\n')
    
    if len(lines) <= max_lines:
        return ct_content
    
    # Show first few lines and last few lines with ellipsis
    first_lines = lines[:max_lines//2]
    last_lines = lines[-(max_lines//2):]
    
    formatted = '\n'.join(first_lines)
    formatted += '\n... (truncated) ...\n'
    formatted += '\n'.join(last_lines)
    
    return formatted
