# Ollama LLM Setup Guide

This application has been configured to use Ollama as the LLM provider instead of Anthropic Claude. Ollama allows you to run large language models locally on your machine.

## Installation

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download and install from [https://ollama.com/download](https://ollama.com/download)

### 2. Start Ollama Server

```bash
ollama serve
```

The Ollama API will be available at `http://localhost:11434`

### 3. Download a Model

We recommend using `llama3.2` (default) or other available models:

```bash
# Download the default model (llama3.2)
ollama pull llama3.2

# Alternative models you can try:
ollama pull llama3.1        # Larger, more capable
ollama pull llama3.1:70b    # Even larger (requires more RAM)
ollama pull mistral         # Alternative model
ollama pull phi3            # Smaller, faster model
```

### 4. Verify Installation

Check that Ollama is running and the model is downloaded:

```bash
# List available models
ollama list

# Test the model
ollama run llama3.2 "Hello, how are you?"
```

## Configuration

The application uses environment variables to configure Ollama. Update your `.env` file:

```bash
# Ollama Configuration
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Environment Variables

- `OLLAMA_API_URL` - The URL where Ollama API is running (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - The model to use (default: `llama3.2`)

## Available Models

Here are some popular models you can use:

| Model | Size | RAM Required | Use Case |
|-------|------|--------------|----------|
| `llama3.2` | 3B | 4GB | Fast, good for chat |
| `llama3.1` | 8B | 8GB | Better quality |
| `llama3.1:70b` | 70B | 48GB | Best quality |
| `mistral` | 7B | 8GB | Alternative to Llama |
| `phi3` | 3.8B | 4GB | Small, fast |
| `codellama` | 7B | 8GB | Code-focused |

## Usage

Once Ollama is installed and running, the application will automatically use it for:

1. **Conversation Generation** - Real-time voice conversation responses
2. **Knowledge Base RAG** - Answering questions from uploaded documents
3. **Call Flow Generation** - Dynamic call flow configurations

## Troubleshooting

### Ollama Not Running

If you see "Ollama LLM service not available":

1. Check if Ollama is running: `ps aux | grep ollama`
2. Start Ollama: `ollama serve`
3. Verify API is accessible: `curl http://localhost:11434/api/tags`

### Model Not Downloaded

If the model is not available:

```bash
# List available models
ollama list

# Download the required model
ollama pull llama3.2
```

### Connection Issues

If the backend can't connect to Ollama:

1. Check `OLLAMA_API_URL` in `.env` file
2. Ensure Ollama is running on the correct port
3. Check firewall settings

### Performance Issues

If responses are slow:

1. Use a smaller model like `phi3` or `llama3.2`
2. Close other applications to free up RAM
3. Consider using a GPU-enabled version of Ollama

## API Endpoints

The following endpoints now use Ollama:

- `POST /api/ai/conversation` - Generate conversation responses
- `GET /api/ai/status` - Check Ollama service status
- `GET /health` - Overall service health (includes Ollama status)

## Switching Back to Claude

If you want to switch back to Claude:

1. Install the anthropic package: `pip install anthropic`
2. Update imports in `fastapi_app.py` and `websocket_handler.py`
3. Replace `ollama_service` with `claude_service`
4. Add `ANTHROPIC_API_KEY` to `.env`

## Benefits of Ollama

- **Privacy**: All processing happens locally, no data sent to external APIs
- **Cost**: Free to use, no API usage fees
- **Control**: Full control over model selection and configuration
- **Offline**: Works without internet connection once models are downloaded

## Performance Comparison

| Feature | Ollama (Local) | Claude (API) |
|---------|---------------|--------------|
| Cost | Free | Pay per token |
| Privacy | Complete | Data sent to API |
| Speed | Depends on hardware | Fast (cloud) |
| Quality | Good (varies by model) | Excellent |
| Offline | Yes | No |

## Additional Resources

- [Ollama Official Documentation](https://github.com/ollama/ollama)
- [Ollama Model Library](https://ollama.com/library)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
