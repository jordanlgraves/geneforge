from src.tools.base_tool import Tool
import os
import dotenv
from typing import List, Dict, Any
import traceback
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# ---------------------------------------------------------------------------
#  Scientific search & utility tools
# ---------------------------------------------------------------------------

class ScientificSearchTool(Tool):
    name = "scientific_search"
    description = "Search scientific literature (Semantic Scholar) and return up-to-date paper metadata."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Free-text search string."},
            "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5},
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5):
        from src.integrations.scientific_search_integration import scientific_search
        try:
            papers = scientific_search(query, max_results=max_results)
            return {"success": True, "papers": papers}
        except Exception as exc:
            return {"error": str(exc)}


class ToolDocsQueryTool(Tool):
    name = "query_tool_docs"
    description = "Ask a question about a tool (e.g., 'cello', 'prod') and get an answer extracted from local documentation PDFs/texts."
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Tool identifier (cello, prod, rbs_calculator, etc.) to provide context for the query."},
            "query": {"type": "string", "description": "Natural language question to ask."},
        },
        "required": ["tool_name", "query"],
    }

    def _get_all_doc_paths(self) -> List[str]:
        """Finds all available tool documentation files in the 'docs/tools' directory."""
        doc_dir = "docs/tools"
        supported_ext = (".pdf", ".md", ".txt")
        paths = []
        if not os.path.isdir(doc_dir):
            return []
        for filename in os.listdir(doc_dir):
            if filename.endswith(supported_ext):
                paths.append(os.path.join(doc_dir, filename))
        return paths

    def execute(self, tool_name: str, query: str):
        """Delegates Q&A to a single, dynamically-created OpenAI Assistant with all docs."""
        import os
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Use session_state to cache a single assistant for all tool docs
        cache_key = "tooldoc_assistant"
        if hasattr(self.session_state, cache_key):
            assistant_id = getattr(self.session_state, cache_key)
        else:
            doc_paths = self._get_all_doc_paths()
            if not doc_paths:
                return {"error": "No documentation files found in docs/tools/."}

            try:
                # 1. Create a single vector store for all tool docs
                vector_store = client.beta.vector_stores.create(name="Tool Documentation Store")

                # 2. Upload all files and add them to the vector store
                file_streams = [open(path, "rb") for path in doc_paths]
                try:
                    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=vector_store.id, files=file_streams
                    )
                finally:
                    for f in file_streams:
                        f.close()
                
                if file_batch.status != 'completed':
                    return {"error": f"File upload failed with status: {file_batch.status}"}

                # 3. Create a single assistant for all docs
                assistant = client.beta.assistants.create(
                    name="Tool Documentation Assistant",
                    instructions="You are an expert Q&A bot. You answer questions about various software tools by consulting the documentation files provided to you. When answering, cite the relevant file.",
                    model="gpt-4o-mini",
                    tools=[{"type": "file_search"}],
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
                )
                assistant_id = assistant.id
                
                # Cache the single assistant for subsequent calls
                setattr(self.session_state, cache_key, assistant_id)

            except Exception as e:
                if DEBUG_MODE:
                    traceback.print_exc()
                return {"error": f"Failed to create OpenAI Assistant: {e}"}

        try:
            # Create a thread with the user's message
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Using the provided documents, please answer the following question about the '{tool_name}' tool: {query}",
                    }
                ]
            )

            # Run the assistant and poll for completion
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant_id,
            )

            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                if messages.data and messages.data[0].role == 'assistant':
                    msg_content = messages.data[0].content[0]
                    if hasattr(msg_content, 'text'):
                        answer = msg_content.text.value
                        citations = []
                        if hasattr(msg_content.text, 'annotations'):
                            for ann in msg_content.text.annotations:
                                if getattr(ann, 'type', '') == 'file_citation':
                                    citations.append(getattr(ann.file_citation, 'file_id', ''))
                        return {"success": True, "answer": answer, "citations": citations}
                return {"error": "Assistant finished but returned no message."}
            else:
                return {"error": f"Assistant run failed with status: {run.status}, reason: {getattr(run.last_error, 'message', 'Unknown')}"}

        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
            return {"error": f"An error occurred during assistant execution: {e}"}


# ------------------- Small utility tools -----------------------------

