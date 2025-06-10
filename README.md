# Fixer

Fixer is an experimental project to build your own AI coding assistant, inspired by tools like Cursor and Claude Code. We're creating a simplified version that uses Google's Gemini AI to go beyond just answering questions. Fixer can be instructed to perform tasks like creating files, writing code, and running programs, acting as your personal software assistant. This project is a hands-on way to explore how to build your own powerful, "agentic" AI tools from the ground up.

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
```
