import streamlit as st
import sys
import os
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, Any
from typing_extensions import override
from openai import AssistantEventHandler

# Ensure the project root is on the PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


from src.llm_module import get_llm_client, run_assistant
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.functions import ToolIntegration
from src.design_state import DesignState

from src.examples.agent.design_w_promoter_vars import DesignWithPromoterVarsRunner, PROMPT as PROMPT_VARS
from src.examples.agent.design_minimal_input_sensors import MinimalInputSensorsRunner, PROMPT as PROMPT_SENSORS
from src.examples.agent.design_w_promoter_vars_and_research import DesignWithPromoterVarsWResearchRunner, PROMPT as PROMPT_VARS_W_RESEARCH
from src.examples.agent.design_toggle_switch import SimpleNotGateSimulationRunner, PROMPT as PROMPT_SIMPLE_NOT_GATE
from src.examples.agent.km_simulation import KineticModelingSimulationRunner, PROMPT as PROMPT_KM_SIMULATION
from src.examples.agent.km_simulation_laci_decay import KMEColiLacIDecayExample, PROMPT as PROMPT_KM_SIMULATION_LACI_DECAY
from src.examples.agent.km_simulation_aa_starvation import KMAminoAcidStarvationExample, PROMPT as PROMPT_KM_SIMULATION_AA_STARVATION
from src.examples.agent.design_and_sim_genetic_toggle import GeneticToggleSwitchExample, PROMPT as PROMPT_GENETIC_TOGGLE_SWITCH

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
    "Circuit Design: with Promoter Variants": (DesignWithPromoterVarsRunner, PROMPT_VARS),
    "Circuit Design: with Minimal Input Sensors": (MinimalInputSensorsRunner, PROMPT_SENSORS),
    "Circuit Design: with Promoter Variants and Research": (DesignWithPromoterVarsWResearchRunner, PROMPT_VARS_W_RESEARCH),
    "Kinetic Modeling: Simple Simulation": (KineticModelingSimulationRunner, PROMPT_KM_SIMULATION),
    "Kinetic Modeling: E. coli LacI Decay": (KMEColiLacIDecayExample, PROMPT_KM_SIMULATION_LACI_DECAY),
    "Kinetic Modeling: Amino Acid Starvation": (KMAminoAcidStarvationExample, PROMPT_KM_SIMULATION_AA_STARVATION),
    "Genetic Toggle Switch": (GeneticToggleSwitchExample, PROMPT_GENETIC_TOGGLE_SWITCH),
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

    # Initialize client and model based on selection using the up-to-date env
    client, model = get_llm_client(client_type=st.session_state.llm_client_type)
    st.session_state.client = client
    st.session_state.model = model
    if "core_session" not in st.session_state:
        st.session_state.core_session = SessionState()
    if "tool_integration" not in st.session_state:
        st.session_state.tool_integration = ToolIntegration(st.session_state.core_session)
    if "agent_mode" not in st.session_state:
        st.session_state.agent_mode = True  # Default to automatic agent mode
    if "pending_tool_calls" not in st.session_state:
        st.session_state.pending_tool_calls = []
    if "current_run_id" not in st.session_state:
        st.session_state.current_run_id = None
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

