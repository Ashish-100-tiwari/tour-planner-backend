# Load environment variables FIRST, before any other imports that use them
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
from contextlib import asynccontextmanager
from database import connect_to_mongo, close_mongo_connection
from auth import router as auth_router, get_current_user
from conversation_memory import (
    setup_conversation_indexes,
    store_message,
    get_conversation_history,
    clear_conversation_history
)
from google_maps_service import (
    extract_locations_from_text,
    format_journey_summary,
    generate_map_image_url
)
from travel_agent_prompt import get_travel_agent_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ctransformers, fallback to llama-cpp-python
USE_CTRANSFORMERS = None
ctransformers_available = False
llama_cpp_available = False

try:
    from ctransformers import AutoModelForCausalLM
    ctransformers_available = True
    logger.info("ctransformers library is available")
except ImportError:
    logger.warning("ctransformers not available")

try:
    from llama_cpp import Llama
    llama_cpp_available = True
    logger.info("llama-cpp-python library is available")
except (ImportError, ValueError, Exception) as e:
    logger.warning(f"llama-cpp-python not available: {e}")
    llama_cpp_available = False

# Prefer ctransformers, but allow fallback
if ctransformers_available:
    USE_CTRANSFORMERS = True
    logger.info("Will try to use ctransformers first")
elif llama_cpp_available:
    USE_CTRANSFORMERS = False
    logger.info("Will use llama-cpp-python")
else:
    raise ImportError(
        "Neither ctransformers nor llama-cpp-python is installed.\n"
        "Install one of them:\n"
        "  pip install ctransformers\n"
        "  OR\n"
        "  pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu"
    )

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "Llama-3.2-3B-Instruct-Q8_0.gguf")
# Convert to absolute path if relative
if not os.path.isabs(MODEL_PATH):
    MODEL_PATH = os.path.abspath(MODEL_PATH)
N_CTX = int(os.getenv("N_CTX", "2048"))
N_THREADS = int(os.getenv("N_THREADS", "4"))
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))

