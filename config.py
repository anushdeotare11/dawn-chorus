"""Central configuration for Dawn Chorus."""

# ── BirdNET settings ─────────────────────────────────────────────
DEFAULT_LATITUDE: float = 13.0   # Bangalore, India
DEFAULT_LONGITUDE: float = 77.6
CONFIDENCE_THRESHOLD: float = 0.5
CONFIDENCE_MIN: float = 0.1
CONFIDENCE_MAX: float = 0.9
CONFIDENCE_STEP: float = 0.05
BINGO_CARD_SIZE: int = 12
BINGO_LOCATION_MIN_CONF: float = 0.03  # BirdNET default for location query

# ── Ollama / Gemma settings ──────────────────────────────────────
OLLAMA_MODEL: str = "gemma3:4b"
FIELD_CARD_MIN_WORDS: int = 150
FIELD_CARD_MAX_WORDS: int = 250
OLLAMA_TIMEOUT: int = 90

# ── Audio settings ───────────────────────────────────────────────
SUPPORTED_EXTENSIONS: list[str] = ["wav", "mp3", "m4a", "ogg", "flac"]
FFMPEG_SAMPLE_RATE: int = 48000
FFMPEG_CHANNELS: int = 1

# ── Output ───────────────────────────────────────────────────────
WALKS_DIR: str = "walks"