class TranslateDnaTool(Tool):
    name = "translate_dna"
    description = "Translate a DNA sequence to protein using standard genetic code (frame 1 unless specified)."
    parameters = {
        "type": "object",
        "properties": {
            "seq_dna": {"type": "string", "description": "DNA sequence (A/T/C/G)."},
            "frame": {"type": "integer", "description": "Reading frame offset 0-2", "default": 0},
        },
        "required": ["seq_dna"],
    }

    def execute(self, seq_dna: str, frame: int = 0):
        try:
            from Bio.Seq import Seq  # type: ignore
            from Bio.SeqUtils import seq3
        except ImportError:
            return {"error": "Biopython not installed. Please add biopython to requirements."}

        seq = Seq(seq_dna.upper().replace("\n", "").replace(" ", ""))
        if frame not in (0, 1, 2):
            return {"error": "Frame must be 0, 1 or 2."}

        trimmed_len = (len(seq) - frame) // 3 * 3
        sub_seq = seq[frame : frame + trimmed_len]
        protein = sub_seq.translate(to_stop=False)
        return {"success": True, "protein": str(protein)}


class GcContentTool(Tool):
    name = "gc_content"
    description = "Calculate GC percentage of a sequence (optionally sliding window)."
    parameters = {
        "type": "object",
        "properties": {
            "seq": {"type": "string", "description": "DNA sequence."},
            "window": {"type": "integer", "description": "Window size for sliding calculation"},
        },
        "required": ["seq"],
    }

    def execute(self, seq: str, window: int | None = None):
        seq = seq.upper().replace("\n", "").replace(" ", "")
        if not seq:
            return {"error": "Sequence empty"}
        def gc(s):
            return round((s.count("G") + s.count("C")) / len(s) * 100, 2)
        if window and window > 0 and window < len(seq):
            values = [gc(seq[i:i+window]) for i in range(0, len(seq)-window+1)]
            return {"success": True, "window": window, "gc_values": values}
        else:
            return {"success": True, "gc_percent": gc(seq)}


class SearchBioNumbersTool(Tool):
    name = "search_bio_numbers"
    description = "Search the BioNumbers database of useful biological numbers for parameters, constants and other values to complete and enrich biological models"
    parameters = {
        "type": "object", 
        "properties": {
            "query": {
                "type": "string", 
                "description": "The query to search for."
            }
        }, 
        "required": ["query"]
    }

    def execute(self, query: str):
        from src.integrations.bionumbers_integration import search_bionumbers   
        results = search_bionumbers(query)
        return {"success": True, "results": results}
    

class ArxivSearchTool(Tool):
    name = "arxiv_search"
    description = "Search the Arxiv database for scientific papers."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The query to search for."}
        },
        "required": ["query"]
    }

    def execute(self, query: str):
        from src.tools.li import ArxivToolSpec
        import openai

        openai.api_key = os.environ.get("OPENAI_API_KEY")
        from llama_index.agent import OpenAIAgent
        arxiv_tool = ArxivToolSpec()

        agent = OpenAIAgent.from_tools(
            arxiv_tool.to_tool_list(),
            verbose=True,
        )

        results = agent.chat(query)
        return {"success": True, "results": results}
    
class GetSessionStateTool(Tool):
    name = "get_session_state"
    description = "Get the state of the active session including which library is currently active, if there are design results attached, parameter values for simulations, etc."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    def execute(self):
        return {"success": True, "session_state": self.session_state.to_dict()}
    
    
class SequenceSimilarityTool(Tool):
    name = "sequence_similarity"
    description = "Return the similarity score by calculating the similarity between two sequences using the `PairwiseAligner` from the BioPython library. "
    parameters = {
        "type": "object",
        "properties": {
            "seq1": {"type": "string", "description": "The first sequence."},
            "seq2": {"type": "string", "description": "The second sequence."},
        },
    }
    
    def execute(self, seq1: str, seq2: str):
        from Bio import Align
        aligner = Align.PairwiseAligner()
        alignments = aligner.align(seq1, seq2)
        return {"success": True, "similarity": alignments.score}
    
class ReportAnswerTool(Tool):
    name = "report_answer"
    description = "Report the answer to the user. This is the final answer to the user's question."
    parameters = {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "The answer to the user."},
        },
        "required": ["answer"],
        "annotations": {
            "title": "Report Answer",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "strict": True
    }
    def execute(self, answer: str):
        return {"success": True, "answer": answer}