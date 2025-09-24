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

logger = logging.getLogger(__name__)


class AssistantState(TypedDict):
    """State for the RNA Design Assistant"""
    messages: Annotated[List, add_messages]
    response_type: str  # 'rna_design', 'general_bioinfo', 'off_topic'
    confidence: float
    tools_used: Annotated[List[str], add]
    rag_context: str  # RAG context from documents
    citations: Annotated[List[Dict[str, Any]], add]  # Citations and references


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
        
        # Initialize RAG system - automatically load documents from data directory
        try:
            self.rag_system = RNADesignRAGSystem(data_directory=data_directory)
            # Automatically process all PDF and Markdown files in the data directory
            processed_count = self.rag_system.add_documents_from_directory()
            logger.info(f"Initialized RAG system with {processed_count} documents")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            raise
        
        # Ensure building state is properly set after initialization
        if hasattr(self.rag_system, 'is_building'):
            # Force the building state to false after initialization
            self.rag_system.is_building = False
            logger.info("RAG system initialization completed - building state cleared")
        
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
        logger.info("Conversation memory cleared")
        
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
            
            # Debug logging for RAG retrieval
            logger.info(f"RAG retrieval results: {len(citations)} citations found")
            if citations:
                for i, citation in enumerate(citations):
                    logger.info(f"Citation {i+1}: score={citation.get('score', 'N/A')}, title={citation.get('title', 'N/A')}")
            
            # Check if we have meaningful context
            # Very permissive threshold - accept any citations with reasonable scores
            has_literature = (
                len(citations) > 0 and
                any(citation.get("score", 0) > -0.5 for citation in citations)  # Accept even negative similarities
            )
            
            # Additional check: if we have any context at all, consider it literature
            if not has_literature and rag_context and rag_context != "No relevant documents found.":
                has_literature = True
                logger.info("RAG context found but no citations - still considering as literature")
            
            # Final fallback: if we have any citations at all, consider it literature
            if not has_literature and len(citations) > 0:
                has_literature = True
                logger.info("Found citations with low scores - still considering as literature")
            
            # Update state with RAG context
            state["rag_context"] = rag_context
            state["citations"] = citations
            state["has_literature"] = has_literature
            
            logger.info(f"Final RAG decision: has_literature={has_literature}, context_length={len(rag_context) if rag_context else 0}")
            
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
    
    def _rna_design_expert(self, state: AssistantState) -> AssistantState:
        """Handle RNA design specific queries with expert knowledge"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        # Check if we have literature support
        has_literature = state.get("has_literature", False)
        
        if not has_literature:
            # Use the literature reference required message
            from .prompts import LITERATURE_REFERENCE_REQUIRED
            response_content = LITERATURE_REFERENCE_REQUIRED.format(query=last_message)
            state["messages"].append(AIMessage(content=response_content))
            state["tools_used"].append("rna_design_expert")
            return state
        
        # Build context including RAG context
        context = self._build_rna_context(state)
        rag_context = state.get("rag_context", "")
        
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
        
        if not has_literature:
            # Use the literature reference required message
            from .prompts import LITERATURE_REFERENCE_REQUIRED
            response_content = LITERATURE_REFERENCE_REQUIRED.format(query=last_message)
            state["messages"].append(AIMessage(content=response_content))
            state["tools_used"].append("general_bioinfo")
            return state
        
        # Build context including RAG context
        context = self._build_general_context(state)
        rag_context = state.get("rag_context", "")
        
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
        
        return "\n".join(context_parts) if context_parts else "No specific context provided"
    
    def _build_general_context(self, state: AssistantState) -> str:
        """Build context string for general bioinformatics queries"""
        return self._build_rna_context(state)
    
    def chat(self, message: str, context: Dict[str, Any] = None, stream: bool = False) -> Dict[str, Any]:
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
                "citations": []
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
                    messages = state["messages"]
                    last_message = messages[-1].content if messages else ""
                    full_response = ""
                    
                    for chunk in self.llm.stream([
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=last_message)
                    ]):
                        # Note: Abort checking is handled by Flask's request handling
                        # The AbortController in the frontend will cause the request to be aborted
                        
                        if hasattr(chunk, 'content') and chunk.content:
                            full_response += chunk.content
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    
                    # Add to conversation memory after streaming is complete
                    self._add_to_memory(user_message, full_response)
                    
                    # Citations removed as requested
                    
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming failed: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
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
