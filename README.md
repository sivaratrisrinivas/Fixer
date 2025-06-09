# Fixer

Fixer is a simple command-line tool that uses Google's Gemini AI to answer your questions and follow your instructions. You give it a prompt, and it gives you a response from the AI.

## Setup

1.  **Get your API Key:** You'll need an API key from Google for the Gemini model. You can get one from [Google AI Studio](https://aistudio.google.com/app/apikey).

2.  **Set up your environment:**
    *   Create a file named `.env` in the same directory as the project.
    *   Add your API key to the `.env` file like this:
        ```
        GEMINI_API_KEY="YOUR_API_KEY_HERE"
        ```

3.  **Install dependencies:**
    Before running the tool for the first time, you need to install the necessary Python packages.
    ```bash
    pip install -r requirements.txt
    ```

## How to Use

To use Fixer, run the `main.py` script from your terminal and type your prompt after it.

```bash
python main.py "Your prompt goes here"
```

For example:
```bash
python main.py "Explain what a neural network is in simple terms"
```

### Verbose Mode

If you want to see how many "tokens" (pieces of words) your prompt and the response used, you can add `--verbose` to your prompt.

```bash
python main.py "What is the capital of France? --verbose" 