# Fixer: An AI Coding Assistant

Fixer is a powerful, terminal-based AI coding assistant built with Python and Google's Gemini API. It's an experimental project that demonstrates how to create an "agentic" AI that can not only answer questions but also interact with your file system to read, write, and execute code to solve problems.

## How It Works

Fixer operates on a conversational loop. When you give it a prompt, it uses the Gemini API's function-calling capabilities to form a plan. It can use a set of sandboxed tools to:

*   List files and directories
*   Read file contents
*   Write or overwrite files
*   Execute Python scripts

After each tool is used, the result is sent back to the AI, which then decides on the next step. This loop continues until the task is complete or it reaches a maximum number of iterations. The agent's "thought process" can be viewed by running it with the `--verbose` flag.

## Project Structure

*   `main.py`: The entry point for the application. It handles command-line arguments, initializes the AI client, and manages the main conversational loop.
*   `prompts.py`: Contains the system prompt that gives the AI its persona and instructions. It also dynamically generates a file tree of the current project to provide the AI with context.
*   `call_function.py`: Acts as a dispatcher. It maps the function names requested by the AI to the actual Python functions and injects the sandboxed `working_directory`.
*   `functions/`: This directory contains the individual Python scripts for each tool the AI can use (e.g., `get_files_info.py`, `write_file.py`).
*   `calculator/`: A sample project directory containing a simple command-line calculator. This is used as a sandbox for the AI to work in and was used to demonstrate its debugging capabilities.

## Setup

1.  **Get your API Key:** You'll need an API key from Google for the Gemini model. You can get one from [Google AI Studio](https://aistudio.google.com/app/apikey).

2.  **Set up your environment:**
    *   Create a file named `.env` in the root of the project.
    *   Add your API key to the `.env` file like this:
        ```
        GEMINI_API_KEY="YOUR_API_KEY_HERE"
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Use

To use Fixer, run the `main.py` script from your terminal and provide a prompt in quotes.

### Basic Questions
```bash
python3 main.py "Explain what a neural network is in simple terms"
```

### File System Operations
Fixer can interact with the file system. For example:
```bash
python3 main.py "List all the files in the current directory"
python3 main.py "Read the contents of the file called main.py"
python3 main.py "Write a new file called 'test.txt' with the content 'hello world'"
```

### Debugging Example
You can even ask Fixer to debug code. For example, to fix a bug in the included calculator application:
```bash
python3 main.py "fix the bug: 3 + 7 * 2 shouldn't be 20"
```

### Verbose Mode
To see the agent's step-by-step reasoning, add the `--verbose` flag to your command:
```bash
python3 main.py "your prompt here" --verbose
```