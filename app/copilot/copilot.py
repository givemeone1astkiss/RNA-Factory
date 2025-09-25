"""
LangGraph-based RNA Design Assistant

AI assistant using LangGraph for RNA design tasks with multimodal RAG support.
"""

import json
import logging
from typing import Dict, Any, List, TypedDict, Annotated
from operator import add
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .prompts import (
    RNA_DESIGN_SYSTEM_PROMPT,
    GENERAL_BIOINFO_SYSTEM_PROMPT,
    QUERY_CLASSIFICATION_PROMPT,
    OFF_TOPIC_REDIRECTION,
    RESPONSE_TEMPLATES,
    CAPABILITIES,
    RESPONSE_TYPES,
    TOOL_DESCRIPTIONS
)
from .rag import RNADesignRAGSystem
from .agent import RNAAnalysisAgent

logger = logging.getLogger(__name__)


class AssistantState(TypedDict):
    """State for the RNA Design Assistant"""
    messages: Annotated[List, add_messages]
    response_type: str  # 'rna_design', 'general_bioinfo', 'off_topic'
    confidence: float
    tools_used: Annotated[List[str], add]
    rag_context: str  # RAG context from documents
    citations: Annotated[List[Dict[str, Any]], add]  # Citations and references
    uploaded_files: List[Dict[str, Any]]  # Uploaded files for analysis
    agent_analysis: Dict[str, Any]  # Agent analysis results


