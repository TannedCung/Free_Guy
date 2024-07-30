from openai import OpenAI
from ollama._client import Client
ollama_client = Client(host='http://localhost:11434/')

emb = ollama_client.embeddings(model='nomic-embed-text', prompt='The sky is blue because of rayleigh scattering')

print(emb)

# client = OpenAI(
#     base_url = 'http://localhost:11434/',
#     api_key='ollama', # required, but unused
# )

# emb = client.embeddings.create(
#         input=["The sky is blue because of Rayleigh scattering"], model="nomic-embed-text")

# res = emb['data'][0]['embedding']

# print(res)