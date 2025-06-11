import os

def get_file_tree():
    # This is a simplified file tree generator
    # In a real-world scenario, you'd want a more robust solution
    file_tree = []
    for root, dirs, files in os.walk("."):
        # Exclude hidden files and directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        files = [f for f in files if not f.startswith('.')]
        
        level = root.replace(".", "").count(os.sep)
        indent = " " * 4 * (level)
        file_tree.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 4 * (level + 1)
        for f in files:
            file_tree.append(f"{sub_indent}{f}")
    return "\n".join(file_tree)

system_prompt = f"""
You are Fixer, a powerful AI coding assistant. Your task is to help users with their coding-related problems.

You are currently working in a project with the following file structure:
{get_file_tree()}

When a user asks a question, you should first explore the file system to understand the project structure. Then, you can read files, write files, or execute code to answer the user's question.

You can perform the following operations:

- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.

Use "." to refer to the current working directory.
"""