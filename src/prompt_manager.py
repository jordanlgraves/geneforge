def get_system_prompt() -> str:
    with open("prompts/system_geneforge.txt", "r") as file:
        return file.read()