# --- UI Components ---
def draw_sidebar():
    """Draw the sidebar with example runners and controls."""
    with st.sidebar:
        # ---------------- Settings ----------------
        with st.expander("⚙️ Settings", expanded=False):
            client_type = st.radio(
                "Select LLM Provider",
                ("openai", "deepseek"),
                index=0 if (st.session_state.llm_client_type in (None, "openai")) else 1,
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
                    if "client" in st.session_state: del st.session_state["client"]
                    if "model" in st.session_state: del st.session_state["model"]
                    st.rerun()
            else:
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
                    if "client" in st.session_state: del st.session_state["client"]
                    if "model" in st.session_state: del st.session_state["model"]
                    st.rerun()

            agent_mode = st.toggle(
                "🤖 Agent Mode",
                value=st.session_state.agent_mode,
                help="When enabled, the agent executes tools automatically. When disabled, you approve each tool call manually."
            )
            if agent_mode != st.session_state.agent_mode:
                st.session_state.agent_mode = agent_mode
                st.rerun()

        # ---------------- Examples ----------------
        st.caption("### Examples")
        st.caption("Select an example to load its prompt.")
        
        example_name = st.selectbox("Choose an example:", list(EXAMPLES.keys()))
        
        if st.button("Load Example"):
            runner_class, prompt_text = EXAMPLES[example_name]
            runner = runner_class(example_name, prompt=prompt_text, max_rounds=20)
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
                sess = st.session_state.core_session
                save_dir: Path = sess.output_directory if sess.output_directory else Path("uploads")
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
                from src.simulate.param_template import build_param_template
                import libsbml
                sbml_doc = libsbml.readSBMLFromFile(str(save_path))
                template = build_param_template(sbml_doc)
                
                st.session_state.core_session.design_state = DesignState()
                st.session_state.core_session.design_state.sbml_doc  = sbml_doc
                st.session_state.core_session.design_state.sbml_file = save_path
                st.session_state.core_session.design_state.parameter_template = template

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

def display_chat():
    """Display the chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message.get("content")

            # ------------------------------------------------------------------
            #  Render normal assistant / user content
            # ------------------------------------------------------------------
            if content and message["role"] in ("assistant", "user"):
                st.markdown(content)

            # ------------------------------------------------------------------
            #  Special handling for tool messages
            # ------------------------------------------------------------------
            if message["role"] == "tool":
                try:
                    tool_payload = json.loads(content)
                except Exception:
                    st.markdown(content)
                    tool_payload = None

                tool_name = message.get("name", "tool_result")

                if tool_name == "run_kinetic_model_simulation" and tool_payload and tool_payload.get("success"):
                    import pandas as pd
                    cols = tool_payload.get("columns") or []
                    data = tool_payload.get("result", [])
                    if data:
                        try:
                            df = pd.DataFrame(data, columns=cols if cols else None)
                            if cols:
                                df.set_index(cols[0], inplace=True)
                            st.line_chart(df)
                        except Exception as e:
                            st.error(f"Failed to render chart: {e}")
                    # Show PNG if generated
                    if tool_payload.get("plot_path"):
                        from pathlib import Path
                        p = Path(tool_payload["plot_path"])
                        if p.exists():
                            st.image(str(p))
                    else:
                        st.info("No simulation data.")
                else:
                    # Fallback – pretty-print JSON
                    if tool_payload is not None:
                        st.json(tool_payload)
                    else:
                        st.markdown(content)

            # ------------------------------------------------------------------
            #  Display tool calls requested by assistant (within assistant msg)
            # ------------------------------------------------------------------
            if message["role"] == "assistant" and "tool_calls" in message:
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call.get("name")
                    args = tool_call.get("arguments", {})
                    result = tool_call.get("result")
                    with st.expander(f"Tool Call: `{tool_name}`", expanded=False):
                        st.write("**Arguments:**")
                        st.json(args)
                        if result:
                            st.write("**Result:**")
                            st.json(result)

    # Display pending tool calls for manual approval
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
                st.rerun()
        with col2:
            if st.button("❌ Skip All Tools"):
                st.session_state.pending_tool_calls = []
                continue_without_tools()
                st.rerun()

    # Clear pending tool calls
    st.session_state.pending_tool_calls = []
    st.session_state.current_run_id = None
    st.session_state.current_thread_id = None

def execute_pending_tool_call(index: int):
    """Execute a specific pending tool call."""
    if index >= len(st.session_state.pending_tool_calls):
        return
    
    tool_call = st.session_state.pending_tool_calls[index]
    fn_name = tool_call['function']['name']
    
    try:
        fn_args = json.loads(tool_call['function']['arguments'])
        result = st.session_state.tool_integration.call_tool_function(fn_name, fn_args)
        
        # Store result for submission
        tool_call['result'] = result
        tool_call['executed'] = True
        
        # Log the tool execution
        tool_msg = {
            "role": "tool",
            "name": fn_name,
            "content": json.dumps(result),
        }
        st.session_state.messages.append(tool_msg)
        
        chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
        if chat_logger:
            chat_logger.add_message(tool_msg)
            
        st.success(f"Executed {fn_name} successfully!")
        
        # Update live session overview
        refresh_session_overview()
        
    except Exception as e:
        st.error(f"Error executing {fn_name}: {e}")
        tool_call['result'] = {"error": str(e)}
        tool_call['executed'] = True

def skip_pending_tool_call(index: int):
    """Skip a specific pending tool call."""
    if index >= len(st.session_state.pending_tool_calls):
        return
    
    tool_call = st.session_state.pending_tool_calls[index]
    tool_call['result'] = {"error": "Tool execution skipped by user"}
    tool_call['executed'] = True
    st.info(f"Skipped {tool_call['function']['name']}")

    # Update live session overview
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
    
    tool_outputs = []
    for tool_call in st.session_state.pending_tool_calls:
        if tool_call.get('executed'):
            tool_outputs.append({
                "tool_call_id": tool_call['id'],
                "output": json.dumps(tool_call.get('result', {}))
            })
    
    if tool_outputs and st.session_state.current_run_id and st.session_state.current_thread_id:
        try:
            # Continue the assistant run with tool outputs
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                class ContinuationHandler(AssistantEventHandler):
                    @override
                    def on_text_delta(self, delta, snapshot):
                        nonlocal full_response
                        full_response += delta.value
                        message_placeholder.markdown(full_response + "▌")
                
                with st.session_state.client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=st.session_state.current_thread_id,
                    run_id=st.session_state.current_run_id,
                    tool_outputs=tool_outputs,
                    event_handler=ContinuationHandler(),
                ) as stream:
                    stream.until_done()
                
                message_placeholder.markdown(full_response)
                if full_response:
                    assistant_msg = {"role": "assistant", "content": full_response}
                    st.session_state.messages.append(assistant_msg)
                    
                    chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
                    if chat_logger:
                        chat_logger.add_message(assistant_msg)
        
        except Exception as e:
            st.error(f"Error submitting tool results: {e}")
    
    # Clear pending tool calls
    st.session_state.pending_tool_calls = []
    st.session_state.current_run_id = None
    st.session_state.current_thread_id = None

def continue_without_tools():
    """Continue the conversation without executing tools."""
    # Submit empty/error results for all pending tools
    tool_outputs = []
    for tool_call in st.session_state.pending_tool_calls:
        tool_outputs.append({
            "tool_call_id": tool_call['id'],
            "output": json.dumps({"error": "Tool execution declined by user"})
        })
    
    if tool_outputs and st.session_state.current_run_id and st.session_state.current_thread_id:
        try:
            with st.session_state.client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=st.session_state.current_thread_id,
                run_id=st.session_state.current_run_id,
                tool_outputs=tool_outputs,
                event_handler=AssistantEventHandler(),
            ) as stream:
                stream.until_done()
        except Exception as e:
            st.error(f"Error continuing without tools: {e}")
    
    # Clear pending tool calls
    st.session_state.pending_tool_calls = []
    st.session_state.current_run_id = None
    st.session_state.current_thread_id = None

def handle_chat_submission(prompt: str):
    """Handles the logic for submitting a prompt to the LLM and updating the chat."""
    if not prompt:
        return

    # ------------------------------------------------------------------
    #  User message – update in-memory chat and persistent log (if enabled)
    # ------------------------------------------------------------------
    user_msg = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)
    chat_logger = getattr(st.session_state.core_session, "chat_logger", None)
    if chat_logger:
        chat_logger.add_message(user_msg)

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        class EventHandler(AssistantEventHandler):
            def __init__(self, run_id=None, thread_id=None):
                super().__init__()
                self.client = st.session_state.client
                self.tool_integration = st.session_state.tool_integration
                self.run_id = run_id
                self.thread_id = thread_id
                self.chat_logger = chat_logger

            @override
            def on_event(self, event):
                if event.event == 'thread.run.created':
                    self.run_id = event.data.id
                    self.thread_id = event.data.thread_id
                
                if event.event == 'thread.run.requires_action':
                    if st.session_state.agent_mode:
                        self.handle_requires_action_auto(event.data)
                    else:
                        self.handle_requires_action_manual(event.data)
                
                if event.event == 'thread.run.failed':
                    self.handle_run_failed(event.data)

            @override
            def on_text_delta(self, delta, snapshot):
                nonlocal full_response
                full_response += delta.value
                message_placeholder.markdown(full_response + "▌")
            
            def handle_run_failed(self, data):
                """Handle run failure."""
                # show an error message
                # st.error(f"Run failed: {data.error.message}") Will not work: "'Run' object has no attribute 'error'"
                # add a failure message to the chat
                # st.chat_message("assistant").markdown(f"**Run failed:** {data.last_error.message}")
                st.session_state.messages.append({"role": "assistant", "content": f"**Run failed:** {data.last_error.message}"})
                if self.chat_logger:
                    self.chat_logger.add_message({"role": "assistant", "content": f"**Run failed:** {data.last_error.message}"})  # type: ignore


            def handle_requires_action_auto(self, data):
                """Handle tool calls automatically in agent mode."""
                nonlocal full_response, message_placeholder  # capture outer scope

                # ----------------------------------------------------------
                #  Finalise assistant text *before* the tool call so that
                #  chat order is preserved (text → tool → next text).
                # ----------------------------------------------------------
                pre_text = full_response.strip()
                if pre_text:
                    # Remove the typing cursor and commit to chat history
                    message_placeholder.markdown(pre_text)
                    st.session_state.messages.append({"role": "assistant", "content": pre_text})
                    if self.chat_logger:
                        self.chat_logger.add_message({"role": "assistant", "content": pre_text})

                # Reset buffer & placeholder for post-tool text
                full_response = ""
                message_placeholder = st.empty()

                run_id = data.id
                thread_id = data.thread_id
                tool_outputs = []

                with st.expander("Tool Calls", expanded=True):
                    seen_call_ids: set[str] = set()
                    for tool_call in data.required_action.submit_tool_outputs.tool_calls:
                        if tool_call.id in seen_call_ids:
                            continue  # skip duplicates
                        seen_call_ids.add(tool_call.id)
                        fn_name = tool_call.function.name
                        try:
                            fn_args = json.loads(tool_call.function.arguments)
                            st.write(f"Calling function: `{fn_name}`")
                            st.json(fn_args)
                        except json.JSONDecodeError as e:
                            st.error(f"Invalid JSON for {fn_name}: {e}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps({"error": f"Invalid JSON arguments: {e}"})
                            })
                            continue

                        try:
                            result = self.tool_integration.call_tool_function(fn_name, fn_args)
                            # If this is a simulation result, render a chart immediately
                            if fn_name == "run_kinetic_model_simulation" and result.get("success"):
                                import pandas as pd
                                cols = result.get("columns") or []
                                data = result.get("result", [])
                                if data:
                                    try:
                                        df = pd.DataFrame(data, columns=cols if cols else None)
                                        if cols:
                                            df.set_index(cols[0], inplace=True)
                                        st.line_chart(df)
                                    except Exception as e:
                                        st.error(f"Failed to render simulation chart: {e}")

                            st.write("Tool Result:")
                            st.json(result)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(result)
                            })
                            # Persist tool call result as a separate message so that
                            # the exported chat log fully reconstructs the dialogue.
                            tool_msg = {
                                "role": "tool",
                                "name": fn_name,
                                "content": json.dumps(result),
                            }
                            st.session_state.messages.append(tool_msg)
                            if self.chat_logger:
                                self.chat_logger.add_message(tool_msg)

                            # Refresh overview in real time
                            refresh_session_overview()

                        except Exception as e:
                            st.error(f"Error calling {fn_name}: {e}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps({"error": str(e)})
                            })
                
                # Ensure tool_outputs have unique ids (defensive)
                filtered_outputs = []
                seen_ids_submit: set[str] = set()
                for entry in tool_outputs:
                    tcid = entry["tool_call_id"]
                    if tcid in seen_ids_submit:
                        continue
                    seen_ids_submit.add(tcid)
                    filtered_outputs.append(entry)

                new_handler = EventHandler(run_id=run_id, thread_id=thread_id)
                with self.client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=filtered_outputs,
                    event_handler=new_handler,
                ) as stream:
                    stream.until_done()

            def handle_requires_action_manual(self, data):
                """Handle tool calls manually - store for user approval."""
                nonlocal full_response
                
                # Store pending tool calls for manual approval
                st.session_state.pending_tool_calls = data.required_action.submit_tool_outputs.tool_calls
                st.session_state.current_run_id = data.id
                st.session_state.current_thread_id = data.thread_id
                
                # Update the response to indicate pending tools
                full_response += "\n\n🔧 **Tool calls pending your approval** (see below)"
                message_placeholder.markdown(full_response)

        try:
            run_assistant(
                client=st.session_state.client,
                session_state=st.session_state.core_session,
                user_prompt=prompt,
                system_prompt=st.session_state.system_prompt,
                event_handler=EventHandler()
            )
            
            message_placeholder.markdown(full_response)
            if full_response:
                assistant_msg = {"role": "assistant", "content": full_response}
                st.session_state.messages.append(assistant_msg)
                
                if chat_logger:
                    chat_logger.add_message(assistant_msg)
            
            # Since we don't get the full message history back anymore,
            # we need to retrieve it manually if we want to repopulate the UI state.
            # For now, we've just appended our own messages.

        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
            st.error(f"An error occurred: {e}")

# ---------------------------------------------------------------------------
#  Session overview (read-only) panel (updates live via placeholder)
# ---------------------------------------------------------------------------

def _render_session_overview(container):
    """Populate *container* with the current SessionState snapshot."""
    container.empty()  # clear previous content
    sess = st.session_state.core_session
    with container.container():        
        st.write(f"**Selected library:** {sess.get_current_library_id() or '—'}")
    
        # gather some specs from the selected library
        if sess.get_current_library_id():
            lib_manager = sess.get_library_manager()
            lib_specs = lib_manager.get_library_specs(sess.get_current_library_id())
            st.write("**Library specs:**")
            st.json(lib_specs)

        if sess.get_design_spec():
            st.write("**Design spec:**")
            st.markdown(sess.get_design_spec()[:400] + (" …" if len(sess.get_design_spec()) > 400 else ""))

        verilog = sess.get_verilog_code()
        if verilog:
            st.write("**Current Verilog:**")
            st.code("\n".join(verilog.splitlines()), language="verilog")
        else:
            st.write("**Current Verilog:** —")

    with container.container():
        # Display SBML file path if present
        if sess.design_state.sbml_file:
            st.write("**SBML file:**")
            st.code(str(sess.design_state.sbml_file))
        # Show the parameter template if it exists
        if sess.design_state.parameter_template:
            st.write("**Parameter template:**")
            st.json(sess.design_state.parameter_template)

        # ------------------------------------------------------------------
        #  Generated files section
        # ------------------------------------------------------------------
        if sess.generated_files:
            st.write("**Generated files:**")
            import uuid as _uuid_dl
            for f in sess.generated_files:
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
    st.title("Genetic Design Assistant")
    
    # with st.expander("View System Prompt"):
    #     st.markdown(f"```\n{st.session_state.system_prompt}\n```")

    draw_sidebar()

    # --- Main chat area ---
    display_chat()

    # Example prompt form
    if st.session_state.get("loaded_prompt"):
        with st.form("loaded_prompt_form"):
            prompt_text = st.text_area("Loaded Example Prompt:", value=st.session_state.loaded_prompt, height=150)
            submitted = st.form_submit_button("Send Prompt")
            if submitted:
                st.session_state.loaded_prompt = None
                handle_chat_submission(prompt_text)

    # Free-form chat input
    if prompt := st.chat_input("What would you like to design?"):
        handle_chat_submission(prompt)

if __name__ == "__main__":
    main() 