class RNADesignAssistant:
    """LangGraph-based RNA Design Assistant"""
    
    def __init__(self, api_key: str, api_base: str = "https://api.deepseek.com", 
                 data_directory: str = "data", multimodal: bool = True):
        """Initialize the RNA Design Assistant"""
        self.api_key = api_key
        self.api_base = api_base
        self.llm = self._initialize_llm()
        self.multimodal = multimodal
        
        # Initialize conversation memory
        self.conversation_memory = []
        self.max_memory_length = 10  # Keep last 10 exchanges
        
        # Initialize streaming control
        self.streaming_active = False
        self.stop_streaming = False
        
        # Initialize RAG system - automatically load documents from data directory
        try:
            self.rag_system = RNADesignRAGSystem(data_directory=data_directory)
            # Automatically process all PDF and Markdown files in the data directory
            processed_count = self.rag_system.add_documents_from_directory()
            # Initialized RAG system
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            raise
        
        # Initialize RNA Analysis Agent
        try:
            self.analysis_agent = RNAAnalysisAgent()
            logger.info("RNA Analysis Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RNA Analysis Agent: {e}")
            self.analysis_agent = None
        
        # Ensure building state is properly set after initialization
        if hasattr(self.rag_system, 'is_building'):
            # Force the building state to false after initialization
            self.rag_system.is_building = False
            # RAG system initialization completed
        
        self.graph = self._build_graph()
    
    def _add_to_memory(self, user_message: str, ai_response: str):
        """Add conversation exchange to memory"""
        self.conversation_memory.append({
            "user": user_message,
            "assistant": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only the last max_memory_length exchanges
        if len(self.conversation_memory) > self.max_memory_length:
            self.conversation_memory = self.conversation_memory[-self.max_memory_length:]
    
    def _get_conversation_context(self) -> str:
        """Get recent conversation context for the LLM"""
        if not self.conversation_memory:
            return ""
        
        context_parts = ["Recent conversation:"]
        for exchange in self.conversation_memory[-3:]:  # Last 3 exchanges
            context_parts.append(f"User: {exchange['user']}")
            context_parts.append(f"Assistant: {exchange['assistant']}")
        
        return "\n".join(context_parts)
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.conversation_memory = []
        # Conversation memory cleared
    
    def stop_current_stream(self):
        """Stop the current streaming response"""
        if self.streaming_active:
            self.stop_streaming = True
            # Stop streaming requested
        
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize DeepSeek LLM using ChatOpenAI"""
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=f"{self.api_base}/v1",
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=2000,
            streaming=True
        )
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AssistantState)
        
        # Add nodes
        workflow.add_node("classify_query", self._classify_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("agent_analysis", self._agent_analysis)
        workflow.add_node("rna_design_expert", self._rna_design_expert)
        workflow.add_node("general_bioinfo", self._general_bioinfo)
        workflow.add_node("off_topic_handler", self._off_topic_handler)
        workflow.add_node("response_formatter", self._format_response)
        
        # Add edges with conditional routing
        workflow.add_edge("classify_query", "retrieve_context")
        workflow.add_conditional_edges(
            "retrieve_context",
            self._route_query,
            {
                "rna_design": "agent_analysis",
                "general_bioinfo": "agent_analysis", 
                "off_topic": "off_topic_handler",
            },
        )
        workflow.add_conditional_edges(
            "agent_analysis",
            self._route_after_agent,
            {
                "rna_design": "rna_design_expert",
                "general_bioinfo": "general_bioinfo",
                "off_topic": "off_topic_handler",
            },
        )
        workflow.add_edge("rna_design_expert", "response_formatter")
        workflow.add_edge("general_bioinfo", "response_formatter")
        workflow.add_edge("off_topic_handler", "response_formatter")
        workflow.add_edge("response_formatter", END)
        
        # Set entry point
        workflow.set_entry_point("classify_query")
        
        return workflow.compile()
    
    def _classify_query(self, state: AssistantState) -> AssistantState:
        """Classify the user query to determine response type"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        # Use the classification prompt from prompts.py
        classification_prompt = QUERY_CLASSIFICATION_PROMPT.format(query=last_message)
        
        try:
            response = self.llm.invoke([HumanMessage(content=classification_prompt)])
            category = response.content.strip().lower()
            
            # Validate category
            if category not in ["rna_design", "general_bioinfo", "off_topic"]:
                category = "off_topic"
                
            state["response_type"] = category
            state["confidence"] = 0.9 if category == "rna_design" else 0.7
            
        except Exception as e:
            logger.error(f"Query classification failed: {e}")
            state["response_type"] = "off_topic"
            state["confidence"] = 0.5
            
        return state
    
    def _retrieve_context(self, state: AssistantState) -> AssistantState:
        """Retrieve relevant context from documents using RAG"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        try:
            # Get RAG context and citations - automatically use documents from data directory
            if self.multimodal and hasattr(self.rag_system, 'get_multimodal_context'):
                rag_context, citations = self.rag_system.get_multimodal_context(
                    last_message, max_text_chunks=15, max_images=5
                )
            else:
                rag_context, citations = self.rag_system.get_rag_context(last_message, max_chunks=15)
            
            # RAG retrieval completed
            
            # Check if we have meaningful context
            # Very permissive threshold - accept any citations with reasonable scores
            has_literature = (
                len(citations) > 0 and
                any(citation.get("score", 0) > -0.5 for citation in citations)  # Accept even negative similarities
            )
            
            # Additional check: if we have any context at all, consider it literature
            if not has_literature and rag_context and rag_context != "No relevant documents found.":
                has_literature = True
                # RAG context found but no citations - still considering as literature
            
            # Final fallback: if we have any citations at all, consider it literature
            if not has_literature and len(citations) > 0:
                has_literature = True
                # Found citations with low scores - still considering as literature
            
            # Update state with RAG context
            state["rag_context"] = rag_context
            state["citations"] = citations
            state["has_literature"] = has_literature
            
            # Final RAG decision made
            
        except Exception as e:
            logger.error(f"RAG context retrieval failed: {e}")
            state["rag_context"] = "No relevant documents found."
            state["citations"] = []
            state["has_literature"] = False
        
        return state
    
    def _route_query(self, state: AssistantState) -> str:
        """Route the query based on classification"""
        response_type = state.get("response_type", "off_topic")
        logger.info(f"Routing query to: {response_type}")
        return response_type
    
    def _route_after_agent(self, state: AssistantState) -> str:
        """Route after agent analysis based on original classification"""
        response_type = state.get("response_type", "off_topic")
        logger.info(f"Routing after agent analysis to: {response_type}")
        return response_type
    
    def _agent_analysis(self, state: AssistantState) -> AssistantState:
        """Perform agent analysis using platform tools"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        uploaded_files = state.get("uploaded_files", [])
        
        # Check if we have uploaded files or if the request suggests tool usage
        should_use_agent = self._should_use_agent(last_message)
        logger.info(f"Agent analysis check - uploaded_files: {len(uploaded_files)}, should_use_agent: {should_use_agent}")
        if uploaded_files:
            logger.info(f"Uploaded files details: {[f.get('name', 'Unknown') for f in uploaded_files]}")
        
        if not uploaded_files and not should_use_agent:
            # No files and no clear tool usage request, skip agent analysis
            state["agent_analysis"] = {"skipped": True, "reason": "No files or tool usage detected"}
            return state
        
        if not self.analysis_agent:
            state["agent_analysis"] = {"error": "Analysis agent not available"}
            return state
        
        try:
            # Analyze the request and determine tools to use
            analysis_result = self.analysis_agent.analyze_request(last_message, uploaded_files)
            
            if analysis_result["success"] and analysis_result.get("recommended_tools"):
                # Execute the analysis
                execution_result = self.analysis_agent.execute_analysis(
                    analysis_result["analysis_plan"],
                    analysis_result["extracted_sequences"],
                    uploaded_files,
                    analysis_result.get("extracted_sequences_detailed")
                )
                
                state["agent_analysis"] = {
                    "success": True,
                    "analysis_plan": analysis_result["analysis_plan"],
                    "execution_result": execution_result,
                    "tools_used": analysis_result["recommended_tools"],
                    "extracted_sequences_detailed": analysis_result.get("extracted_sequences_detailed", {})
                }
                state["tools_used"].extend(analysis_result["recommended_tools"])
            else:
                state["agent_analysis"] = {
                    "success": False,
                    "reason": "No suitable tools identified",
                    "analysis_plan": analysis_result.get("analysis_plan", {})
                }
                
        except Exception as e:
            logger.error(f"Agent analysis failed: {e}")
            state["agent_analysis"] = {
                "success": False,
                "error": str(e)
            }
        
        return state
    
    def _should_use_agent(self, message: str) -> bool:
        """Determine if the message suggests using agent tools"""
        message_lower = message.lower()
        tool_keywords = [
            'analyze', 'predict', 'structure', 'fold', 'interaction', 'binding',
            'design', 'generate', 'create', 'aptamer', 'backbone', 'sequence',
            'protein', 'ligand', 'affinity', 'smiles', 'pdb', 'cif'
        ]
        found_keywords = [keyword for keyword in tool_keywords if keyword in message_lower]
        logger.info(f"Agent detection - Message: '{message_lower}', Found keywords: {found_keywords}")
        return len(found_keywords) > 0
    
    def _rna_design_expert(self, state: AssistantState) -> AssistantState:
        """Handle RNA design specific queries with expert knowledge"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        # Check if we have literature support
        has_literature = state.get("has_literature", False)
        
        # Check if we have agent analysis results
        agent_analysis = state.get("agent_analysis", {})
        
        if not has_literature and not agent_analysis.get("success", False):
            # Use the literature reference required message
            from .prompts import LITERATURE_REFERENCE_REQUIRED
            response_content = LITERATURE_REFERENCE_REQUIRED.format(query=last_message)
            state["messages"].append(AIMessage(content=response_content))
            state["tools_used"].append("rna_design_expert")
            return state
        
        # Build context including RAG context and agent analysis
        context = self._build_rna_context(state)
        rag_context = state.get("rag_context", "")
        
        # Add agent analysis results to context
        if agent_analysis.get("success", False):
            execution_result = agent_analysis.get("execution_result", {})
            if execution_result.get("success", False):
                context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                
                # Add specific tool results
                tool_results = execution_result.get("tool_results", {})
                for tool_name, result in tool_results.items():
                    if result.get("success", False):
                        context += f"\n{tool_name.upper()} RESULTS:\n"
                        context += f"Status: Success\n"
                        context += f"Category: {result.get('category', 'Unknown')}\n"
                        
                        # Add specific data from the tool
                        data = result.get("data", {})
                        if isinstance(data, dict):
                            # Handle RNA secondary structure prediction tools
                            if tool_name in ['bpfold', 'ufold', 'mxfold2', 'rnaformer']:
                                if "results" in data and data["results"]:
                                    structure_result = data["results"][0]
                                    sequence = structure_result.get("sequence", "")
                                    
                                    # Extract dot-bracket notation if available
                                    dot_bracket = None
                                    if "structure" in structure_result:
                                        dot_bracket = structure_result["structure"]
                                    elif "dot_bracket" in structure_result:
                                        dot_bracket = structure_result["dot_bracket"]
                                    elif "data" in structure_result and not structure_result["data"].startswith("1 "):
                                        # Only use data field if it's not CT format (which starts with "1 ")
                                        dot_bracket = structure_result["data"]
                                    
                                    if dot_bracket:
                                        context += f"Secondary Structure (dot-bracket): {dot_bracket}\n"
                                    
                                    # Extract CT data if available
                                    if "ct_data" in structure_result:
                                        ct_data = structure_result["ct_data"]
                                        context += f"CT Format Data:\n{ct_data}\n"
                                    
                                    # Extract energy information if available
                                    if "energy" in structure_result:
                                        energy = structure_result["energy"]
                                        context += f"Free Energy: {energy} kcal/mol\n"
                                    
                                    context += f"Sequence: {sequence}\n"
                                    context += f"Length: {len(sequence)} nucleotides\n"
                                    
                            # Handle protein-RNA interaction tools
                            elif "binding_scores" in data:
                                scores = data["binding_scores"]
                                context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                            elif "prediction" in data:
                                pred = data["prediction"]
                                if isinstance(pred, dict) and "binding_affinity" in pred:
                                    context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                else:
                                    context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                            else:
                                context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                    else:
                        context += f"\n{tool_name.upper()} RESULTS:\n"
                        context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
        
        # Enhance context with RAG information
        if rag_context and rag_context != "No relevant documents found.":
            # Add RAG context with clear instructions
            context += f"\n\nCRITICAL: You have access to relevant literature. Use the following information to answer the user's question. DO NOT say 'no relevant literature found' - use the provided literature:\n\n{rag_context}"
        
        # Use the RNA design system prompt from prompts.py
        system_prompt = RNA_DESIGN_SYSTEM_PROMPT.format(context=context)
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=last_message)
            ])
            
            state["messages"].append(AIMessage(content=response.content))
            state["tools_used"].append("rna_design_expert")
            
        except Exception as e:
            logger.error(f"RNA design expert failed: {e}")
            state["messages"].append(AIMessage(content=RESPONSE_TEMPLATES["error_message"]))
            
        return state
    
    def _general_bioinfo(self, state: AssistantState) -> AssistantState:
        """Handle general bioinformatics queries that might be relevant to RNA work"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        # Check if we have literature support
        has_literature = state.get("has_literature", False)
        
        # Check if we have agent analysis results
        agent_analysis = state.get("agent_analysis", {})
        
        if not has_literature and not agent_analysis.get("success", False):
            # Use the literature reference required message
            from .prompts import LITERATURE_REFERENCE_REQUIRED
            response_content = LITERATURE_REFERENCE_REQUIRED.format(query=last_message)
            state["messages"].append(AIMessage(content=response_content))
            state["tools_used"].append("general_bioinfo")
            return state
        
        # Build context including RAG context and agent analysis
        context = self._build_general_context(state)
        rag_context = state.get("rag_context", "")
        
        # Add agent analysis results to context
        if agent_analysis.get("success", False):
            execution_result = agent_analysis.get("execution_result", {})
            if execution_result.get("success", False):
                context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                
                # Add specific tool results
                tool_results = execution_result.get("tool_results", {})
                for tool_name, result in tool_results.items():
                    if result.get("success", False):
                        context += f"\n{tool_name.upper()} RESULTS:\n"
                        context += f"Status: Success\n"
                        context += f"Category: {result.get('category', 'Unknown')}\n"
                        
                        # Add specific data from the tool
                        data = result.get("data", {})
                        if isinstance(data, dict):
                            # Handle RNA secondary structure prediction tools
                            if tool_name in ['bpfold', 'ufold', 'mxfold2', 'rnaformer']:
                                if "results" in data and data["results"]:
                                    structure_result = data["results"][0]
                                    sequence = structure_result.get("sequence", "")
                                    
                                    # Extract dot-bracket notation if available
                                    dot_bracket = None
                                    if "structure" in structure_result:
                                        dot_bracket = structure_result["structure"]
                                    elif "dot_bracket" in structure_result:
                                        dot_bracket = structure_result["dot_bracket"]
                                    elif "data" in structure_result and not structure_result["data"].startswith("1 "):
                                        # Only use data field if it's not CT format (which starts with "1 ")
                                        dot_bracket = structure_result["data"]
                                    
                                    if dot_bracket:
                                        context += f"Secondary Structure (dot-bracket): {dot_bracket}\n"
                                    
                                    # Extract CT data if available
                                    if "ct_data" in structure_result:
                                        ct_data = structure_result["ct_data"]
                                        context += f"CT Format Data:\n{ct_data}\n"
                                    
                                    # Extract energy information if available
                                    if "energy" in structure_result:
                                        energy = structure_result["energy"]
                                        context += f"Free Energy: {energy} kcal/mol\n"
                                    
                                    context += f"Sequence: {sequence}\n"
                                    context += f"Length: {len(sequence)} nucleotides\n"
                                    
                            # Handle protein-RNA interaction tools
                            elif "binding_scores" in data:
                                scores = data["binding_scores"]
                                context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                            elif "prediction" in data:
                                pred = data["prediction"]
                                if isinstance(pred, dict) and "binding_affinity" in pred:
                                    context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                else:
                                    context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                            else:
                                context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                    else:
                        context += f"\n{tool_name.upper()} RESULTS:\n"
                        context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
        
        # Enhance context with RAG information
        if rag_context and rag_context != "No relevant documents found.":
            # Add RAG context with clear instructions
            context += f"\n\nCRITICAL: You have access to relevant literature. Use the following information to answer the user's question. DO NOT say 'no relevant literature found' - use the provided literature:\n\n{rag_context}"
        
        # Use the general bioinfo system prompt from prompts.py
        system_prompt = GENERAL_BIOINFO_SYSTEM_PROMPT.format(context=context)
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=last_message)
            ])
            
            state["messages"].append(AIMessage(content=response.content))
            state["tools_used"].append("general_bioinfo")
            
        except Exception as e:
            logger.error(f"General bioinfo failed: {e}")
            state["messages"].append(AIMessage(content=RESPONSE_TEMPLATES["error_message"]))
            
        return state
    
    def _off_topic_handler(self, state: AssistantState) -> AssistantState:
        """Handle off-topic queries by redirecting to RNA design"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        # Use the off-topic redirection message from prompts.py
        redirection_message = OFF_TOPIC_REDIRECTION.format(query=last_message)
        
        state["messages"].append(AIMessage(content=redirection_message))
        state["tools_used"].append("off_topic_handler")
        
        return state
    
    def _format_response(self, state: AssistantState) -> AssistantState:
        """Format the final response with citations"""
        messages = state["messages"]
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                # Get citations
                citations = state.get("citations", [])
                
                # Format response with citations
                response_content = last_message.content
                
                # Citations removed as requested
                
                # Metadata removed as requested
                
                state["messages"][-1] = AIMessage(content=response_content)
        
        return state
    
    def _build_rna_context(self, state: AssistantState) -> str:
        """Build context string for RNA design queries"""
        context_parts = []
        
        # Add user context if available
        if state.get("user_context"):
            for key, value in state["user_context"].items():
                context_parts.append(f"{key}: {value}")
        
        # Add uploaded files information with detailed context
        uploaded_files = state.get("uploaded_files", [])
        if uploaded_files:
            context_parts.append("=== UPLOADED FILES ===")
            for i, file_info in enumerate(uploaded_files, 1):
                file_name = file_info.get('name', 'Unknown')
                file_type = file_info.get('type', 'Unknown type')
                file_size = file_info.get('size', 0)
                temp_path = file_info.get('temp_path', '')
                file_id = file_info.get('id', '')
                
                context_parts.append(f"File {i}: {file_name}")
                context_parts.append(f"  - Type: {file_type}")
                context_parts.append(f"  - Size: {file_size} bytes")
                context_parts.append(f"  - ID: {file_id}")
                context_parts.append(f"  - Storage Path: {temp_path}")
                
                # Add file content preview for text files
                if file_info.get('content'):
                    content = file_info['content'].strip()
                    if content:
                        # Show first 200 characters for preview
                        preview = content[:200] + "..." if len(content) > 200 else content
                        context_parts.append(f"  - Content Preview: {preview}")
                
                # Add specific file type analysis
                if file_name.lower().endswith('.pdb'):
                    context_parts.append(f"  - Analysis: This is a PDB structure file that can be used for RNA design tools like RiboDiffusion and RNAMPNN")
                elif file_name.lower().endswith(('.fasta', '.fa')):
                    context_parts.append(f"  - Analysis: This is a FASTA sequence file that can be used for structure prediction tools")
                elif file_name.lower().endswith('.cif'):
                    context_parts.append(f"  - Analysis: This is a CIF structure file that can be used for RNA-ligand interaction analysis")
                elif file_name.lower().endswith('.smiles'):
                    context_parts.append(f"  - Analysis: This is a SMILES file that can be used for aptamer generation")
                
                context_parts.append("")  # Empty line for readability
        
        return "\n".join(context_parts) if context_parts else "No specific context provided"
    
    def _build_general_context(self, state: AssistantState) -> str:
        """Build context string for general bioinformatics queries"""
        return self._build_rna_context(state)
    
    def chat(self, message: str, context: Dict[str, Any] = None, stream: bool = False, uploaded_files: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main chat interface"""
        try:
            # Build conversation context
            conversation_context = self._get_conversation_context()
            
            # Initialize state with conversation history
            messages = []
            if conversation_context:
                messages.append(SystemMessage(content=f"Conversation context:\n{conversation_context}"))
            messages.append(HumanMessage(content=message))
            
            initial_state = {
                "messages": messages,
                "response_type": "",
                "confidence": 0.0,
                "tools_used": [],
                "rag_context": "",
                "citations": [],
                "uploaded_files": uploaded_files or [],
                "agent_analysis": {}
            }
            
            if stream:
                return self._stream_chat(initial_state, message)
            else:
                return self._non_stream_chat(initial_state, message)
                
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error. Please try again."
            }
    
    def _non_stream_chat(self, state: AssistantState, user_message: str) -> Dict[str, Any]:
        """Handle non-streaming chat"""
        try:
            # Run the graph
            result = self.graph.invoke(state)
            
            # Extract response
            messages = result["messages"]
            ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
            
            if ai_messages:
                response = ai_messages[-1].content
            else:
                response = "I apologize, but I couldn't generate a response."
            
            # Add to conversation memory
            self._add_to_memory(user_message, response)
            
            return {
                "success": True,
                "response": response,
                "response_type": result.get("response_type", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "tools_used": result.get("tools_used", []),
                "citations": result.get("citations", []),
                "rag_context_used": bool(result.get("rag_context", "")),
                "agent_analysis": result.get("agent_analysis", {}),
                "timestamp": datetime.utcnow().isoformat(),
                "model": "DeepSeek Chat (LangGraph + RAG)"
            }
            
        except Exception as e:
            logger.error(f"Non-stream chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error. Please try again."
            }
    
    def _stream_chat(self, state: AssistantState, user_message: str) -> Dict[str, Any]:
        """Handle streaming chat"""
        try:
            # First, retrieve RAG context (same as non-streaming)
            state = self._retrieve_context(state)
            
            # Determine which expert to use based on classification
            classification_result = self._classify_query(state.copy())
            response_type = classification_result["response_type"]
            
            # Perform agent analysis if needed (same as non-streaming)
            if response_type in ["rna_design", "general_bioinfo"]:
                # Check if agent analysis should be performed
                should_use_agent = self._should_use_agent(user_message)
                uploaded_files = state.get("uploaded_files", [])
                
                if uploaded_files or should_use_agent:
                    # Send tool calling status to frontend
                    def generate_tool_status_stream():
                        yield f"data: {json.dumps({'type': 'tool_status', 'status': 'analyzing', 'message': 'Analyzing sequences and calling tools...'})}\n\n"
                        
                        # Perform agent analysis
                        state_with_agent = self._agent_analysis(state)
                        
                        # Update state with agent results
                        state.update(state_with_agent)
                        
                        # Send completion status only if tools were actually used
                        agent_analysis = state.get("agent_analysis", {})
                        if agent_analysis.get("success", False):
                            tools_used = agent_analysis.get("tools_used", [])
                            if tools_used:  # Only show status if tools were actually used
                                yield f"data: {json.dumps({'type': 'tool_status', 'status': 'completed', 'message': f'Analysis completed using {len(tools_used)} tools: {", ".join(tools_used)}'})}\n\n"
                        
                        return state
                    
                    # Create a combined stream that shows tool status and then AI response
                    def generate_combined_stream():
                        # Check if agent analysis should be performed
                        should_use_agent = self._should_use_agent(user_message)
                        uploaded_files = state.get("uploaded_files", [])
                        
                        if uploaded_files or should_use_agent:
                            # Analyze the request first
                            analysis_result = self.analysis_agent.analyze_request(user_message, uploaded_files)
                            
                            if analysis_result["success"] and analysis_result.get("recommended_tools"):
                                tools_used = analysis_result["recommended_tools"]
                                
                                # Send tool calling status for each tool and execute them
                                execution_results = {}
                                for tool_name in tools_used:
                                    # Send calling status
                                    yield f"data: {json.dumps({'type': 'tool_status', 'status': 'calling', 'tool': tool_name, 'message': f'Calling {tool_name}...'})}\n\n"
                                    
                                    # Small delay to ensure status is sent before tool execution
                                    import time
                                    time.sleep(0.2)
                                    
                                    # Execute the tool
                                    try:
                                        tool_result = self.analysis_agent._call_tool(
                                            tool_name,
                                            analysis_result["extracted_sequences"],
                                            uploaded_files,
                                            analysis_result.get("extracted_sequences_detailed")
                                        )
                                        execution_results[tool_name] = tool_result
                                        
                                        # Send completion status
                                        yield f"data: {json.dumps({'type': 'tool_status', 'status': 'completed', 'tool': tool_name, 'message': f'{tool_name} completed'})}\n\n"
                                        
                                    except Exception as e:
                                        execution_results[tool_name] = {
                                            "success": False,
                                            "error": str(e),
                                            "tool_name": tool_name
                                        }
                                        
                                        # Send error status
                                        yield f"data: {json.dumps({'type': 'tool_status', 'status': 'error', 'tool': tool_name, 'message': f'{tool_name} failed'})}\n\n"
                                
                                # Update state with results
                                state["agent_analysis"] = {
                                    "success": True,
                                    "analysis_plan": analysis_result["analysis_plan"],
                                    "execution_result": {
                                        "success": True,
                                        "summary": f"Successfully completed analysis using: {', '.join(tools_used)}",
                                        "tool_results": execution_results
                                    },
                                    "tools_used": tools_used,
                                    "extracted_sequences_detailed": analysis_result.get("extracted_sequences_detailed", {})
                                }
                                state["tools_used"].extend(tools_used)
                            else:
                                # No tools were identified, but don't show status message
                                state["agent_analysis"] = {
                                    "success": False,
                                    "reason": "No suitable tools identified",
                                    "analysis_plan": analysis_result.get("analysis_plan", {})
                                }
                        else:
                            # No agent analysis needed
                            state["agent_analysis"] = {"skipped": True, "reason": "No files or tool usage detected"}
                        
                        # Now continue with AI response generation
                        # Build context with agent analysis results
                        if response_type == "rna_design":
                            context = self._build_rna_context(state)
                            rag_context = state.get("rag_context", "")
                            
                            # Add agent analysis results to context
                            agent_analysis = state.get("agent_analysis", {})
                            if agent_analysis.get("success", False):
                                execution_result = agent_analysis.get("execution_result", {})
                                if execution_result.get("success", False):
                                    context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                                    context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                                    context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                                    
                                    # Add specific tool results
                                    tool_results = execution_result.get("tool_results", {})
                                    for tool_name, result in tool_results.items():
                                        if result.get("success", False):
                                            context += f"\n{tool_name.upper()} RESULTS:\n"
                                            context += f"Status: Success\n"
                                            context += f"Category: {result.get('category', 'Unknown')}\n"
                                            
                                            # Add specific data from the tool
                                            data = result.get("data", {})
                                            if isinstance(data, dict):
                                                # Handle RNA secondary structure prediction tools
                                                if tool_name in ['bpfold', 'ufold', 'mxfold2', 'rnaformer']:
                                                    if "results" in data and data["results"]:
                                                        structure_result = data["results"][0]
                                                        sequence = structure_result.get("sequence", "")
                                                        
                                                        # Extract dot-bracket notation if available
                                                        dot_bracket = None
                                                        if "structure" in structure_result:
                                                            dot_bracket = structure_result["structure"]
                                                        elif "dot_bracket" in structure_result:
                                                            dot_bracket = structure_result["dot_bracket"]
                                                        elif "data" in structure_result and not structure_result["data"].startswith("1 "):
                                                            # Only use data field if it's not CT format (which starts with "1 ")
                                                            dot_bracket = structure_result["data"]
                                                        
                                                        
                                                        if dot_bracket:
                                                            context += f"Secondary Structure (dot-bracket): {dot_bracket}\n"
                                                        elif tool_name == 'bpfold' and "data" in structure_result and structure_result["data"].startswith("1 "):
                                                            # BPFold returns CT format, indicate this
                                                            context += f"Secondary Structure: CT format data provided (not dot-bracket)\n"
                                                        
                                                        # Extract CT data if available
                                                        if "ct_data" in structure_result:
                                                            ct_data = structure_result["ct_data"]
                                                            context += f"CT Format Data:\n{ct_data}\n"
                                                        
                                                        # Extract energy information if available
                                                        if "energy" in structure_result:
                                                            energy = structure_result["energy"]
                                                            context += f"Free Energy: {energy} kcal/mol\n"
                                                        
                                                        context += f"Sequence: {sequence}\n"
                                                        context += f"Length: {len(sequence)} nucleotides\n"
                                                        
                                                # Handle protein-RNA interaction tools
                                                elif "binding_scores" in data:
                                                    scores = data["binding_scores"]
                                                    context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                                    context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                                    context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                                                elif "prediction" in data:
                                                    pred = data["prediction"]
                                                    if isinstance(pred, dict) and "binding_affinity" in pred:
                                                        context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                                    else:
                                                        context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                                                else:
                                                    context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                                        else:
                                            context += f"\n{tool_name.upper()} RESULTS:\n"
                                            context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
                            
                            # Enhance context with RAG information
                            if rag_context and rag_context != "No relevant documents found.":
                                context += f"\n\nRELEVANT LITERATURE CONTEXT:\n{rag_context}"
                            
                            system_prompt = f"""
                            You are an expert RNA design assistant. Provide detailed, accurate advice for RNA design tasks.
                            Current context: {context}
                            """
                        elif response_type == "general_bioinfo":
                            context = self._build_general_context(state)
                            rag_context = state.get("rag_context", "")
                            
                            # Add agent analysis results to context
                            agent_analysis = state.get("agent_analysis", {})
                            if agent_analysis.get("success", False):
                                execution_result = agent_analysis.get("execution_result", {})
                                if execution_result.get("success", False):
                                    context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                                    context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                                    context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                                    
                                    # Add specific tool results
                                    tool_results = execution_result.get("tool_results", {})
                                    for tool_name, result in tool_results.items():
                                        if result.get("success", False):
                                            context += f"\n{tool_name.upper()} RESULTS:\n"
                                            context += f"Status: Success\n"
                                            context += f"Category: {result.get('category', 'Unknown')}\n"
                                            
                                            # Add specific data from the tool
                                            data = result.get("data", {})
                                            if isinstance(data, dict):
                                                # Handle RNA secondary structure prediction tools
                                                if tool_name in ['bpfold', 'ufold', 'mxfold2', 'rnaformer']:
                                                    if "results" in data and data["results"]:
                                                        structure_result = data["results"][0]
                                                        sequence = structure_result.get("sequence", "")
                                                        
                                                        # Extract dot-bracket notation if available
                                                        dot_bracket = None
                                                        if "structure" in structure_result:
                                                            dot_bracket = structure_result["structure"]
                                                        elif "dot_bracket" in structure_result:
                                                            dot_bracket = structure_result["dot_bracket"]
                                                        elif "data" in structure_result and not structure_result["data"].startswith("1 "):
                                                            # Only use data field if it's not CT format (which starts with "1 ")
                                                            dot_bracket = structure_result["data"]
                                                        
                                                        
                                                        if dot_bracket:
                                                            context += f"Secondary Structure (dot-bracket): {dot_bracket}\n"
                                                        elif tool_name == 'bpfold' and "data" in structure_result and structure_result["data"].startswith("1 "):
                                                            # BPFold returns CT format, indicate this
                                                            context += f"Secondary Structure: CT format data provided (not dot-bracket)\n"
                                                        
                                                        # Extract CT data if available
                                                        if "ct_data" in structure_result:
                                                            ct_data = structure_result["ct_data"]
                                                            context += f"CT Format Data:\n{ct_data}\n"
                                                        
                                                        # Extract energy information if available
                                                        if "energy" in structure_result:
                                                            energy = structure_result["energy"]
                                                            context += f"Free Energy: {energy} kcal/mol\n"
                                                        
                                                        context += f"Sequence: {sequence}\n"
                                                        context += f"Length: {len(sequence)} nucleotides\n"
                                                        
                                                # Handle protein-RNA interaction tools
                                                elif "binding_scores" in data:
                                                    scores = data["binding_scores"]
                                                    context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                                    context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                                    context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                                                elif "prediction" in data:
                                                    pred = data["prediction"]
                                                    if isinstance(pred, dict) and "binding_affinity" in pred:
                                                        context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                                    else:
                                                        context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                                                else:
                                                    context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                                        else:
                                            context += f"\n{tool_name.upper()} RESULTS:\n"
                                            context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
                            
                            # Enhance context with RAG information
                            if rag_context and rag_context != "No relevant documents found.":
                                context += f"\n\nRELEVANT LITERATURE CONTEXT:\n{rag_context}"
                            
                            system_prompt = f"""
                            You are a bioinformatics assistant. Answer the question while relating to RNA biology when possible.
                            Current context: {context}
                            """
                        else:
                            system_prompt = """
                            You are a specialized RNA design assistant. Politely redirect off-topic questions to RNA design topics.
                            """
                        
                        # Generate AI response
                        try:
                            self.streaming_active = True
                            self.stop_streaming = False
                            
                            messages = state["messages"]
                            last_message = messages[-1].content if messages else ""
                            full_response = ""
                            
                            for chunk in self.llm.stream([
                                SystemMessage(content=system_prompt),
                                HumanMessage(content=last_message)
                            ]):
                                # Check if streaming should be stopped
                                if self.stop_streaming:
                                    logger.info("Streaming stopped by user request")
                                    break
                                    
                                # Process chunk content
                                try:
                                    if hasattr(chunk, 'content') and chunk.content:
                                        full_response += chunk.content
                                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                                except Exception as e:
                                    logger.error(f"Error processing chunk: {e}")
                                    break
                            
                            # Add to conversation memory after streaming is complete
                            if not self.stop_streaming:
                                self._add_to_memory(user_message, full_response)
                            
                            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                            
                        except Exception as e:
                            logger.error(f"Error in combined stream: {e}")
                            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    
                    return {
                        "success": True,
                        "stream_generator": generate_combined_stream,
                        "response_type": response_type,
                        "confidence": classification_result.get("confidence", 0.0),
                        "rag_context": state.get("rag_context", ""),
                        "citations": state.get("citations", [])
                    }
                else:
                    state = self._agent_analysis(state)
            
            # Check if we have literature support for RNA design and general bioinfo
            has_literature = state.get("has_literature", False)
            
            # Debug logging for streaming
            logger.info(f"Streaming RAG check: has_literature={has_literature}, response_type={response_type}")
            
            if response_type in ["rna_design", "general_bioinfo"] and not has_literature:
                # Use the literature reference required message for streaming
                from .prompts import LITERATURE_REFERENCE_REQUIRED
                messages = state["messages"]
                last_message = messages[-1].content if messages else ""
                response_content = LITERATURE_REFERENCE_REQUIRED.format(query=last_message)
                
                def generate_stream():
                    # Stream the literature required message character by character
                    for char in response_content:
                        yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
                return {
                    "success": True,
                    "stream_generator": generate_stream,
                    "response_type": response_type,
                    "confidence": classification_result.get("confidence", 0.0),
                    "rag_context": state.get("rag_context", ""),
                    "citations": state.get("citations", [])
                }
            
            # Build context based on response type
            if response_type == "rna_design":
                context = self._build_rna_context(state)
                rag_context = state.get("rag_context", "")
                
                # Add agent analysis results to context
                agent_analysis = state.get("agent_analysis", {})
                if agent_analysis.get("success", False):
                    execution_result = agent_analysis.get("execution_result", {})
                    if execution_result.get("success", False):
                        context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                        context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                        context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                        
                        # Add specific tool results
                        tool_results = execution_result.get("tool_results", {})
                        for tool_name, result in tool_results.items():
                            if result.get("success", False):
                                context += f"\n{tool_name.upper()} RESULTS:\n"
                                context += f"Status: Success\n"
                                context += f"Category: {result.get('category', 'Unknown')}\n"
                                
                                # Add specific data from the tool
                                data = result.get("data", {})
                                if isinstance(data, dict):
                                    if "binding_scores" in data:
                                        scores = data["binding_scores"]
                                        context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                        context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                        context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                                    elif "prediction" in data:
                                        pred = data["prediction"]
                                        if isinstance(pred, dict) and "binding_affinity" in pred:
                                            context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                        else:
                                            context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                                    else:
                                        context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                            else:
                                context += f"\n{tool_name.upper()} RESULTS:\n"
                                context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
                
                # Enhance context with RAG information
                if rag_context and rag_context != "No relevant documents found.":
                    context += f"\n\nRELEVANT LITERATURE CONTEXT:\n{rag_context}"
                
                system_prompt = f"""
                You are an expert RNA design assistant. Provide detailed, accurate advice for RNA design tasks.
                Current context: {context}
                """
            elif response_type == "general_bioinfo":
                context = self._build_general_context(state)
                rag_context = state.get("rag_context", "")
                
                # Add agent analysis results to context
                agent_analysis = state.get("agent_analysis", {})
                if agent_analysis.get("success", False):
                    execution_result = agent_analysis.get("execution_result", {})
                    if execution_result.get("success", False):
                        context += f"\n\nAGENT ANALYSIS RESULTS:\n"
                        context += f"Tools used: {', '.join(agent_analysis.get('tools_used', []))}\n"
                        context += f"Analysis summary: {execution_result.get('summary', 'No summary available')}\n"
                        
                        # Add specific tool results
                        tool_results = execution_result.get("tool_results", {})
                        for tool_name, result in tool_results.items():
                            if result.get("success", False):
                                context += f"\n{tool_name.upper()} RESULTS:\n"
                                context += f"Status: Success\n"
                                context += f"Category: {result.get('category', 'Unknown')}\n"
                                
                                # Add specific data from the tool
                                data = result.get("data", {})
                                if isinstance(data, dict):
                                    if "binding_scores" in data:
                                        scores = data["binding_scores"]
                                        context += f"Binding Scores: {scores[:10]}{'...' if len(scores) > 10 else ''}\n"
                                        context += f"Max Score: {data.get('max_score', 'N/A')}\n"
                                        context += f"Mean Score: {data.get('mean_score', 'N/A')}\n"
                                    elif "prediction" in data:
                                        pred = data["prediction"]
                                        if isinstance(pred, dict) and "binding_affinity" in pred:
                                            context += f"Binding Affinity: {pred['binding_affinity']}\n"
                                        else:
                                            context += f"Prediction: {str(pred)[:200]}{'...' if len(str(pred)) > 200 else ''}\n"
                                    else:
                                        context += f"Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}\n"
                            else:
                                context += f"\n{tool_name.upper()} RESULTS:\n"
                                context += f"Status: Failed - {result.get('error', 'Unknown error')}\n"
                
                # Enhance context with RAG information
                if rag_context and rag_context != "No relevant documents found.":
                    context += f"\n\nRELEVANT LITERATURE CONTEXT:\n{rag_context}"
                
                system_prompt = f"""
                You are a bioinformatics assistant. Answer the question while relating to RNA biology when possible.
                Current context: {context}
                """
            else:
                system_prompt = """
                You are a specialized RNA design assistant. Politely redirect off-topic questions to RNA design topics.
                """
            
            # Create streaming response
            def generate_stream():
                try:
                    self.streaming_active = True
                    self.stop_streaming = False
                    
                    # Send tool calling status only if tools were actually used
                    agent_analysis = state.get("agent_analysis", {})
                    if agent_analysis.get("success", False):
                        tools_used = agent_analysis.get("tools_used", [])
                        if tools_used:  # Only show status if tools were actually used
                            yield f"data: {json.dumps({'type': 'tool_status', 'status': 'completed', 'message': f'Analysis completed using {len(tools_used)} tools: {", ".join(tools_used)}'})}\n\n"
                    
                    messages = state["messages"]
                    last_message = messages[-1].content if messages else ""
                    full_response = ""
                    
                    for chunk in self.llm.stream([
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=last_message)
                    ]):
                        # Check if streaming should be stopped
                        if self.stop_streaming:
                            logger.info("Streaming stopped by user request")
                            break
                            
                        # Process chunk content
                        try:
                            if hasattr(chunk, 'content') and chunk.content:
                                full_response += chunk.content
                                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            break
                    
                    # Add to conversation memory after streaming is complete
                    if not self.stop_streaming:
                        self._add_to_memory(user_message, full_response)
                    
                    # Citations removed as requested
                    
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming failed: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                finally:
                    self.streaming_active = False
            
            return {
                "success": True,
                "stream_generator": generate_stream,
                "response_type": response_type,
                "confidence": classification_result.get("confidence", 0.0),
                "rag_context": state.get("rag_context", ""),
                "citations": state.get("citations", [])
            }
            
        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error. Please try again."
            }
    
    def get_assistant_info(self) -> Dict[str, Any]:
        """Get information about the assistant"""
        rag_stats = self.rag_system.get_system_stats()
        return {
            "name": "RNA Design Assistant",
            "version": "2.1.0",
            "framework": "LangGraph + Multimodal RAG",
            "model": "DeepSeek Chat",
            "specialization": "RNA Design and Bioinformatics",
            "capabilities": CAPABILITIES,
            "response_types": RESPONSE_TYPES,
            "tools": TOOL_DESCRIPTIONS,
            "rag_system": {
                "enabled": True,
                "multimodal": self.multimodal,
                "total_documents": rag_stats.get("total_documents", 0),
                "total_images": rag_stats.get("total_images", 0),
                "data_directory": rag_stats.get("data_directory", "data"),
                "vector_store_initialized": rag_stats.get("vector_store_initialized", True),
                "image_processing_available": rag_stats.get("image_processing_available", False),
                "is_building": rag_stats.get("is_building", False)
            }
        }
    
    
    def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search documents in the RAG system"""
        return self.rag_system.search_documents(query, k)
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        return self.rag_system.get_system_stats()
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the RAG system"""
        return self.rag_system.list_documents()
