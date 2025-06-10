# from functions.get_files_info import get_files_info

# print("--- Running get_files_info('calculator', '.') ---")
# print(get_files_info("calculator", "."))
# print("\n--- Running get_files_info('calculator', 'pkg') ---")
# print(get_files_info("calculator", "pkg"))
# print("\n--- Running get_files_info('calculator', '/bin') ---")
# print(get_files_info("calculator", "/bin"))
# print("\n--- Running get_files_info('calculator', '../') ---")
# print(get_files_info("calculator", "../"))

from functions.get_file_content import get_file_content

# Create a large file to test truncation
# with open("calculator/lorem.txt", "w") as f:
#     f.write("x" * 10001)  # Create file with 10001 characters
# print(get_file_content("calculator", "lorem.txt"))

print(get_file_content("calculator", "calculator/main.py"))
print(get_file_content("calculator", "calculator/pkg/calculator.py"))
print(get_file_content("calculator", "/bin/cat"))

