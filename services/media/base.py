"""Base types and interfaces for TTS providers."""


def create_tts_config(pipeline_config):
    """Create TTS configuration from pipeline configuration."""
    return {
        "elevenlabs_api_key": pipeline_config.get("elevenlabs_api_key"),
        "elevenlabs_voice_id": pipeline_config.get(
            "elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb"
        ),
        "elevenlabs_model_id": pipeline_config.get(
            "elevenlabs_model_id", "eleven_multilingual_v2"
        ),
        "edge_tts_voice": pipeline_config.get("edge_tts_voice", "en-US-AriaNeural"),
        "request_timeout_seconds": pipeline_config.get("request_timeout_seconds", 20),
    }
