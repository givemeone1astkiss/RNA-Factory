"""
RNA Design Agent with Tool Calling Capabilities

This module provides an intelligent agent that can call platform tools
to perform RNA analysis tasks based on user requests.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class RNAAnalysisAgent:
    """Intelligent agent for RNA analysis using platform tools"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """Initialize the RNA Analysis Agent"""
        self.base_url = base_url.rstrip('/')
        self.available_tools = self._initialize_tools()
        self.tool_descriptions = self._get_tool_descriptions()
        
    def _initialize_tools(self) -> Dict[str, Dict[str, Any]]:
        """Initialize available analysis tools"""
        return {
            "bpfold": {
                "name": "BPFold",
                "description": "Deep learning model for RNA secondary structure prediction",
                "endpoint": "/api/bpfold/predict",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "base_pairs", "confidence"],
                "category": "structure_prediction"
            },
            "ufold": {
                "name": "UFold", 
                "description": "Deep learning-based RNA secondary structure prediction using FCNs",
                "endpoint": "/api/ufold/predict",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "ct_format", "bpseq_format"],
                "category": "structure_prediction"
            },
            "mxfold2": {
                "name": "MXFold2",
                "description": "Deep learning-based RNA secondary structure prediction with thermodynamic integration",
                "endpoint": "/api/mxfold2/predict", 
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "dot_bracket", "energy"],
                "category": "structure_prediction"
            },
            "rnaformer": {
                "name": "RNAformer",
                "description": "Deep learning model using 2D latent space and axial attention",
                "endpoint": "/api/rnaformer/predict",
                "input_types": ["fasta", "text"], 
                "output_types": ["secondary_structure", "dot_bracket", "ct_format"],
                "category": "structure_prediction"
            },
            "rnamigos2": {
                "name": "RNAmigos2",
                "description": "Virtual screening tool for RNA-ligand interaction prediction",
                "endpoint": "/api/rnamigos2/predict",
                "input_types": ["mmcif", "smiles"],
                "output_types": ["interaction_scores", "binding_affinity"],
                "category": "interaction_prediction"
            },
            "reformer": {
                "name": "Reformer",
                "description": "Protein-RNA binding affinity prediction at single-base resolution. REQUIRES: RNA sequence, RBP (RNA-binding protein) name, and cell line. Only use when all three parameters are available.",
                "endpoint": "/api/reformer/predict",
                "input_types": ["rna_sequence", "rbp_name", "cell_line"],
                "output_types": ["binding_scores", "affinity_prediction"],
                "category": "interaction_prediction",
                "required_params": ["rna_sequence", "rbp_name", "cell_line"]
            },
            "copra": {
                "name": "CoPRA",
                "description": "Protein-RNA binding affinity prediction using language models",
                "endpoint": "/api/copra/predict",
                "input_types": ["protein_sequence", "rna_sequence"],
                "output_types": ["binding_affinity", "confidence_score"],
                "category": "interaction_prediction"
            },
            "deeprpi": {
                "name": "DeepRPI",
                "description": "Deep learning-based RNA-protein interaction prediction",
                "endpoint": "/api/deeprpi/predict",
                "input_types": ["protein_sequence", "rna_sequence"],
                "output_types": ["interaction_prediction", "probability", "attention_maps"],
                "category": "interaction_prediction"
            },
            "mol2aptamer": {
                "name": "Mol2Aptamer",
                "description": "Generate RNA aptamers from small molecule SMILES",
                "endpoint": "/api/mol2aptamer/predict",
                "input_types": ["smiles"],
                "output_types": ["rna_sequences", "aptamer_candidates"],
                "category": "de_novo_design"
            },
            "rnaflow": {
                "name": "RNAFlow",
                "description": "Protein-conditioned RNA sequence-structure design",
                "endpoint": "/api/rnaflow/predict",
                "input_types": ["protein_sequence", "protein_coordinates", "rna_length"],
                "output_types": ["rna_sequences", "rna_structures"],
                "category": "de_novo_design"
            },
            "rnaframeflow": {
                "name": "RNA-FrameFlow",
                "description": "3D RNA backbone structure design using SE(3) flow matching",
                "endpoint": "/api/rnaframeflow/predict",
                "input_types": ["structure_length", "num_structures"],
                "output_types": ["rna_structures", "3d_coordinates", "pdb_files"],
                "category": "de_novo_design"
            },
            "ribodiffusion": {
                "name": "RiboDiffusion",
                "description": "RNA inverse folding from protein structures using diffusion",
                "endpoint": "/api/ribodiffusion/predict",
                "input_types": ["pdb"],
                "output_types": ["rna_sequences", "fasta_files"],
                "category": "de_novo_design"
            },
            "rnampnn": {
                "name": "RNAMPNN",
                "description": "RNA sequence recovery from 3D structure using graph neural networks",
                "endpoint": "/api/rnampnn/predict",
                "input_types": ["pdb"],
                "output_types": ["rna_sequence", "confidence_scores"],
                "category": "de_novo_design"
            }
        }
    
    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for LLM"""
        descriptions = []
        for tool_id, tool_info in self.available_tools.items():
            desc = f"- {tool_info['name']} ({tool_id}): {tool_info['description']}"
            desc += f"\n  Input types: {', '.join(tool_info['input_types'])}"
            desc += f"\n  Output types: {', '.join(tool_info['output_types'])}"
            desc += f"\n  Category: {tool_info['category']}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def analyze_request(self, user_request: str, uploaded_files: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze user request and determine appropriate tools to use"""
        try:
            # Extract RNA sequences from uploaded files
            sequences_from_files = self._extract_sequences_from_files(uploaded_files or [])
            
            # Extract sequences from user request text
            sequences_from_text = self._extract_sequences_from_text(user_request)
            
            # Combine all sequences (for backward compatibility)
            all_sequences = sequences_from_files + sequences_from_text.get('rna', [])
            
            # Determine analysis type based on request and available data
            analysis_plan = self._create_analysis_plan(user_request, all_sequences, uploaded_files)
            
            return {
                "success": True,
                "analysis_plan": analysis_plan,
                "extracted_sequences": all_sequences,
                "extracted_sequences_detailed": sequences_from_text,  # Include detailed sequence info
                "recommended_tools": analysis_plan.get("tools", []),
                "reasoning": analysis_plan.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Request analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_plan": {"tools": [], "reasoning": "Analysis failed"}
            }
    
    def _extract_sequences_from_files(self, files: List[Dict[str, Any]]) -> List[str]:
        """Extract RNA sequences from uploaded files"""
        sequences = []
        
        for file_info in files:
            if file_info.get("type") == "text/plain" or file_info.get("name", "").endswith(('.txt', '.fasta', '.fa')):
                content = file_info.get("content", "")
                # Extract sequences from FASTA format
                if content.startswith('>'):
                    lines = content.split('\n')
                    sequence = ""
                    for line in lines:
                        if not line.startswith('>') and line.strip():
                            sequence += line.strip()
                    if sequence:
                        sequences.append(sequence)
                else:
                    # Treat as plain text sequence
                    cleaned = ''.join(c for c in content if c.upper() in 'ATCGU')
                    if cleaned:
                        sequences.append(cleaned)
        
        return sequences
    
    def _extract_sequences_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract protein and RNA sequences from user request text"""
        import re
        sequences = {
            'rna': [],
            'protein': []
        }
        
        # Look for RNA sequences
        rna_patterns = [
            r'RNA[:\s]+([AUCG]+)',  # "RNA: AGUCGAUGCAUGUCAGUAGCUCAGCUAGUACUGCGUAGCUA"
            r'RNA sequence[:\s]+([AUCG]+)',  # "RNA sequence: AGUCGAUGCAUGUCAGUAGCUCAGCUAGUACUGCGUAGCUA"
            r'["\']([AUCG]+)["\']',  # "AGUCGAUGCAUGUCAGUAGCUCAGCUAGUACUGCGUAGCUA"
            r'([AUCG]{10,})',  # Any sequence of 10+ RNA bases
        ]
        
        for pattern in rna_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the sequence (remove any non-RNA characters)
                clean_seq = ''.join(c.upper() for c in match if c.upper() in 'AUCG')
                if len(clean_seq) >= 10:  # Only consider sequences of 10+ bases
                    sequences['rna'].append(clean_seq)
        
        # Look for protein sequences
        protein_patterns = [
            r'protein sequence[:\s]+([A-Z]+)',  # "protein sequence: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            r'protein[:\s]+([A-Z]{20,})',  # "protein: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            r'([A-Z]{20,})',  # Any sequence of 20+ amino acids
        ]
        
        for pattern in protein_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the sequence (remove any non-amino acid characters)
                clean_seq = ''.join(c.upper() for c in match if c.upper() in 'ACDEFGHIKLMNPQRSTVWY')
                if len(clean_seq) >= 20:  # Only consider sequences of 20+ amino acids
                    sequences['protein'].append(clean_seq)
        
        # Remove duplicates while preserving order
        for seq_type in sequences:
            seen = set()
            unique_sequences = []
            for seq in sequences[seq_type]:
                if seq not in seen:
                    seen.add(seq)
                    unique_sequences.append(seq)
            sequences[seq_type] = unique_sequences
        
        return sequences
    
    def _create_analysis_plan(self, request: str, sequences: List[str], files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create analysis plan based on user request and available data"""
        request_lower = request.lower()
        tools = []
        reasoning = []
        
        # Check for structure prediction requests
        if any(keyword in request_lower for keyword in ['structure', 'fold', 'secondary', 'base pair', 'helix']):
            if sequences:
                tools.extend(['bpfold', 'ufold', 'mxfold2', 'rnaformer'])
                reasoning.append("RNA sequences detected for structure prediction")
            else:
                reasoning.append("Structure prediction requested but no sequences provided")
        
        # Check for interaction prediction requests
        if any(keyword in request_lower for keyword in ['interaction', 'binding', 'protein', 'ligand', 'affinity']):
            if any(f.get("name", "").endswith('.cif') for f in files or []):
                tools.append('rnamigos2')
                reasoning.append("mmCIF structure file detected for ligand interaction analysis")
            if sequences:
                # Only add tools that can work with available data
                tools.extend(['copra', 'deeprpi'])
                reasoning.append("Sequences available for protein-RNA interaction analysis")
                
                # Check if we have specific RBP and cell line information for Reformer
                if any(keyword in request_lower for keyword in ['rbp', 'rna-binding protein', 'u2af2', 'hepg2', 'cell line', 'specific protein']):
                    tools.append('reformer')
                    reasoning.append("RBP and cell line information detected for Reformer analysis")
        
        # Check for design requests
        if any(keyword in request_lower for keyword in ['design', 'generate', 'create', 'aptamer', 'backbone']):
            if any('smiles' in f.get("name", "").lower() for f in files or []):
                tools.append('mol2aptamer')
                reasoning.append("SMILES file detected for aptamer generation")
            if any(f.get("name", "").endswith('.pdb') for f in files or []):
                tools.extend(['ribodiffusion', 'rnampnn'])
                reasoning.append("PDB structure file detected for RNA design")
            if any(keyword in request_lower for keyword in ['protein', 'conditioned']):
                tools.append('rnaflow')
                reasoning.append("Protein-conditioned RNA design requested")
            if any(keyword in request_lower for keyword in ['3d', 'backbone', 'structure']):
                tools.append('rnaframeflow')
                reasoning.append("3D structure design requested")
        
        # If no specific tools identified, suggest general analysis
        if not tools and sequences:
            tools = ['bpfold', 'ufold']
            reasoning.append("General RNA analysis with available sequences")
        
        return {
            "tools": tools,
            "reasoning": "; ".join(reasoning) if reasoning else "No specific analysis identified",
            "data_available": {
                "sequences": len(sequences),
                "files": len(files or []),
                "sequence_types": list(set(self._get_sequence_types(sequences)))
            }
        }
    
    def _get_sequence_types(self, sequences: List[str]) -> List[str]:
        """Determine types of sequences"""
        types = []
        for seq in sequences:
            if all(c.upper() in 'ATCG' for c in seq):
                types.append('DNA')
            elif all(c.upper() in 'AUCG' for c in seq):
                types.append('RNA')
            else:
                types.append('Mixed')
        return types
    
    def execute_analysis(self, analysis_plan: Dict[str, Any], sequences: List[str], files: List[Dict[str, Any]] = None, detailed_sequences: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Execute the analysis plan using appropriate tools"""
        try:
            results = {
                "success": True,
                "tool_results": {},
                "summary": "",
                "errors": []
            }
            
            tools_to_use = analysis_plan.get("tools", [])
            if not tools_to_use:
                return {
                    "success": False,
                    "error": "No tools identified for analysis",
                    "tool_results": {},
                    "summary": "No analysis tools could be determined from the request"
                }
            
            # Execute each tool
            for tool_id in tools_to_use:
                if tool_id in self.available_tools:
                    try:
                        tool_result = self._call_tool(tool_id, sequences, files or [], detailed_sequences)
                        results["tool_results"][tool_id] = tool_result
                    except Exception as e:
                        error_msg = f"Tool {tool_id} failed: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
            
            # Generate summary
            results["summary"] = self._generate_summary(results["tool_results"], analysis_plan)
            
            return results
            
        except Exception as e:
            logger.error(f"Analysis execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_results": {},
                "summary": "Analysis execution failed"
            }
    
    def _call_tool(self, tool_id: str, sequences: List[str], files: List[Dict[str, Any]], detailed_sequences: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Call a specific analysis tool"""
        tool_info = self.available_tools[tool_id]
        endpoint = f"{self.base_url}{tool_info['endpoint']}"
        
        # Prepare request data based on tool requirements
        request_data = self._prepare_tool_request(tool_id, sequences, files, detailed_sequences)
        
        try:
            response = requests.post(
                endpoint,
                json=request_data,
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "tool_name": tool_info["name"],
                    "category": tool_info["category"]
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "tool_name": tool_info["name"]
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout - analysis took too long",
                "tool_name": tool_info["name"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_info["name"]
            }
    
    def _prepare_tool_request(self, tool_id: str, sequences: List[str], files: List[Dict[str, Any]], detailed_sequences: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Prepare request data for specific tool"""
        request_data = {}
        
        if tool_id in ['bpfold', 'ufold', 'mxfold2', 'rnaformer']:
            # Structure prediction tools
            if sequences:
                request_data = {
                    "sequences": sequences,
                    "input_type": "text"
                }
                # Specify output format for BPFold to get dot-bracket notation
                if tool_id == 'bpfold':
                    request_data["output_format"] = "dbn"
            else:
                # Use file data if available
                for file_info in files:
                    if file_info.get("type") == "text/plain":
                        request_data = {
                            "sequences": [file_info.get("content", "")],
                            "input_type": "text"
                        }
                        break
        
        elif tool_id == 'rnamigos2':
            # RNA-ligand interaction tool
            for file_info in files:
                if file_info.get("name", "").endswith('.cif'):
                    request_data = {
                        "structure_file": file_info.get("content", ""),
                        "ligands": ["C1=CC=CC=C1"]  # Default benzene for testing
                    }
                    break
        
        elif tool_id == 'reformer':
            # Reformer tool - needs DNA sequence
            if sequences:
                # Use detailed sequences if available, otherwise fall back to basic extraction
                if detailed_sequences:
                    rna_sequence = detailed_sequences.get('rna', [sequences[0] if sequences else ""])[0]
                else:
                    rna_sequence = sequences[0] if sequences else ""
                
                # Convert RNA to DNA for Reformer
                dna_sequence = rna_sequence.replace('U', 'T')
                request_data = {
                    "sequence": dna_sequence,
                    "rbp_name": "U2AF2",
                    "cell_line": "HepG2"
                }
        
        elif tool_id in ['copra', 'deeprpi']:
            # CoPRA and DeepRPI tools - need both protein and RNA sequences
            if sequences:
                # Use detailed sequences if available, otherwise fall back to basic extraction
                if detailed_sequences:
                    rna_sequence = detailed_sequences.get('rna', [sequences[0] if sequences else ""])[0]
                    protein_sequence = detailed_sequences.get('protein', ["MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"])[0]
                else:
                    rna_sequence = sequences[0] if sequences else ""
                    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
                
                request_data = {
                    "rna_sequence": rna_sequence,
                    "protein_sequence": protein_sequence
                }
        
        elif tool_id == 'mol2aptamer':
            # Aptamer generation
            for file_info in files:
                if 'smiles' in file_info.get("name", "").lower():
                    request_data = {
                        "smiles": file_info.get("content", ""),
                        "num_sequences": 5
                    }
                    break
        
        elif tool_id == 'rnaflow':
            # Protein-conditioned RNA design
            request_data = {
                "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "rna_length": 50
            }
        
        elif tool_id == 'rnaframeflow':
            # 3D structure design
            request_data = {
                "structure_length": 30,
                "num_structures": 3
            }
        
        elif tool_id in ['ribodiffusion', 'rnampnn']:
            # Structure-based design
            for file_info in files:
                if file_info.get("name", "").endswith('.pdb'):
                    request_data = {
                        "pdb_content": file_info.get("content", "")
                    }
                    break
        
        return request_data
    
    def _generate_summary(self, tool_results: Dict[str, Any], analysis_plan: Dict[str, Any]) -> str:
        """Generate a summary of analysis results"""
        successful_tools = [tool for tool, result in tool_results.items() if result.get("success", False)]
        failed_tools = [tool for tool, result in tool_results.items() if not result.get("success", False)]
        
        summary_parts = []
        
        if successful_tools:
            summary_parts.append(f"Successfully completed analysis using: {', '.join(successful_tools)}")
            
            # Add specific results for each tool
            for tool in successful_tools:
                result = tool_results[tool]
                tool_name = result.get("tool_name", tool)
                category = result.get("category", "unknown")
                summary_parts.append(f"- {tool_name} ({category}): Analysis completed")
        
        if failed_tools:
            summary_parts.append(f"Failed tools: {', '.join(failed_tools)}")
        
        if not tool_results:
            summary_parts.append("No analysis tools were executed")
        
        return "\n".join(summary_parts)
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get information about available tools"""
        return {
            "tools": self.available_tools,
            "descriptions": self.tool_descriptions,
            "categories": {
                "structure_prediction": [tool for tool, info in self.available_tools.items() 
                                       if info["category"] == "structure_prediction"],
                "interaction_prediction": [tool for tool, info in self.available_tools.items() 
                                         if info["category"] == "interaction_prediction"],
                "de_novo_design": [tool for tool, info in self.available_tools.items() 
                                  if info["category"] == "de_novo_design"]
            }
        }
