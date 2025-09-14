import streamlit as st
import sys
import os
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
from src.tool_registry import tool_functions

# Ensure the project root is on the PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


from litellm import completion
from src.llm_module import get_llm_params
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.tool_registry import ToolIntegration, tool_functions

from src.scenarios.design.design_w_promoter_vars import DesignWithPromoterVarsScenario, PROMPT as PROMPT_VARS
from src.scenarios.design.design_minimal_input_sensors import MinimalInputSensorsScenario, PROMPT as PROMPT_SENSORS
from src.scenarios.design.design_w_promoter_vars_and_research import DesignWithPromoterVarsWResearchScenario, PROMPT as PROMPT_VARS_W_RESEARCH
from src.scenarios.design.design_toggle_switch import SimpleNotGateSimulationScenario, PROMPT as PROMPT_SIMPLE_NOT_GATE
from src.scenarios.km_simulation.km_simulation import KineticModelingSimulationScenario, PROMPT as PROMPT_KM_SIMULATION
from src.scenarios.km_simulation.km_simulation_laci_decay import KMEColiLacIDecayScenario, PROMPT as PROMPT_KM_SIMULATION_LACI_DECAY
from src.scenarios.km_simulation.km_simulation_aa_starvation import KMAminoAcidStarvationScenario, PROMPT as PROMPT_KM_SIMULATION_AA_STARVATION
from src.scenarios.design.design_and_sim_genetic_toggle import GeneticToggleSwitchScenario, PROMPT as PROMPT_GENETIC_TOGGLE_SWITCH

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
    # "Circuit Design: Simple Not Gate Simulation": (SimpleNotGateSimulationRunner, PROMPT_SIMPLE_NOT_GATE),
    "Circuit Design: with Promoter Variants": (DesignWithPromoterVarsScenario, PROMPT_VARS),
    "Circuit Design: with Minimal Input Sensors": (MinimalInputSensorsScenario, PROMPT_SENSORS),
    "Circuit Design: with Promoter Variants and Research": (DesignWithPromoterVarsWResearchScenario, PROMPT_VARS_W_RESEARCH),
    "Kinetic Modeling: Simple Simulation": (KineticModelingSimulationScenario, PROMPT_KM_SIMULATION),
    "Kinetic Modeling: E. coli LacI Decay": (KMEColiLacIDecayScenario, PROMPT_KM_SIMULATION_LACI_DECAY),
    "Kinetic Modeling: Amino Acid Starvation": (KMAminoAcidStarvationScenario, PROMPT_KM_SIMULATION_AA_STARVATION),
    "Genetic Toggle Switch": (GeneticToggleSwitchScenario, PROMPT_GENETIC_TOGGLE_SWITCH),
}