# Global model instance
llm_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global llm_model, USE_CTRANSFORMERS
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Set up conversation memory indexes
    await setup_conversation_indexes()
    
    # Startup
    try:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model file not found at {MODEL_PATH}")
            logger.info(f"Please ensure the GGUF model file is available at {MODEL_PATH}")
            yield
            return
        
        logger.info(f"Loading model from {MODEL_PATH}")
        
        if USE_CTRANSFORMERS:
            # Using ctransformers - try different model types for Llama 3.2
            # Try various model types that might work with Llama 3.2
            model_types_to_try = ["llama", "llama3", "llama-2", None]  # None = auto-detect
            local_files_options = [False, True]  # Try False first (allows downloading config if needed)
            
            loaded = False
            for local_files_only in local_files_options:
                for model_type in model_types_to_try:
                    try:
                        logger.info(f"Trying to load with model_type={model_type if model_type else 'auto-detect'}, local_files_only={local_files_only}")
                        # Try with model_file parameter for GGUF files
                        try:
                            if model_type:
                                llm_model = AutoModelForCausalLM.from_pretrained(
                                    MODEL_PATH,
                                    model_type=model_type,
                                    context_length=N_CTX,
                                    threads=N_THREADS,
                                    gpu_layers=N_GPU_LAYERS,
                                    local_files_only=local_files_only,
                                )
                            else:
                                # Auto-detect model type - don't specify model_type
                                llm_model = AutoModelForCausalLM.from_pretrained(
                                    MODEL_PATH,
                                    context_length=N_CTX,
                                    threads=N_THREADS,
                                    gpu_layers=N_GPU_LAYERS,
                                    local_files_only=local_files_only,
                                )
                        except Exception as e1:
                            # If from_pretrained fails, try using model_file parameter directly
                            logger.debug(f"from_pretrained failed, trying model_file parameter: {e1}")
                            if model_type:
                                llm_model = AutoModelForCausalLM(
                                    model_file=MODEL_PATH,
                                    model_type=model_type,
                                    context_length=N_CTX,
                                    threads=N_THREADS,
                                    gpu_layers=N_GPU_LAYERS,
                                )
                            else:
                                llm_model = AutoModelForCausalLM(
                                    model_file=MODEL_PATH,
                                    context_length=N_CTX,
                                    threads=N_THREADS,
                                    gpu_layers=N_GPU_LAYERS,
                                )
                        
                        logger.info(f"Successfully loaded with model_type={model_type if model_type else 'auto-detect'}")
                        loaded = True
                        break
                    except Exception as e:
                        logger.warning(f"Failed with model_type={model_type if model_type else 'auto-detect'}, local_files_only={local_files_only}: {e}")
                        continue
                if loaded:
                    break
            
            if not loaded:
                # If ctransformers failed but llama-cpp-python is available, try that
                if llama_cpp_available:
                    logger.warning("ctransformers failed, trying llama-cpp-python as fallback...")
                    USE_CTRANSFORMERS = False
                    llm_model = Llama(
                        model_path=MODEL_PATH,
                        n_ctx=N_CTX,
                        n_threads=N_THREADS,
                        n_gpu_layers=N_GPU_LAYERS,
                        verbose=False
                    )
                    logger.info("Successfully loaded with llama-cpp-python fallback")
                else:
                    error_msg = (
                        "Failed to load model with ctransformers. All model types failed.\n"
                        "Possible solutions:\n"
                        "1. Upgrade ctransformers: pip install --upgrade ctransformers\n"
                        "2. Install llama-cpp-python (may require Visual C++ Redistributables on Windows):\n"
                        "   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu\n"
                        "   If that fails, try: pip install llama-cpp-python --force-reinstall --no-cache-dir\n"
                        "3. Check if the GGUF model file is valid and not corrupted"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)
        else:
            # Using llama-cpp-python
            llm_model = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=N_THREADS,
                n_gpu_layers=N_GPU_LAYERS,
                verbose=False
            )
        
        logger.info("Model loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.error("=" * 60)
        logger.error("MODEL LOADING FAILED!")
        logger.error("=" * 60)
        try:
            if USE_CTRANSFORMERS:
                logger.error("ctransformers failed to load the model.")
                logger.error("You can try:")
                logger.error("1. Install llama-cpp-python instead: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu")
                logger.error("2. Or check if ctransformers version is compatible: pip install --upgrade ctransformers")
                logger.error("3. Or try using the llama.cpp server binary (original approach)")
            else:
                logger.error("llama-cpp-python failed to load the model.")
                logger.error("You can try:")
                logger.error("1. Install ctransformers: pip install ctransformers")
                logger.error("2. Or check if the model file is valid and accessible")
        except:
            logger.error("Unable to determine which library was being used.")
            logger.error("Try installing: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu")
        logger.error("=" * 60)
        logger.info("The application will start but model endpoints will not work")
    
    yield
    
    # Shutdown
    if llm_model:
        logger.info("Unloading model...")
        llm_model = None
        logger.info("Model unloaded")
    
    # Close MongoDB connection
    await close_mongo_connection()


app = FastAPI(
    title="LLM Server with Llama-3.2-3B-Instruct",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.5      # Optimized: reduced from 0.7 for faster generation
    max_tokens: Optional[int] = 100         # Optimized: reduced from 200 for faster responses
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1
    stop: Optional[List[str]] = None


class CompletionRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 200  # ~150 words (1 token ≈ 0.75 words)
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1
    stop: Optional[List[str]] = None


class ChatResponse(BaseModel):
    message: ChatMessage
    usage: dict


class CompletionResponse(BaseModel):
    text: str
    usage: dict


def format_messages_for_llama(messages: List[ChatMessage]) -> str:
    """Format messages for Llama-3.2-Instruct format"""
    # Llama-3.2-Instruct uses a specific chat template
    formatted = ""
    is_first_message = True
    
    for msg in messages:
        if msg.role == "system":
            # Only add begin_of_text for the very first system message
            if is_first_message:
                formatted += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{msg.content}<|eot_id|>"
                is_first_message = False
            else:
                # Subsequent system messages don't need begin_of_text
                formatted += f"<|start_header_id|>system<|end_header_id|>\n\n{msg.content}<|eot_id|>"
        elif msg.role == "user":
            formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{msg.content}<|eot_id|>"
            is_first_message = False
        elif msg.role == "assistant":
            formatted += f"<|start_header_id|>assistant<|end_header_id|>\n\n{msg.content}<|eot_id|>"
            is_first_message = False
    
    # Add assistant header for response
    formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return formatted


@app.get("/")
async def root():
    """Health check endpoint"""
    model_loaded = llm_model is not None
    return {
        "status": "running",
        "model_loaded": model_loaded,
        "model_path": MODEL_PATH,
        "library": "ctransformers" if USE_CTRANSFORMERS else "llama-cpp-python"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    model_loaded = llm_model is not None
    return {
        "status": "healthy" if model_loaded else "unhealthy",
        "model_loaded": model_loaded
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Chat completions endpoint compatible with OpenAI API (requires authentication)"""
    if llm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        user_email = current_user.get("email")
        
        # Retrieve conversation history from MongoDB
        history = await get_conversation_history(user_email)
        
        # Combine history with current request messages
        # History is already in chronological order (oldest first)
        all_messages = []
        
        # Add travel agent system prompt at the beginning
        system_prompt = get_travel_agent_prompt()
        all_messages.append(ChatMessage(
            role="system",
            content=system_prompt
        ))
        
        # Add historical messages
        for hist_msg in history:
            all_messages.append(ChatMessage(
                role=hist_msg["role"],
                content=hist_msg["content"]
            ))
        
        # Check if user message contains location information
        journey_info = None
        map_image_url = None
        detected_origin = None
        detected_destination = None
        
        for msg in request.messages:
            if msg.role == "user":
                # Try to extract origin and destination
                origin, destination = extract_locations_from_text(msg.content)
                
                if origin and destination:
                    # Store for later use
                    detected_origin = origin
                    detected_destination = destination
                    
                    # Fetch journey information from Google Maps
                    logger.info(f"Detected journey request: {origin} to {destination}")
                    journey_info = format_journey_summary(origin, destination)
                    
                    # Generate map image URL
                    map_image_url = generate_map_image_url(origin, destination)
                    
                    if journey_info:
                        # Add journey information as a system message before user's message
                        all_messages.append(ChatMessage(
                            role="system",
                            content=f"[JOURNEY DATA FROM GOOGLE MAPS]\n{journey_info}\n[Use this information to provide a helpful travel summary to the user]"
                        ))
                        logger.info("Successfully retrieved journey information from Google Maps")
                    else:
                        logger.warning("Failed to retrieve journey information from Google Maps")
        
        # Add current request messages
        all_messages.extend(request.messages)
        
        # Store the user's current message(s) in the database
        for msg in request.messages:
            if msg.role == "user":
                await store_message(user_email, "user", msg.content)
        
        # Format messages for Llama-3.2-Instruct
        prompt = format_messages_for_llama(all_messages)
        
        # Generate response
        if USE_CTRANSFORMERS:
            # ctransformers uses max_new_tokens
            generation_kwargs = {
                "max_new_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k,
                "repetition_penalty": request.repeat_penalty,
            }
            if request.stop:
                generation_kwargs["stop"] = request.stop
            
            response_text = llm_model(
                prompt,
                **generation_kwargs
            )
        else:
            # llama-cpp-python uses max_tokens (not max_new_tokens)
            # and uses create_completion method which returns a Completion object
            response = llm_model.create_completion(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                repeat_penalty=request.repeat_penalty,
                stop=request.stop if request.stop else [],
            )
            response_text = response["choices"][0]["text"]
        
        # Clean up response (remove the prompt if it was included)
        if response_text.startswith(prompt):
            response_text = response_text[len(prompt):].strip()
        
        # Note: Only user messages are stored in conversation history
        # Assistant responses are NOT stored to save database space
        
        # Calculate usage (approximate)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response_text.split())
        
        return {
            "id": "chatcmpl-" + str(hash(prompt)),
            "object": "chat.completion",
            "created": int(__import__("time").time()),
            "model": "llama-3.2-3b-instruct",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            # Include map image URL if journey was detected
            "map_image_url": map_image_url,
            "journey_details": {
                "origin": detected_origin,
                "destination": detected_destination
            } if detected_origin and detected_destination else None
        }
    except Exception as e:
        logger.error(f"Error generating chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/completions")
async def completions(request: CompletionRequest, current_user: dict = Depends(get_current_user)):
    """Text completions endpoint (requires authentication)"""
    if llm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Generate response
        if USE_CTRANSFORMERS:
            # ctransformers uses max_new_tokens
            generation_kwargs = {
                "max_new_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k,
                "repetition_penalty": request.repeat_penalty,
            }
            if request.stop:
                generation_kwargs["stop"] = request.stop
            
            response_text = llm_model(
                request.prompt,
                **generation_kwargs
            )
        else:
            # llama-cpp-python uses max_tokens (not max_new_tokens)
            # and uses create_completion method which returns a Completion object
            response = llm_model.create_completion(
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                repeat_penalty=request.repeat_penalty,
                stop=request.stop if request.stop else [],
            )
            response_text = response["choices"][0]["text"]
        
        # Calculate usage (approximate)
        prompt_tokens = len(request.prompt.split())
        completion_tokens = len(response_text.split())
        
        return {
            "id": "cmpl-" + str(hash(request.prompt)),
            "object": "text_completion",
            "created": int(__import__("time").time()),
            "model": "llama-3.2-3b-instruct",
            "choices": [{
                "index": 0,
                "text": response_text,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }
    except Exception as e:
        logger.error(f"Error generating completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))




class MapRequest(BaseModel):
    origin: str
    destination: str
    zoom: Optional[int] = None
    size: Optional[str] = "600x400"


class MapResponse(BaseModel):
    map_image_url: str
    zoom_level: Optional[int]
    origin: str
    destination: str


@app.post("/v1/map/generate", response_model=MapResponse)
async def generate_map(request: MapRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate a map image URL with optional zoom level (requires authentication)
    
    Args:
        request: MapRequest with origin, destination, optional zoom and size
        current_user: Authenticated user from JWT token
    
    Returns:
        MapResponse with map_image_url and metadata
    """
    try:
        # Validate zoom level if provided
        if request.zoom is not None:
            if request.zoom < 1 or request.zoom > 21:
                raise HTTPException(
                    status_code=400,
                    detail="Zoom level must be between 1 and 21"
                )
        
        # Generate map image URL
        map_url = generate_map_image_url(
            origin=request.origin,
            destination=request.destination,
            size=request.size,
            zoom=request.zoom
        )
        
        if not map_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate map image URL"
            )
        
        logger.info(f"Generated map for {request.origin} to {request.destination} with zoom={request.zoom}")
        
        return MapResponse(
            map_image_url=map_url,
            zoom_level=request.zoom,
            origin=request.origin,
            destination=request.destination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/conversations/clear")
async def clear_conversations(current_user: dict = Depends(get_current_user)):
    """
    Clear conversation history for the current user
    Manually removes all stored messages (they would auto-expire after 30 minutes anyway)
    """
    try:
        user_email = current_user.get("email")
        success = await clear_conversation_history(user_email)
        
        if success:
            return {
                "status": "success",
                "message": "Conversation history cleared"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear conversation history"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Try to find an available port starting from the specified port
    def find_free_port(start_port):
        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        return None
    
    # Check if the specified port is available
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
        logger.info(f"Starting server on port {port}")
    except OSError:
        logger.warning(f"Port {port} is already in use, trying to find an available port...")
        free_port = find_free_port(port)
        if free_port:
            port = free_port
            logger.info(f"Found available port: {port}")
        else:
            logger.error(f"Could not find an available port starting from {port}")
            raise
    
    uvicorn.run(app, host="0.0.0.0", port=port)

