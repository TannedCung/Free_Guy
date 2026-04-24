import os

from dotenv import load_dotenv

load_dotenv()

# OpenAI API key — required only when LLM_PROVIDER=openai.
# vLLM and Ollama providers work fine with an empty or dummy key.
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
_llm_provider = os.environ.get("LLM_PROVIDER", "openai").lower()
if not openai_api_key and _llm_provider == "openai":
    raise ValueError("OPENAI_API_KEY environment variable is required. Copy .env.example to .env and set a value.")

# Put your name
key_owner = os.environ.get("KEY_OWNER", "unknown")

maze_assets_loc = os.environ.get("MAZE_ASSETS_LOC", "..//frontend_server/static_dirs/assets")
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

collision_block_id = "32125"

# Verbose
debug = True
