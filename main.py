import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

if len(sys.argv) < 2:
    print('Usage: python main.py "prompt is not provided"')
    sys.exit(1)

prompt = ' '.join(sys.argv[1:])

messages = [
    types.Content(
        role='user',
        parts=[types.Part(text=prompt)]
    )
]

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=messages
)

verbose = '--verbose' in prompt
if verbose:
    prompt = prompt.replace('--verbose', '').strip()
    print(f'User prompt: {prompt}')
    print(f'Prompt tokens: {response.usage_metadata.prompt_token_count}')
    print(f'Response tokens: {response.usage_metadata.candidates_token_count}')

print(response.text)