# --- Session State Initialization ---
def init_session_state():
    """Initialize Streamlit session state.  The first call creates default
    placeholders for provider-specific credentials so they persist across
    reruns."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = get_system_prompt()
    if "loaded_prompt" not in st.session_state:
        st.session_state.loaded_prompt = None
    if "llm_client_type" not in st.session_state:
        st.session_state.llm_client_type = "deepseek"  # Default client

    # Provider credentials – pre-populate from the current environment
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if "deepseek_api_key" not in st.session_state:
        st.session_state.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if "deepseek_base_url" not in st.session_state:
        st.session_state.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # Ensure environment variables reflect current credentials **before**
    # initialising the SDK client.
    if st.session_state.openai_api_key:
        os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
    if st.session_state.deepseek_api_key:
        os.environ["DEEPSEEK_API_KEY"] = st.session_state.deepseek_api_key
    if st.session_state.deepseek_base_url:
        os.environ["DEEPSEEK_BASE_URL"] = st.session_state.deepseek_base_url

    # Initialize model based on selection using the up-to-date env
    def _default_model_for_client(client_type: str) -> str:
        if client_type == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o")
        if client_type == "deepseek":
            return os.getenv("DEEPSEEK_MODEL", "deepseek-coder")
        if client_type == "art":
            # If using local ART, caller should configure hosted_vllm/<name> via env
            return os.getenv("ART_MODEL", "hosted_vllm/local")
        return "gpt-4o"

    if "model" not in st.session_state:
        st.session_state.model = _default_model_for_client(st.session_state.llm_client_type)
    if "core_session" not in st.session_state:
        st.session_state.core_session = SessionState()
    if "tool_integration" not in st.session_state:
        st.session_state.tool_integration = ToolIntegration(st.session_state.core_session)
    if "agent_mode" not in st.session_state:
        st.session_state.agent_mode = True  # Default to automatic agent mode
    if "pending_tool_calls" not in st.session_state:
        st.session_state.pending_tool_calls = []
    # Clean up deprecated assistant state
    for key in ["current_run_id", "current_thread_id"]:
        if key in st.session_state:
            del st.session_state[key]

# --- UI Components ---
def draw_sidebar():
    """Draw the sidebar with example runners and controls."""
    with st.sidebar:
        # ---------------- Settings ----------------
        with st.expander("⚙️ Settings", expanded=False):
            client_type = st.radio(
                "Select LLM Provider",
                ("openai", "deepseek", "art"),
                index=(
                    0
                    if st.session_state.llm_client_type in (None, "openai")
                    else 1
                    if st.session_state.llm_client_type == "deepseek"
                    else 2
                ),
                key="llm_provider_radio"
            )

            if client_type != st.session_state.llm_client_type:
                st.session_state.llm_client_type = client_type
                if "client" in st.session_state: del st.session_state["client"]
                if "model" in st.session_state: del st.session_state["model"]
                st.rerun()

            st.markdown("---")

            # Provider-specific creds
            if client_type == "openai":
                openai_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password")
                if openai_key != st.session_state.openai_api_key:
                    st.session_state.openai_api_key = openai_key
                    os.environ["OPENAI_API_KEY"] = openai_key
                    if "model" in st.session_state: del st.session_state["model"]
                    st.rerun()
                # Model override
                m = st.text_input("OpenAI model", value=st.session_state.get("model", "gpt-4o"))
                if m != st.session_state.get("model"):
                    st.session_state.model = m
                    st.rerun()
            elif client_type == "deepseek":
                deepseek_key = st.text_input("DeepSeek API Key", value=st.session_state.deepseek_api_key, type="password")
                deepseek_url = st.text_input("DeepSeek Base URL", value=st.session_state.deepseek_base_url)

                changed = False
                if deepseek_key != st.session_state.deepseek_api_key:
                    st.session_state.deepseek_api_key = deepseek_key
                    os.environ["DEEPSEEK_API_KEY"] = deepseek_key
                    changed = True
                if deepseek_url != st.session_state.deepseek_base_url:
                    st.session_state.deepseek_base_url = deepseek_url
                    os.environ["DEEPSEEK_BASE_URL"] = deepseek_url
                    changed = True
                if changed:
                    if "model" in st.session_state: del st.session_state["model"]
                    st.rerun()
                m = st.text_input("DeepSeek model", value=st.session_state.get("model", "deepseek-coder"))
                if m != st.session_state.get("model"):
                    st.session_state.model = m
                    st.rerun()
            else:
                # 'art' backend currently requires no additional credentials.
                st.info("Using local *art* model – no API keys required.")
                m = st.text_input("ART model (hosted_vllm/<name>)", value=st.session_state.get("model", os.getenv("ART_MODEL", "hosted_vllm/local")))
                if m != st.session_state.get("model"):
                    st.session_state.model = m
                    st.rerun()

            agent_mode = st.toggle(
                "🤖 Agent Mode",
                value=st.session_state.agent_mode,
                help="When enabled, the agent executes tools automatically. When disabled, you approve each tool call manually."
            )
            if agent_mode != st.session_state.agent_mode:
                st.session_state.agent_mode = agent_mode
                st.rerun()

        st.divider()

        # ---------------- History Export ----------------
        if st.session_state.messages:
            # Use a unique key for the button based on message count to avoid state issues
            export_key = f"export_{len(st.session_state.messages)}"
            if st.button("Export Chat History", key=export_key):
                # Create a unique filename for the export
                export_filename = f"geneforge_chat_{uuid.uuid4().hex[:8]}.json"
                export_data = json.dumps(st.session_state.messages, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=export_data,
                    file_name=export_filename,
                    mime="application/json",
                )

        # ---------------- Examples ----------------
        st.caption("### Examples")
        st.caption("Select an example to load its prompt.")
        
        example_name = st.selectbox("Choose an example:", list(EXAMPLES.keys()))
        
        if st.button("Load Example"):
            runner_class, prompt_text = EXAMPLES[example_name]
            runner = runner_class(scenario_name=example_name, prompt=prompt_text)
            st.session_state.system_prompt = runner.system_prompt or get_system_prompt()
            st.session_state.messages = []
            st.session_state.loaded_prompt = runner.prompt
            st.rerun()

        st.divider()
        st.subheader("Session State")

        # ---- Session Overview inside sidebar ----
        if "overview_placeholder" not in st.session_state:
            st.session_state.overview_placeholder = st.empty()
        _render_session_overview(st.session_state.overview_placeholder)

        st.divider()

        # ---------------- SBML Upload ----------------
        with st.expander("📄 Upload SBML", expanded=False):
            uploaded_sbml = st.file_uploader("Upload SBML file (.xml, .sbml, .rdf)", type=["xml", "sbml", "rdf"])
            if uploaded_sbml is not None:
                import tellurium as te
                try:
                    rr = te.loadSBMLModel(uploaded_sbml.getvalue().decode('utf-8'))
                except Exception as e:
                    st.error(f"Error loading SBML file: {e}")
                    return

                # Determine save directory (session-specific if available)
                design_session_state = st.session_state.core_session
                save_dir: Path = design_session_state.output_directory if design_session_state.output_directory else Path("uploads")
                os.makedirs(save_dir, exist_ok=True)

                # Build unique filename preserving original extension
                orig_name = Path(uploaded_sbml.name)
                unique_name = f"{orig_name.stem}_{uuid.uuid4().hex[:8]}{orig_name.suffix}"
                save_path = save_dir / unique_name

                # make sure we can read with tellurium
                # Persist file bytes
                with open(save_path, "wb") as fp:
                    fp.write(uploaded_sbml.getbuffer())

                # Persist in session
                from src.simulation_utils import build_param_template
                import libsbml
                sbml_doc = libsbml.readSBMLFromFile(str(save_path))
                template = build_param_template(sbml_doc)
                
                design_session_state.sbml_doc = sbml_doc
                design_session_state.sbml_file = save_path
                design_session_state.parameter_template = template

                st.success(f"SBML file saved to {save_path}")

                # Optional preview
                if st.checkbox("Show first 20 lines", key="preview_sbml"):
                    try:
                        txt = uploaded_sbml.getvalue().decode("utf-8", errors="ignore")
                        preview = "\n".join(txt.splitlines()[:20])
                        st.code(preview, language="xml")
                    except Exception:
                        st.warning("Could not decode file for preview.")

                # Force UI refresh so that session overview updates immediately
                # st.rerun()

        st.divider()
        if st.button("🔄 Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def execute_pending_tool_call(index: int, container=st):
    """Execute a specific pending tool call."""
    if index >= len(st.session_state.pending_tool_calls):
        return
    
    tool_call = st.session_state.pending_tool_calls[index]
    fn_name = tool_call['function']['name']
    tool_msg = None
    try:
        fn_args = json.loads(tool_call['function']['arguments'])
        result = st.session_state.tool_integration.call_tool_function(fn_name, fn_args)
        
        # Store result for submission
        tool_msg_content = json.dumps(result)
        # container.success(f"Executed {fn_name} successfully!")
        
    except Exception as e:
        # container.error(f"Error executing {fn_name}: {e}")
        tool_msg_content = json.dumps({"error": str(e), "success": False})

    # Create and log the tool message
    tool_msg = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": fn_name,
        "content": tool_msg_content,
    }
    st.session_state.messages.append(tool_msg)
    
    chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
    if chat_logger:
        chat_logger.add_message(tool_msg)
            
    tool_call["executed"] = True
    refresh_session_overview()

def skip_pending_tool_call(index: int):
    """Skip a specific pending tool call."""
    if index >= len(st.session_state.pending_tool_calls):
        return
    
    tool_call = st.session_state.pending_tool_calls[index]
    
    tool_msg_content = json.dumps({"error": "Tool execution skipped by user", "success": False})
    tool_msg = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": tool_call["function"]["name"],
        "content": tool_msg_content,
    }
    st.session_state.messages.append(tool_msg)

    chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
    if chat_logger:
        chat_logger.add_message(tool_msg)

    st.info(f"Skipped {tool_call['function']['name']}")
    tool_call['executed'] = True
    refresh_session_overview()

def execute_all_pending_tools():
    """Execute all pending tool calls."""
    for i in range(len(st.session_state.pending_tool_calls)):
        if not st.session_state.pending_tool_calls[i].get('executed'):
            execute_pending_tool_call(i)
    
    # Submit all results
    submit_tool_results()

def submit_tool_results():
    """Submit tool results back to the assistant."""
    if not st.session_state.pending_tool_calls:
        return
    
    handle_chat_submission(prompt=None)
    st.session_state.pending_tool_calls = []

def continue_without_tools():
    """Continue the conversation without executing tools."""
    for tool_call in st.session_state.pending_tool_calls:
        tool_msg = {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "name": tool_call["function"]["name"],
            "content": json.dumps({"error": "Tool execution declined by user", "success": False}),
        }
        st.session_state.messages.append(tool_msg)
        chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
        if chat_logger:
            chat_logger.add_message(tool_msg)

    st.session_state.pending_tool_calls = []
    handle_chat_submission(prompt=None)

def handle_chat_submission(prompt: Optional[str]):
    """Handles one turn of the conversation: takes a prompt, calls the LLM, and appends the response."""
    chat_logger = getattr(st.session_state.core_session, "chat_logger", None)

    # 1. Add new user prompt to history if provided
    if prompt:
        user_msg = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_msg)
        if chat_logger:
            chat_logger.add_message(user_msg)

    # 2. Run the LLM if it's our turn
    # (i.e., last message was from user or a tool response)
    last_message = st.session_state.messages[-1] if st.session_state.messages else None
    if not last_message or last_message["role"] in ("user", "tool"):
        with st.spinner("Assistant is thinking..."):
            try:
                api_messages = [
                    {k: v for k, v in msg.items() if k != "name"}
                    for msg in st.session_state.messages
                ]
                # Build litellm params (provider inferred from model string)
                llm_params = get_llm_params(model=st.session_state.model)
                # Use litellm streaming interface
                stream = completion(
                    **llm_params,
                    messages=api_messages,
                    tools=tool_functions,
                    stream=True,
                )

                # We can't use the streaming context manager because we need the final assembled message
                response_content = ""
                tool_call_chunks = []
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        response_content += delta.content
                    if delta and delta.tool_calls:
                        for tool_call_chunk in delta.tool_calls:
                            if len(tool_call_chunks) <= tool_call_chunk.index:
                                tool_call_chunks.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            
                            chunk_json = tool_call_chunk.model_dump()
                            if chunk_json.get("id"):
                                tool_call_chunks[tool_call_chunk.index]["id"] += chunk_json.get("id", "")
                            if chunk_json.get("function", {}).get("name"):
                                tool_call_chunks[tool_call_chunk.index]["function"]["name"] += chunk_json["function"]["name"]
                            if chunk_json.get("function", {}).get("arguments"):
                                tool_call_chunks[tool_call_chunk.index]["function"]["arguments"] += chunk_json["function"]["arguments"]
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                logger.error(f"Chat completion failed: {e}", exc_info=True)
                return

        assistant_msg = {"role": "assistant", "content": response_content or ""}
        if tool_call_chunks:
            assistant_msg["tool_calls"] = tool_call_chunks
        
        st.session_state.messages.append(assistant_msg)
        if chat_logger:
            chat_logger.add_message(assistant_msg)
        
# ---------------------------------------------------------------------------
#  Session overview (read-only) panel (updates live via placeholder)
# ---------------------------------------------------------------------------

def _render_session_overview(container):
    """Populate *container* with the current SessionState snapshot."""
    container.empty()  # clear previous content
    design_session_state: SessionState = st.session_state.core_session
    with container.container():        
        st.write(f"**Selected library:** {design_session_state.cello_library.current_library_id or '—'}")
    
        # gather some specs from the selected library
        if design_session_state.cello_library.current_library_id:
            cello_library = design_session_state.cello_library
            lib_specs = cello_library.get_library_specs(design_session_state.cello_library.current_library_id)
            st.write("**Library specs:**")
            st.json(lib_specs)

        if design_session_state.design_spec:
            st.write("**Design spec:**")
            st.markdown(design_session_state.design_spec[:400] + (" …" if len(design_session_state.design_spec) > 400 else ""))

        verilog = design_session_state.verilog_code
        if verilog:
            st.write("**Current Verilog:**")
            st.code("\n".join(verilog.splitlines()), language="verilog")
        else:
            st.write("**Current Verilog:** —")

    with container.container():
        # Display SBML file path if present
        if design_session_state.sbml_file:
            st.write("**SBML file:**")
            st.code(str(design_session_state.sbml_file))
        # Show the parameter template if it exists
        if design_session_state.parameter_template:
            st.write("**Parameter template:**")
            st.json(design_session_state.parameter_template)

        # ------------------------------------------------------------------
        #  Generated files section
        # ------------------------------------------------------------------
        if design_session_state.generated_files:
            st.write("**Generated files:**")
            import uuid as _uuid_dl
            for f in design_session_state.generated_files:
                path_obj = Path(f["path"])
                if not path_obj.exists():
                    logger.warning("Generated file missing on disk: %s", path_obj)
                    continue

                label = f.get("label", path_obj.name)
                unique_key = f"download_{_uuid_dl.uuid4().hex}"

                try:
                    data_bytes = path_obj.read_bytes()
                    st.download_button(
                        label=f"Download {label}",
                        data=data_bytes,
                        file_name=path_obj.name,
                        key=unique_key,
                    )
                except Exception as exc:
                    logger.error("Failed to prepare download button for %s: %s", path_obj, exc)
                    st.warning(f"Could not load file {path_obj.name} for download.")

def refresh_session_overview():
    """Re-render the overview placeholder if it exists in session_state."""
    placeholder = st.session_state.get("overview_placeholder")
    if placeholder is not None:
        _render_session_overview(placeholder)

# --- Main Application Logic ---
def main():
    """Main function to run the Streamlit app."""
    init_session_state()

    # If the last run set a flag to continue, do it now
    if st.session_state.get("run_llm_on_next_rerun"):
        st.session_state.run_llm_on_next_rerun = False
        handle_chat_submission(prompt=None)
        st.rerun()

    # st.title("Genetic Design Assistant")
    
    # with st.expander("View System Prompt"):
    #     st.markdown(f"```\n{st.session_state.system_prompt}\n```")

    draw_sidebar()

    # --- CSS for scrollable tool container ---
    st.markdown("""
        <style>
        /*
        The selector below targets the second column of the main layout.
        It's designed to be specific enough to avoid affecting other parts of the UI.
        - 'section[data-testid="stSidebar"] + section': Targets the main content area next to the sidebar.
        - '[data-testid="stHorizontalBlock"]': Finds the horizontal block for the columns.
        - '> div:nth-child(2)': Selects the wrapper of the second column.
        */
        section[data-testid="stSidebar"] + section [data-testid="stHorizontalBlock"] > div:nth-child(2) {
            max-height: 80vh; /* Use max-height to be flexible */
            overflow-y: auto;
            padding-right: 1rem; /* Add some padding */
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Main chat area ---
    col_text, col_tool = st.columns([1, 1], gap="medium")

    with col_text:
        st.subheader("Chat")
        for m in st.session_state.messages:
            if m["role"] == "user":
                 with st.chat_message("user"):
                    content = m.get("content", "")
                    if content:
                        st.markdown(content)
            elif m["role"] == "assistant":
                content = m.get("content", "")
                if content:
                    with st.chat_message("assistant"):
                        st.markdown(content)
    
    with col_tool:
        st.subheader("Tool Use")
        for m in st.session_state.messages:
            role = m["role"]
            if role == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    st.info(f"🛠️ Tool Call: `{fn_name}`")
                    try:
                        args = json.loads(tc["function"]["arguments"])
                        st.json(args, expanded=False)
                    except json.JSONDecodeError:
                        st.text(tc["function"]["arguments"])

            if role == "tool":
                label = m.get("name") or "tool_response"
                st.info(f"📤 Tool Response: `{label}`")
                try:
                    payload = json.loads(m.get("content", ""))
                    if label == "run_kinetic_model_simulation" and isinstance(payload, dict) and payload.get("success"):
                        import pandas as pd
                        cols = payload.get("columns", [])
                        data = payload.get("result", [])
                        if data:
                            try:
                                df = pd.DataFrame(data, columns=cols if cols else None)
                                if cols:
                                    df.set_index(cols[0], inplace=True)
                                st.line_chart(df)
                            except Exception as e:
                                st.error(f"Chart error: {e}")
                        if payload.get("plot_path"):
                            from pathlib import Path as _P
                            p = _P(payload["plot_path"])
                            if p.exists():
                                st.image(str(p))
                    else:
                        st.json(payload, expanded=False)
                except Exception:
                    st.text(m.get("content", ""))


    # --- Agent Execution Logic ---
    last_message = st.session_state.messages[-1] if st.session_state.messages else None
    if last_message and last_message.get("tool_calls"):
        if st.session_state.agent_mode:
            st.session_state.pending_tool_calls = last_message["tool_calls"]
            with st.spinner("Executing tools..."):
                for i in range(len(st.session_state.pending_tool_calls)):
                    execute_pending_tool_call(i)
            st.session_state.pending_tool_calls = []
            st.session_state.run_llm_on_next_rerun = True
            st.rerun()
        elif not st.session_state.pending_tool_calls:
            st.session_state.pending_tool_calls = last_message.get("tool_calls", [])
            st.rerun()


    # --- Manual Tool Approval UI ---
    if not st.session_state.agent_mode and st.session_state.pending_tool_calls:
        st.divider()
        st.subheader("🔧 Pending Tool Calls")
        st.write("The assistant wants to execute the following tools. Review and approve them:")
        
        for i, tool_call in enumerate(st.session_state.pending_tool_calls):
            with st.expander(f"Tool {i+1}: `{tool_call['function']['name']}`", expanded=True):
                try:
                    args = json.loads(tool_call['function']['arguments'])
                    st.json(args)
                except json.JSONDecodeError:
                    st.error("Invalid JSON arguments")
                    st.text(tool_call['function']['arguments'])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Execute Tool {i+1}", key=f"execute_{i}"):
                        execute_pending_tool_call(i)
                        st.rerun()
                with col2:
                    if st.button(f"❌ Skip Tool {i+1}", key=f"skip_{i}"):
                        skip_pending_tool_call(i)
                        st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Execute All Tools"):
                execute_all_pending_tools()
                # The underlying functions will trigger the rerun
        with col2:
            if st.button("❌ Skip All Tools"):
                continue_without_tools()
                # The underlying functions will trigger the rerun

    # Example prompt form
    if st.session_state.get("loaded_prompt"):
        with st.form("loaded_prompt_form"):
            prompt_text = st.text_area("Loaded Example Prompt:", value=st.session_state.loaded_prompt, height=150)
            submitted = st.form_submit_button("Send Prompt")
            if submitted:
                st.session_state.loaded_prompt = None
                handle_chat_submission(prompt_text)
                st.rerun()

    # Free-form chat input
    if prompt := st.chat_input("What would you like to design?"):
        handle_chat_submission(prompt)
        st.rerun()

if __name__ == "__main__":
    main() 