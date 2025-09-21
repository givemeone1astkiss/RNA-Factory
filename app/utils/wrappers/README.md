# Model Wrappers Documentation

This document provides detailed information about the model wrappers in the RNA-Factory platform, including their packaging methods, calling methods, and testing approaches.

## Table of Contents

- [Overview](#overview)
- [BPFold Wrapper](#bpfold-wrapper)
- [UFold Wrapper](#ufold-wrapper)
- [MXFold2 Wrapper](#mxfold2-wrapper)
- [RNAformer Wrapper](#rnaformer-wrapper)
- [RNAmigos2 Wrapper](#rnamigos2-wrapper)
- [Mol2Aptamer Wrapper](#mol2aptamer-wrapper)
- [RNAFlow Wrapper](#rnaflow-wrapper)
- [General Testing Methods](#general-testing-methods)
- [Troubleshooting](#troubleshooting)

## Overview

All wrappers follow a unified design pattern:

1. **Initialization**: Set model path and virtual environment path
2. **Input Processing**: Convert user input to model-required format
3. **Model Invocation**: Call model through subprocess
4. **Result Parsing**: Convert model output to unified format
5. **Cleanup**: Remove temporary files

## BPFold Wrapper

### Packaging Method

BPFold wrapper calls BPFold's Python script through subprocess for RNA secondary structure prediction.

**File Location**: `app/utils/wrappers/bpfold_wrapper.py`

**Main Class**: `BPFoldWrapper`

### Calling Method

```python
from app.utils.wrappers.bpfold_wrapper import BPFoldWrapper

# Initialize wrapper
wrapper = BPFoldWrapper(
    model_path="/path/to/BPfold/model_predict",
    environment_path="/path/to/.venv_bpfold"
)

# Predict RNA secondary structure
result = wrapper.predict(
    rna_sequences=["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
    output_format="ct"  # Supports "ct", "dotbracket", "bpseq"
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
            "structure": "(((((((((..(((...)))..))))))))",
            "energy": -10.5,
            "length": 31
        }
    ],
    "ct_content": "CT file content...",
    "error": None
}
```

### Input Requirements

- **rna_sequences**: List of RNA sequences, supports FASTA format
- **output_format**: Output format, supports "ct", "dotbracket", "bpseq"

### Output Format

- **success**: Boolean value indicating whether prediction was successful
- **results**: List of prediction results
- **ct_content**: CT format structure file content
- **error**: Error message (if any)

### Testing Method

```python
# Basic test
def test_bpfold_basic():
    wrapper = BPFoldWrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert result["success"] == True
    assert len(result["results"]) == 1

# Multiple sequences test
def test_bpfold_multiple():
    wrapper = BPFoldWrapper()
    sequences = [
        "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
        "AUGCGUAUCGUAUCGUAUCGUAUCGUAUCGU"
    ]
    result = wrapper.predict(sequences)
    assert result["success"] == True
    assert len(result["results"]) == 2

# Error handling test
def test_bpfold_error():
    wrapper = BPFoldWrapper()
    result = wrapper.predict(["INVALID_SEQUENCE_WITH_NON_RNA_CHARS"])
    assert result["success"] == False
    assert result["error"] is not None
```

## UFold Wrapper

### Packaging Method

UFold wrapper calls UFold's Python script through subprocess for RNA secondary structure prediction.

**File Location**: `app/utils/wrappers/ufold_wrapper.py`

**Main Class**: `UFoldWrapper`

### Calling Method

```python
from app.utils.wrappers.ufold_wrapper import UFoldWrapper

# Initialize wrapper
wrapper = UFoldWrapper(
    model_path="/path/to/UFold",
    environment_path="/path/to/.venv_ufold"
)

# Predict RNA secondary structure
result = wrapper.predict(
    rna_sequences=["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
    output_format="ct"  # Supports "ct", "dotbracket"
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
            "structure": "(((((((((..(((...)))..))))))))",
            "confidence": 0.85,
            "length": 31
        }
    ],
    "ct_content": "CT file content...",
    "error": None
}
```

### Input Requirements

- **rna_sequences**: List of RNA sequences
- **output_format**: Output format, supports "ct", "dotbracket"

### Output Format

- **success**: Boolean value indicating whether prediction was successful
- **results**: List of prediction results, includes confidence field
- **ct_content**: CT format structure file content
- **error**: Error message (if any)

### Testing Method

```python
# Basic test
def test_ufold_basic():
    wrapper = UFoldWrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert result["success"] == True
    assert "confidence" in result["results"][0]

# Confidence test
def test_ufold_confidence():
    wrapper = UFoldWrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert 0 <= result["results"][0]["confidence"] <= 1
```

## MXFold2 Wrapper

### Packaging Method

MXFold2 wrapper calls external MXFold2 package through subprocess for RNA secondary structure prediction. Uses pre-compiled wheel file installation, supports multiple model architectures and output formats.

**File Location**: `app/utils/wrappers/mxfold2_wrapper.py`

**Main Class**: `MXFold2Wrapper`

**Installation Requirements**: Python 3.10+

### Calling Method

```python
from app.utils.wrappers.mxfold2_wrapper import MXFold2Wrapper

# Initialize wrapper (using dynamic paths)
wrapper = MXFold2Wrapper()

# Predict RNA secondary structure
result = wrapper.predict(
    rna_sequences=["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
    output_format="ct",  # Supports "ct", "dotbracket", "bpseq"
    model="MixC",        # Supports "Turner", "Zuker", "ZukerS", "ZukerL", "ZukerC", "Mix", "MixC"
    gpu=-1               # -1 for CPU, 0+ for GPU
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
            "structure": "(((((((((..(((...)))..)))))))))",
            "energy": 16.7,
            "length": 31,
            "format": "ct",
            "ct_data": "CT file content...",
            "bpseq_data": "BPSEQ file content..."  # If output format is bpseq
        }
    ],
    "stdout": "MXFold2 raw output...",
    "stderr": "",
    "error": None
}
```

### Input Requirements

- **rna_sequences**: List of RNA sequences
- **output_format**: Output format, supports "ct", "dotbracket", "bpseq"
- **model**: Model type, supports "Turner", "Zuker", "ZukerS", "ZukerL", "ZukerC", "Mix", "MixC"
- **gpu**: GPU ID, -1 for CPU, 0+ for GPU
- **max_helix_length**: Maximum helix length (optional)
- **use_constraint**: Whether to use constraints (optional)

### Output Format

- **success**: Boolean value indicating whether prediction was successful
- **results**: List of prediction results, includes the following fields:
  - **sequence**: RNA sequence
  - **structure**: dot-bracket structure representation
  - **energy**: Energy value (kcal/mol)
  - **length**: Sequence length
  - **format**: Output format
  - **ct_data**: CT format data (if output format is ct)
  - **bpseq_data**: BPSEQ format data (if output format is bpseq)
- **stdout**: MXFold2 raw standard output
- **stderr**: MXFold2 raw error output
- **error**: Error message (if any)

### Model Information

```python
# Get model information
info = wrapper.get_model_info()
print(f"Model name: {info['name']}")
print(f"Version: {info['version']}")
print(f"Description: {info['description']}")
print(f"Supported models: {info['supported_models']}")
print(f"Supported formats: {info['supported_formats']}")
```

### Testing Method

```python
# Basic test
def test_mxfold2_basic():
    wrapper = MXFold2Wrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert result["success"] == True
    assert "energy" in result["results"][0]
    assert "structure" in result["results"][0]

# Different models test
def test_mxfold2_models():
    wrapper = MXFold2Wrapper()
    models = ["Turner", "Zuker", "MixC"]
    for model in models:
        result = wrapper.predict(
            ["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
            model=model
        )
        assert result["success"] == True

# Different formats test
def test_mxfold2_formats():
    wrapper = MXFold2Wrapper()
    formats = ["ct", "dotbracket", "bpseq"]
    for fmt in formats:
        result = wrapper.predict(
            ["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
            output_format=fmt
        )
        assert result["success"] == True
        if fmt == "ct":
            assert "ct_data" in result["results"][0]
        elif fmt == "bpseq":
            assert "bpseq_data" in result["results"][0]

# Energy value test
def test_mxfold2_energy():
    wrapper = MXFold2Wrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert isinstance(result["results"][0]["energy"], (int, float))
    assert result["results"][0]["energy"] > 0  # Energy values are usually positive
```

### Installation Process

MXFold2 uses pre-compiled wheel file installation:

1. **Create virtual environment**:
   ```bash
   uv venv .venv_mxfold2 --python 3.10
   ```

2. **Install MXFold2**:
   ```bash
   uv pip install --python .venv_mxfold2/bin/python models/mxfold2/mxfold2-0.1.2-cp310-cp310-manylinux_2_17_x86_64.whl
   ```

3. **Verify installation**:
   ```bash
   source .venv_mxfold2/bin/activate
   mxfold2 --help
   ```

### Features

- **Deep learning prediction**: Uses deep neural networks for RNA secondary structure prediction
- **Thermodynamic integration**: Combines thermodynamic parameters to improve prediction accuracy
- **Multiple model architectures**: Supports 7 different model architectures
- **Multiple output formats**: Supports CT, dot-bracket, BPSEQ formats
- **GPU acceleration**: Supports CUDA acceleration
- **High accuracy**: Achieves 91% accuracy in multiple benchmark tests
- **Fast inference**: Optimized inference speed
- **Long sequence support**: Supports longer RNA sequence prediction

## RNAformer Wrapper

### Packaging Method

RNAformer wrapper calls RNAformer's Python script through subprocess for RNA secondary structure prediction. Uses Transformer-based deep learning model for high-accuracy RNA secondary structure prediction.

**File Location**: `app/utils/wrappers/rnaformer_wrapper.py`

**Main Class**: `RNAformerWrapper`

**Installation Requirements**: Python 3.10+ (required, as torch==2.1.0 doesn't support Python 3.12)

### Calling Method

```python
from app.utils.wrappers.rnaformer_wrapper import RNAformerWrapper

# Initialize wrapper (using dynamic paths)
wrapper = RNAformerWrapper()

# Predict RNA secondary structure
result = wrapper.predict(
    sequences=["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"]
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
            "dot_bracket": ")))))))))..)))...(((..(((((((((",
            "length": 31,
            "ct_content": "31\n   1 G    0    2   30    1\n...",
            "pairing_indices": [0, 30, 1, 29, 2, 28, ...]
        }
    ],
    "model": "RNAformer",
    "total_sequences": 1,
    "error": None
}
```

### Input Requirements

- **sequences**: List of RNA sequences

### Output Format

- **success**: Boolean value indicating whether prediction was successful
- **results**: List of prediction results, includes the following fields:
  - **sequence**: RNA sequence
  - **dot_bracket**: dot-bracket structure representation
  - **length**: Sequence length
  - **ct_content**: CT format data
  - **pairing_indices**: List of pairing indices
- **model**: Model name
- **total_sequences**: Total number of processed sequences
- **error**: Error message (if any)

### Model Information

```python
# Get model information
info = wrapper.get_model_info()
print(f"Model name: {info['name']}")
print(f"Version: {info['version']}")
print(f"Description: {info['description']}")
```

### Testing Method

```python
# Basic test
def test_rnaformer_basic():
    wrapper = RNAformerWrapper()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    assert result["success"] == True
    assert len(result["results"]) == 1
    assert "dot_bracket" in result["results"][0]
    assert "ct_content" in result["results"][0]

# Long sequence test
def test_rnaformer_long_sequence():
    wrapper = RNAformerWrapper()
    long_seq = "G" * 100 + "U" * 100 + "C" * 100 + "A" * 100
    result = wrapper.predict([long_seq])
    assert result["success"] == True
    assert result["results"][0]["length"] == 400

# Model test
def test_rnaformer_model():
    wrapper = RNAformerWrapper()
    is_working = wrapper.test_model()
    assert is_working == True

# Dot-bracket conversion test
def test_rnaformer_conversion():
    wrapper = RNAformerWrapper()
    sequence = "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"
    pairing_indices = [0, 30, 1, 29, 2, 28]
    dot_bracket = wrapper._indices_to_dot_bracket(sequence, pairing_indices)
    assert len(dot_bracket) == len(sequence)
    assert dot_bracket.count('(') == dot_bracket.count(')')
```

### Installation Process

RNAformer requires specific Python version and dependencies:

1. **Create virtual environment** (must use Python 3.10):
   ```bash
   uv venv .venv_rnaformer --python 3.10
   ```

2. **Install dependencies**:
   ```bash
   uv pip install --python .venv_rnaformer/bin/python -r models/RNAformer/requirements.txt
   ```

3. **Verify installation**:
   ```bash
   source .venv_rnaformer/bin/activate
   python -c "import torch; print('PyTorch version:', torch.__version__)"
   python -c "import transformers; print('Transformers version:', transformers.__version__)"
   ```

4. **Test model**:
   ```bash
   python models/RNAformer/infer_RNAformer.py --help
   ```

### Features

- **Transformer architecture**: Based on advanced Transformer model for RNA secondary structure prediction
- **High accuracy prediction**: Achieves high accuracy in multiple benchmark tests
- **Long sequence support**: Can handle longer RNA sequences
- **Multiple output formats**: Supports dot-bracket and CT format output
- **Pairing information**: Provides detailed pairing index information
- **GPU acceleration**: Supports CUDA acceleration (optional)
- **Memory optimization**: Supports memory-efficient inference mode

## RNAmigos2 Wrapper

### Packaging Method

RNAmigos2 wrapper calls RNAmigos2's Python script through subprocess for RNA-ligand interaction prediction.

**File Location**: `app/utils/wrappers/rnamigos2_wrapper.py`

**Main Class**: `RNAmigos2Wrapper`

### Calling Method

```python
from app.utils.wrappers.rnamigos2_wrapper import RNAmigos2Wrapper

# Initialize wrapper
wrapper = RNAmigos2Wrapper(
    model_path="/path/to/rnamigos2",
    environment_path="/path/to/.venv_rnamigos2"
)

# Predict RNA-ligand interaction
result = wrapper.predict(
    rna_sequences=["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
    smiles_list=["CCOC(=O)C1=C(/C(=C/C2=CC(=C(C=C2)OCCOCCOCCOCCNC(=O)C3=CC(=CC(=C3)NC(=O)NC4=CC=C(C=C4)C5=NCCN5)NC(=O)NC6=CC=C(C=C6)C7=NCCN7)O)/SC1=NC8=CC=CC=C8)O"],
    binding_sites=["A.20", "A.19", "A.18"]
)

# Result format
{
    "success": True,
    "results": [
        {
            "rna_sequence": "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC",
            "smiles": "CCOC(=O)C1=C(/C(=C/C2=CC(=C(C=C2)OCCOCCOCCOCCNC(=O)C3=CC(=CC(=C3)NC(=O)NC4=CC=C(C=C4)C5=NCCN5)NC(=O)NC6=CC=C(C=C6)C7=NCCN7)O)/SC1=NC8=CC=CC=C8)O",
            "binding_sites": "A.20,A.19,A.18",
            "score": 0.85,
            "rank": 1
        }
    ],
    "csv_content": "Rank,SMILES,Score\n1,CCOC(=O)...,0.85",
    "error": None
}
```

### Input Requirements

- **rna_sequences**: List of RNA sequences
- **smiles_list**: List of SMILES strings
- **binding_sites**: List of binding sites (optional)

### Output Format

- **success**: Boolean value indicating whether prediction was successful
- **results**: List of prediction results, includes score and rank fields
- **csv_content**: CSV format result file content
- **error**: Error message (if any)

### Testing Method

```python
# Basic test
def test_rnamigos2_basic():
    wrapper = RNAmigos2Wrapper()
    result = wrapper.predict(
        ["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
        ["CCOC(=O)C1=C(/C(=C/C2=CC(=C(C=C2)OCCOCCOCCOCCNC(=O)C3=CC(=CC(=C3)NC(=O)NC4=CC=C(C=C4)C5=NCCN5)NC(=O)NC6=CC=C(C=C6)C7=NCCN7)O)/SC1=NC8=CC=CC=C8)O"]
    )
    assert result["success"] == True
    assert "score" in result["results"][0]

# Binding sites test
def test_rnamigos2_binding_sites():
    wrapper = RNAmigos2Wrapper()
    result = wrapper.predict(
        ["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"],
        ["CCOC(=O)C1=C(/C(=C/C2=CC(=C(C=C2)OCCOCCOCCOCCNC(=O)C3=CC(=CC(=C3)NC(=O)NC4=CC=C(C=C4)C5=NCCN5)NC(=O)NC6=CC=C(C=C6)C7=NCCN7)O)/SC1=NC8=CC=CC=C8)O"],
        ["A.20", "A.19", "A.18"]
    )
    assert result["success"] == True
    assert result["results"][0]["binding_sites"] == "A.20,A.19,A.18"
```

## Mol2Aptamer Wrapper

### Packaging Method

Mol2Aptamer wrapper calls Mol2Aptamer's Python script through subprocess for RNA aptamer generation from small molecule SMILES.

**File Location**: `app/utils/wrappers/mol2aptamer_wrapper.py`

**Main Class**: `Mol2AptamerWrapper`

### Calling Method

```python
from app.utils.wrappers.mol2aptamer_wrapper import Mol2AptamerWrapper

# Initialize wrapper
wrapper = Mol2AptamerWrapper(
    model_path="/path/to/Mol2Aptamer",
    environment_path="/path/to/.venv_mol2aptamer"
)

# Generate RNA aptamers
result = wrapper.predict(
    smiles="CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C",
    num_sequences=5,
    max_length=40,
    temperature=1.0,
    top_k=50,
    top_p=0.9,
    strategy="greedy"
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GGGCCUUCGCCUCUGGCCCAGCCCUCAC",
            "length": 28,
            "delta_g": -8.5,
            "confidence": 0.85
        }
    ],
    "statistics": {
        "max_length": 35,
        "min_length": 25,
        "avg_length": 30.2,
        "nucleotide_distribution": {"A": 0.25, "C": 0.25, "G": 0.25, "U": 0.25}
    },
    "error": None
}
```

### Input Requirements

- **smiles**: SMILES string of the small molecule
- **num_sequences**: Number of aptamer sequences to generate (1-100)
- **max_length**: Maximum length of generated sequences (10-100)
- **temperature**: Sampling temperature (0.1-2.0)
- **top_k**: Top-k sampling parameter (1-100)
- **top_p**: Top-p sampling parameter (0.1-1.0)
- **strategy**: Generation strategy ("greedy", "sampling")

### Output Format

- **success**: Boolean value indicating whether generation was successful
- **results**: List of generated aptamer sequences with thermodynamic validation
- **statistics**: Summary statistics including length distribution and nucleotide composition
- **error**: Error message (if any)

### Testing Method

```python
# Basic test
def test_mol2aptamer_basic():
    wrapper = Mol2AptamerWrapper()
    result = wrapper.predict("CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C")
    assert result["success"] == True
    assert len(result["results"]) > 0
    assert "delta_g" in result["results"][0]

# Parameter validation test
def test_mol2aptamer_parameters():
    wrapper = Mol2AptamerWrapper()
    result = wrapper.predict(
        "CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C",
        num_sequences=3,
        max_length=30,
        temperature=0.8
    )
    assert result["success"] == True
    assert len(result["results"]) == 3

# Error handling test
def test_mol2aptamer_error():
    wrapper = Mol2AptamerWrapper()
    result = wrapper.predict("INVALID_SMILES")
    assert result["success"] == False
    assert result["error"] is not None
```

## RNAFlow Wrapper

### Packaging Method

RNAFlow wrapper calls RNAFlow's Python script through subprocess for protein-conditioned RNA sequence-structure design.

**File Location**: `app/utils/wrappers/rnaflow_wrapper.py`

**Main Class**: `RNAFlowWrapper`

### Calling Method

```python
from app.utils.wrappers.rnaflow_wrapper import RNAFlowWrapper

# Initialize wrapper
wrapper = RNAFlowWrapper(
    model_path="/path/to/RNAFlow",
    environment_path="/path/to/.venv_rnaflow"
)

# Design RNA sequences and structures
result = wrapper.design_rna(
    protein_sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    rna_length=50,
    num_samples=5
)

# Result format
{
    "success": True,
    "results": [
        {
            "sequence": "GGGCCUUCGCCUCUGGCCCAGCCCUCACGGGCCUUCGCCUCUGGCCCAGCCCUCAC",
            "structure": "(((((((((..(((...)))..))))))))(((((((((..(((...)))..))))))))",
            "confidence": 0.78,
            "length": 50
        }
    ],
    "statistics": {
        "highest_confidence": 0.85,
        "lowest_confidence": 0.72,
        "nucleotide_distribution": {"A": 0.24, "C": 0.26, "G": 0.25, "U": 0.25}
    },
    "error": None
}
```

### Input Requirements

- **protein_sequence**: Protein sequence string
- **rna_length**: Desired RNA sequence length (5-200)
- **num_samples**: Number of samples to generate (1-50)
- **protein_coordinates**: Optional protein coordinates (Tensor)

### Output Format

- **success**: Boolean value indicating whether design was successful
- **results**: List of designed RNA sequences and structures
- **statistics**: Summary statistics including confidence scores and nucleotide composition
- **error**: Error message (if any)

### Testing Method

```python
# Basic test
def test_rnaflow_basic():
    wrapper = RNAFlowWrapper()
    result = wrapper.design_rna(
        "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        rna_length=30,
        num_samples=3
    )
    assert result["success"] == True
    assert len(result["results"]) == 3
    assert "confidence" in result["results"][0]

# Different lengths test
def test_rnaflow_lengths():
    wrapper = RNAFlowWrapper()
    lengths = [20, 40, 60]
    for length in lengths:
        result = wrapper.design_rna(
            "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            rna_length=length,
            num_samples=2
        )
        assert result["success"] == True
        assert all(r["length"] == length for r in result["results"])

# Error handling test
def test_rnaflow_error():
    wrapper = RNAFlowWrapper()
    result = wrapper.design_rna("", rna_length=30, num_samples=1)
    assert result["success"] == False
    assert result["error"] is not None
```

## General Testing Methods

### 1. Unit Testing

```python
import unittest
from app.utils.wrappers import (BPFoldWrapper, UFoldWrapper, MXFold2Wrapper, 
                               RNAformerWrapper, RNAmigos2Wrapper, 
                               Mol2AptamerWrapper, RNAFlowWrapper)

class TestWrappers(unittest.TestCase):
    def setUp(self):
        self.test_sequence = "GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"
        self.test_smiles = "CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C"
        self.test_protein = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    def test_structure_prediction_wrappers(self):
        wrappers = [
            BPFoldWrapper(),
            UFoldWrapper(),
            MXFold2Wrapper(),
            RNAformerWrapper()
        ]
        
        for wrapper in wrappers:
            with self.subTest(wrapper=wrapper.__class__.__name__):
                result = wrapper.predict([self.test_sequence])
                self.assertTrue(result["success"])
                self.assertIsInstance(result["results"], list)
                self.assertGreater(len(result["results"]), 0)
    
    def test_interaction_prediction_wrappers(self):
        wrapper = RNAmigos2Wrapper()
        result = wrapper.predict(
            [self.test_sequence],
            [self.test_smiles],
            ["A.20", "A.19", "A.18"]
        )
        self.assertTrue(result["success"])
        self.assertIsInstance(result["results"], list)
    
    def test_de_novo_design_wrappers(self):
        # Test Mol2Aptamer
        mol2aptamer = Mol2AptamerWrapper()
        result = mol2aptamer.predict(self.test_smiles)
        self.assertTrue(result["success"])
        self.assertIsInstance(result["results"], list)
        
        # Test RNAFlow
        rnaflow = RNAFlowWrapper()
        result = rnaflow.design_rna(self.test_protein, rna_length=30, num_samples=2)
        self.assertTrue(result["success"])
        self.assertIsInstance(result["results"], list)
```

### 2. Integration Testing

```python
def test_wrapper_integration():
    """Test wrapper integration with Flask application"""
    from app import create_app
    
    app = create_app()
    with app.test_client() as client:
        # Test structure prediction
        response = client.post('/api/bpfold/predict', json={
            'sequences': ['GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC']
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        
        # Test interaction prediction
        response = client.post('/api/rnamigos2/predict', json={
            'rna_sequences': ['GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC'],
            'smiles_list': ['CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C'],
            'binding_sites': ['A.20', 'A.19', 'A.18']
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        
        # Test de novo design - Mol2Aptamer
        response = client.post('/api/mol2aptamer/predict', json={
            'smiles': 'CC1=CC2=C(CC1)C(=CC3=C2C(=CO3)C)C',
            'num_sequences': 3,
            'max_length': 30
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        
        # Test de novo design - RNAFlow
        response = client.post('/api/rnaflow/design', json={
            'protein_sequence': 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
            'rna_length': 30,
            'num_samples': 2
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
```

### 3. Performance Testing

```python
import time

def test_wrapper_performance():
    """Test wrapper performance"""
    wrapper = BPFoldWrapper()
    
    start_time = time.time()
    result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
    end_time = time.time()
    
    assert result["success"] == True
    assert (end_time - start_time) < 30  # Complete within 30 seconds
```

### 4. Error Handling Testing

```python
def test_wrapper_error_handling():
    """Test wrapper error handling"""
    wrapper = BPFoldWrapper()
    
    # Test invalid sequence
    result = wrapper.predict(["INVALID_SEQUENCE"])
    assert result["success"] == False
    assert result["error"] is not None
    
    # Test empty sequence
    result = wrapper.predict([])
    assert result["success"] == False
    assert result["error"] is not None
```

## Troubleshooting

### Common Issues

1. **Virtual environment path error**
   ```python
   # Check if virtual environment exists
   import os
   env_path = "/home/huaizhi/Software/.venv_bpfold"
   assert os.path.exists(env_path), f"Virtual environment not found: {env_path}"
   ```

2. **Model path error**
   ```python
   # Check if model path exists
   model_path = "/home/huaizhi/Software/models/BPfold/model_predict"
   assert os.path.exists(model_path), f"Model path not found: {model_path}"
   ```

3. **Missing dependencies**
   ```bash
   # Reinstall dependencies
   source /home/huaizhi/Software/.venv_bpfold/bin/activate
   uv pip install -r requirements.txt
   ```

4. **Permission issues**
   ```bash
   # Check file permissions
   chmod +x /home/huaizhi/Software/.venv_bpfold/bin/python
   ```

### Debugging Methods

1. **Enable verbose logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check temporary files**
   ```python
   wrapper = BPFoldWrapper()
   result = wrapper.predict(["GUGGGGGCUUCGCCUCUGGCCCAGCCCUCAC"])
   print(f"Temporary directory: {wrapper.temp_dir}")
   ```

3. **Manual model testing**
   ```bash
   # Direct model call
   source /home/huaizhi/Software/.venv_bpfold/bin/activate
   python /home/huaizhi/Software/models/BPfold/predict.py --help
   ```

### Performance Optimization

1. **Batch processing**
   ```python
   # Process multiple sequences at once
   result = wrapper.predict(sequences)
   ```

2. **Cache results**
   ```python
   # Use cache to avoid repeated calculations
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def cached_predict(sequence):
       return wrapper.predict([sequence])
   ```

3. **Asynchronous processing**
   ```python
   import asyncio
   
   async def async_predict(sequences):
       # Asynchronously process multiple sequences
       tasks = [wrapper.predict([seq]) for seq in sequences]
       return await asyncio.gather(*tasks)
   ```

## Summary

All wrappers follow a unified design pattern, providing consistent interfaces and error handling mechanisms. Through this document, developers can:

1. Understand the packaging and calling methods of each wrapper
2. Learn how to write test cases
3. Master troubleshooting and performance optimization methods
4. Quickly integrate new model wrappers

It is recommended to follow the existing design patterns when adding new model wrappers to ensure code consistency and maintainability.