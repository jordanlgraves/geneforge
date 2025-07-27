# Genetic Circuit Design Examples

This directory contains examples demonstrating various capabilities of the GeneForge library.

## Library Selection Examples

### `library_selection_example.py` (Comprehensive Example)

This example demonstrates different approaches to library selection for genetic circuit design:

1. **Rule-based selection**: Fast pattern matching to extract requirements from user prompts
2. **LLM-based selection**: Uses large language models for sophisticated reasoning
3. **Tool-based selection**: Uses a flexible interface that can be backed by different selection strategies

The example contains all three approaches in a single script for easy comparison, with command-line options to focus on specific methods:

```bash
# Show all selection methods
python src/examples/library_selection_example.py

# Show only rule-based selection with detailed analysis
python src/examples/library_selection_example.py --method rule --detailed

# Show LLM-based selection with the GPT-4 model
python src/examples/library_selection_example.py --method llm --llm
```

### Legacy Examples (For Reference Only)

The following examples are retained for reference but are superseded by the comprehensive example:

- `llm_library_selection_example.py`: Original example showing LLM-based library selection
- `llm_ucf_selection_example.py`: Example showing how to select UCF files with simulated LLM reasoning

## Other Examples

### `cello_integration_example.py`

Demonstrates how to integrate with Cello for genetic circuit design:
- UCF library selection and management
- Verilog code synthesis
- DNA sequence generation

### `library_manager_example.py`

Shows how to use the `LibraryManager` class to:
- List available libraries
- Load library data
- Get library metadata
- Select libraries by ID or organism name

## Note on Consolidation

The examples were consolidated to:
1. Reduce redundancy and code duplication
2. Make it easier to compare different approaches
3. Provide a single, comprehensive reference example
4. Simplify maintenance of the codebase

When adding new examples, please follow these principles:
- Focus on demonstrating one specific capability
- Include clear documentation and comments
- Avoid duplicating functionality already demonstrated in other examples 