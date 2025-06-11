from google.genai import types

# Import the functions and their schemas
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.run_python import run_python_file, schema_run_python_file
from functions.write_file import write_file, schema_write_file

# A map of function names to the actual functions
function_map = {
    "get_files_info": get_files_info,
    "get_file_content": get_file_content,
    "run_python_file": run_python_file,
    "write_file": write_file,
}

# The tool definition for the Gemini API
available_functions = types.Tool(
    function_declarations=[
        schema_get_files_info,
        schema_get_file_content,
        schema_run_python_file,
        schema_write_file,
    ]
)

def call_function(function_call, verbose=False):
    function_name = function_call.name
    
    if function_name not in function_map:
        raise ValueError(f"Unknown function: {function_name}")

    function_to_call = function_map[function_name]
    function_args = dict(function_call.args)
    
    # All our functions expect a `working_directory`
    # This is a security measure to prevent the AI from accessing
    # other parts of the file system.
    function_args["working_directory"] = "."

    if verbose:
        print(f"Calling function: {function_name}({function_args})")

    result = function_to_call(**function_args)
    
    return types.Part(
        function_response=types.FunctionResponse(
            name=function_name,
            response={"result": result},
        )
    )
