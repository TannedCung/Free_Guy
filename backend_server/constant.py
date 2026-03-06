import os

from dotenv import load_dotenv

load_dotenv()

# OpenAI API key loaded from environment variable OPENAI_API_KEY
openai_api_key = os.environ.get('OPENAI_API_KEY', '')
if not openai_api_key:
    raise ValueError(
        "OPENAI_API_KEY environment variable is required. "
        "Copy .env.example to .env and set a value."
    )

# Put your name
key_owner = os.environ.get('KEY_OWNER', 'unknown')

maze_assets_loc = "..//frontend_server/static_dirs/assets"
# maze_assets_loc = "frontend_server/static_dirs/assets"
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

fs_storage = "..//frontend_server/storage"
fs_temp_storage = "..//frontend_server/temp_storage"
# fs_storage = "frontend_server/storage"
# fs_temp_storage = "frontend_server/temp_storage"

collision_block_id = "32125"

# Verbose 
debug = True