import streamlit as st
import sys
import os
import logging
import json
from typing import Dict, Any

# Ensure the project root is on the PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.llm_module import get_llm_client, chat_with_tool
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.tools.functions import ToolIntegration
from src.examples.agent.example_harness import ExampleRunner
from src.examples.agent.design_w_promoter_vars import DesignWithPromoterVarsRunner, PROMPT as PROMPT_VARS
from src.examples.agent.design_minimal_input_sensors import MinimalInputSensorsRunner, PROMPT as PROMPT_SENSORS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeneForge_UI")

# --- Page Configuration ---
st.set_page_config(
    page_title="GeneForge",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Examples ---
EXAMPLES: Dict[str, Any] = {
    "Design with Promoter Variants": (DesignWithPromoterVarsRunner, PROMPT_VARS),
    "Design with Minimal Input Sensors": (MinimalInputSensorsRunner, PROMPT_SENSORS),
}

# --- Session State Initialization ---
def init_session_state():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = get_system_prompt()
    if "loaded_prompt" not in st.session_state:
        st.session_state.loaded_prompt = None
    if "llm_client_type" not in st.session_state:
        st.session_state.llm_client_type = "deepseek"  # Default client
    if "core_session" not in st.session_state:
        st.session_state.core_session = SessionState()
    if "tool_integration" not in st.session_state:
        st.session_state.tool_integration = ToolIntegration(st.session_state.core_session)
    
    # Initialize client and model based on selection
    client, model = get_llm_client(client_type=st.session_state.llm_client_type)
    st.session_state.client = client
    st.session_state.model = model

# --- UI Components ---
def draw_sidebar():
    """Draw the sidebar with example runners and controls."""
    with st.sidebar:
        st.title("Settings")
        
        # LLM Client Selector
        client_type = st.radio(
            "Select LLM Client",
            ("deepseek", "openai"),
            index=0 if st.session_state.llm_client_type == "deepseek" else 1,
        )
        if client_type != st.session_state.llm_client_type:
            st.session_state.llm_client_type = client_type
            # Clear client-specific session state to force re-initialization
            if "client" in st.session_state: del st.session_state["client"]
            if "model" in st.session_state: del st.session_state["model"]
            st.rerun()

        st.divider()
        st.title("GeneForge Examples")
        st.write("Select an example to load its prompt.")
        
        example_name = st.selectbox("Choose an example:", list(EXAMPLES.keys()))
        
        if st.button("Load Example"):
            runner_class, prompt_text = EXAMPLES[example_name]
            runner = runner_class(example_name, prompt=prompt_text, max_rounds=20)
            st.session_state.system_prompt = runner.system_prompt or get_system_prompt()
            st.session_state.messages = []
            st.session_state.loaded_prompt = runner.prompt
            st.rerun()

        st.divider()
        st.title("Session Controls")
        if st.button("Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def display_chat():
    """Display the chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message.get("content")
            if content:
                st.markdown(content)
            
            # Display tool calls from the assistant in a clean, readable format
            if "function_call" in message and message["function_call"]:
                tool_call = message["function_call"]
                tool_name = tool_call.get("name")
                
                try:
                    args = json.loads(tool_call.get("arguments", "{}"))
                    
                    with st.expander(f"Tool Call: `{tool_name}`", expanded=True):
                        # Display arguments in a more readable format
                        formatted_args = f"**{tool_name}**\n"
                        for key, value in args.items():
                            # Truncate long values
                            display_value = str(value)
                            if len(display_value) > 200:
                                display_value = display_value[:200] + "..."
                            formatted_args += f"- **{key}**: `{display_value}`\n"
                        st.markdown(formatted_args)

                except json.JSONDecodeError:
                    # Fallback for malformed JSON
                    st.json(tool_call)

def handle_chat_submission(prompt: str):
    """Handles the logic for submitting a prompt to the LLM and updating the chat."""
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # This list will be modified by chat_with_tool to include the full history
                messages_for_api = [
                    {"role": "system", "content": st.session_state.system_prompt}
                ] + st.session_state.messages
                
                # print the tool integrations
                print('tool integrations:   ')
                for tool in st.session_state.tool_integration.tools:
                    print(tool)

                response_message = chat_with_tool(
                    client=st.session_state.client,
                    messages=messages_for_api,
                    tool_integration=st.session_state.tool_integration,
                    model=st.session_state.model,
                    max_rounds=25
                )
                
                # Update main message list with the history from the run
                st.session_state.messages = [m for m in messages_for_api if m['role'] != 'system']
                # Append the final assistant response which is not added by chat_with_tool
                st.session_state.messages.append({"role": "assistant", "content": response_message.content})
                
            except Exception as e:
                logger.error(f"An error occurred: {e}", exc_info=True)
                st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {e}"})
    
    # Rerun to display the new messages
    st.rerun()

# --- Main Application Logic ---
def main():
    """Main function to run the Streamlit app."""
    init_session_state()
    st.title("GeneForge Agentic Design 🧬")
    
    with st.expander("View System Prompt"):
        st.markdown(f"```\n{st.session_state.system_prompt}\n```")

    draw_sidebar()
    display_chat()

    # If an example prompt has been loaded, show it in a form
    if st.session_state.get("loaded_prompt"):
        with st.form("loaded_prompt_form"):
            prompt_text = st.text_area("Loaded Example Prompt:", value=st.session_state.loaded_prompt, height=150)
            submitted = st.form_submit_button("Send Prompt")
            if submitted:
                st.session_state.loaded_prompt = None  # Clear prompt after sending
                handle_chat_submission(prompt_text)

    # The main chat input for freeform conversation
    if prompt := st.chat_input("What would you like to design?"):
        handle_chat_submission(prompt)

if __name__ == "__main__":
    main() 