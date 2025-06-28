def get_system_prompt() -> str:
    with open("prompts/system_geneforge.txt", "r") as file:
        return file.read()

def get_kinmod_prompt() -> str:
    with open("prompts/kinmod_system.txt", "r") as file:
        return file.read()