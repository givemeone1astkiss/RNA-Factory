from flask import Blueprint, request, jsonify, Response
import os
import json
import logging
from pathlib import Path

from app.copilot import RNADesignAssistant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

copilot_bp = Blueprint("copilot", __name__)

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")

# Initialize RNA Design Assistant
assistant = None


def get_assistant():
    """Get or initialize the RNA Design Assistant"""
    global assistant
    if assistant is None:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DeepSeek API key not configured")
        assistant = RNADesignAssistant(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            multimodal=True
        )
    return assistant


@copilot_bp.route("/status", methods=["GET"])
def ai_status():
    """Check AI service status"""
    try:
        if not DEEPSEEK_API_KEY:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "DeepSeek API key not configured",
                        "status": "unconfigured",
                    }
                ),
                200,
            )

        # Get assistant info
        assistant = get_assistant()
        info = assistant.get_assistant_info()

        return jsonify(
            {
                "success": True,
                "message": "RNA Design Assistant is running",
                "status": "ready",
                "assistant_info": info,
            }
        )

    except Exception as e:
        logger.error(f"AI status check failed: {e}")
        return jsonify({"success": False, "message": str(e), "status": "error"}), 200


@copilot_bp.route("/chat", methods=["POST"])
def ai_chat():
    """Handle AI chat requests"""
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"success": False, "message": "Message is required"}), 400

        message = data["message"].strip()
        context = data.get("context", {})
        stream = data.get("stream", False)

        if not message:
            return (
                jsonify({"success": False, "message": "Message cannot be empty"}),
                400,
            )

        # Check if API key is configured
        if not DEEPSEEK_API_KEY:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "DeepSeek API key not configured. Please contact administrator.",
                    }
                ),
                500,
            )

        # Get assistant and process request
        assistant = get_assistant()
        
        if stream:
            return ai_chat_stream(assistant, message, context)
        else:
            result = assistant.chat(message, context, stream=False)
            return jsonify(result)

    except ValueError as e:
        logger.error(f"AI chat validation error: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request. Please try again later.",
                }
            ),
            500,
        )


def ai_chat_stream(assistant, message, context):
    """Handle streaming AI chat responses"""

    def generate():
        try:
            # Get streaming response from assistant
            result = assistant.chat(message, context, stream=True)
            
            if not result["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', 'Unknown error')})}\n\n"
                return
            
            # Use the stream generator from the assistant
            stream_generator = result.get("stream_generator")
            if stream_generator:
                for chunk in stream_generator():
                    # Note: Abort checking is handled by Flask's request handling
                    # The AbortController in the frontend will cause the request to be aborted
                    yield chunk
            else:
                # Fallback to non-streaming response
                non_stream_result = assistant.chat(message, context, stream=False)
                if non_stream_result["success"]:
                    response = non_stream_result["response"]
                    # Send response as single chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': response})}\n\n"
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': non_stream_result.get('error', 'Unknown error')})}\n\n"

        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    # Return SSE response with proper headers
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@copilot_bp.route("/models", methods=["GET"])
def ai_models():
    """Get available AI models"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500
        
        assistant = get_assistant()
        info = assistant.get_assistant_info()
        
        return jsonify(
            {
                "success": True,
                "models": [
                    {
                        "id": "rna-design-assistant",
                        "name": "RNA Design Assistant",
                        "description": "LangGraph-powered AI assistant specialized in RNA design and bioinformatics",
                        "framework": "LangGraph",
                        "capabilities": info["capabilities"],
                        "response_types": info["response_types"],
                    }
                ],
            }
        )
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@copilot_bp.route("/config", methods=["GET"])
def ai_config():
    """Get AI configuration status"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": True,
                "configured": False,
                "message": "DeepSeek API key not configured"
            })
        
        assistant = get_assistant()
        info = assistant.get_assistant_info()
        
        return jsonify(
            {
                "success": True,
                "configured": True,
                "api_base": DEEPSEEK_API_BASE,
                "assistant_info": info,
                "features": [
                    "LangGraph workflow management",
                    "Query classification and routing",
                    "RNA design expertise",
                    "Context-aware responses",
                    "Streaming support",
                    "Off-topic redirection",
                ],
            }
        )
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@copilot_bp.route("/rag/documents", methods=["GET"])
def rag_documents():
    """Get list of documents in RAG system"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500
        
        assistant = get_assistant()
        documents = assistant.list_documents()
        
        return jsonify({
            "success": True,
            "documents": documents,
            "count": len(documents)
        })
        
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




@copilot_bp.route("/rag/search", methods=["POST"])
def rag_search():
    """Search documents in RAG system"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500
        
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({
                "success": False,
                "message": "query is required"
            }), 400
        
        assistant = get_assistant()
        results = assistant.search_documents(
            query=data["query"],
            k=data.get("k", 5)
        )
        
        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@copilot_bp.route("/rag/stats", methods=["GET"])
def rag_stats():
    """Get RAG system statistics"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500

        assistant = get_assistant()
        stats = assistant.get_rag_stats()

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@copilot_bp.route("/multimodal/search", methods=["POST"])
def multimodal_search():
    """Search both text and images in documents"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500

        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({
                "success": False,
                "message": "query is required"
            }), 400

        assistant = get_assistant()
        
        # Check if multimodal is available
        if not assistant.multimodal or not hasattr(assistant.rag_system, 'search_documents'):
            return jsonify({
                "success": False,
                "message": "Multimodal search not available"
            }), 400

        results = assistant.rag_system.search_documents(
            query=data["query"],
            k=data.get("k", 5),
            include_images=data.get("include_images", True)
        )

        return jsonify({
            "success": True,
            "results": results,
            "count": len(results),
            "multimodal": True
        })

    except Exception as e:
        logger.error(f"Failed to perform multimodal search: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@copilot_bp.route("/multimodal/images", methods=["GET"])
def list_images():
    """List all images in the RAG system"""
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                "success": False,
                "message": "DeepSeek API key not configured"
            }), 500

        assistant = get_assistant()
        
        if not assistant.multimodal or not hasattr(assistant.rag_system, 'images_metadata'):
            return jsonify({
                "success": False,
                "message": "Multimodal system not available"
            }), 400

        images = []
        for image_hash, metadata in assistant.rag_system.images_metadata.items():
            images.append({
                "hash": image_hash,
                "source_file": metadata.get("source_file", ""),
                "page_number": metadata.get("page", 0),
                "description": metadata.get("description", ""),
                "image_path": metadata.get("image_path", ""),
                "ocr_text": metadata.get("ocr_text", "")
            })

        return jsonify({
            "success": True,
            "images": images,
            "count": len(images)
        })

    except Exception as e:
        logger.error(f"Failed to list images: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




@copilot_bp.route("/memory/clear", methods=["POST"])
def clear_memory():
    """Clear conversation memory"""
    try:
        assistant = get_assistant()
        assistant.clear_memory()
        return jsonify({"success": True, "message": "Conversation memory cleared"})
    except Exception as e:
        logger.error(f"Clear memory failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@copilot_bp.route("/memory", methods=["GET"])
def get_memory():
    """Get conversation memory"""
    try:
        assistant = get_assistant()
        memory = assistant.conversation_memory
        return jsonify({
            "success": True,
            "memory": memory,
            "count": len(memory)
        })
    except Exception as e:
        logger.error(f"Get memory failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

