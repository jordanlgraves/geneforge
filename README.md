# LLM-Based Cello Designer

This repository contains an implementation for LLM-based selection of UCF, input, and output files, as well as part selection for Cello, a genetic circuit design tool.

## Overview

The implementation provides a comprehensive solution for using Large Language Models (LLMs) to assist in the selection of appropriate files and genetic parts for Cello circuit design. It includes:

1. **File Selection**: Automatically selects appropriate UCF, input, and output files based on user requests.
2. **Part Selection**: Selects appropriate genetic parts (gates, sensors, reporters) based on user requests.
3. **Verilog Generation**: Generates Verilog code based on the selected parts and user requirements.
4. **Explanations**: Provides detailed explanations for why specific files and parts were selected.

## Directory Structure

```
.
├── README.md                   # This file
├── src/                        # Source code
│   ├── library/                # Library code
│   │   ├── llm_file_selector.py    # File selection functionality
│   │   ├── llm_part_selector.py    # Part selection functionality
│   │   └── llm_cello_designer.py   # Integration of file and part selection
│   └── demo.py                 # Demo script
└── data/                       # Data directory
    ├── ucf/                    # UCF files
    ├── input/                  # Input files
    └── output/                 # Output files
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/llm-cello-designer.git
   cd llm-cello-designer
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

To use the LLM-based Cello designer, you can run the demo script:

```bash
python src/demo.py --request "Design a circuit that senses arabinose and produces GFP using NOT and AND gates."
```

### Command-Line Arguments

The demo script supports the following command-line arguments:

- `--ucf-dir`: Directory containing UCF files (default: `data/ucf`)
- `--input-dir`: Directory containing input files (default: `data/input`)
- `--output-dir`: Directory containing output files (default: `data/output`)
- `--request`: User request for circuit design (default: `Design a circuit that senses arabinose and produces GFP using NOT and AND gates.`)
- `--llm-reasoning`: Optional LLM reasoning about file and part selection
- `--output-file`: File to save the results to (default: `demo_results.json`)
- `--generate-verilog`: Generate Verilog code for the selected parts

### Example

```bash
python src/demo.py --request "Design a circuit for E. coli that detects IPTG and produces RFP using NOR gates." --generate-verilog
```

## API Usage

You can also use the library programmatically:

```python
from library.llm_cello_designer import LLMCelloDesigner

# Initialize the designer
designer = LLMCelloDesigner(
    ucf_dir='data/ucf',
    input_dir='data/input',
    output_dir='data/output',
    organism_prefixes={
        "Escherichia coli": "Eco",
        "Bacillus subtilis": "Bsu",
        "Saccharomyces cerevisiae": "Sce"
    }
)

# Process a user request
user_request = "Design a circuit that senses arabinose and produces GFP using NOT and AND gates."
result = designer.process_user_request(user_request)

# Get explanations
explanations = designer.explain_selection(user_request)

# Generate Verilog code
verilog_code = designer.generate_verilog(user_request)
```

## File Selection

The `LLMFileSelector` class handles the selection of appropriate UCF, input, and output files based on user requests. It:

1. Scans directories for JSON files
2. Extracts metadata from each file
3. Determines file types based on filename patterns
4. Validates file selections for compatibility
5. Finds alternative files if the selected files are not valid

## Part Selection

The `LLMPartSelector` class handles the selection of appropriate genetic parts based on user requests. It:

1. Loads and categorizes parts from a UCF file
2. Extracts requirements from user requests using regex patterns
3. Selects appropriate gates, sensors, and reporters based on those requirements
4. Provides explanations for why specific parts were selected

## Integration

The `LLMCelloDesigner` class integrates the file selection and part selection functionality, providing a unified interface for LLM-based Cello circuit design. It:

1. Initializes both the file selector and part selector components
2. Processes user requests to select appropriate files and parts
3. Provides methods to get available files and parts
4. Generates explanations for why specific files and parts were selected
5. Includes a method to generate Verilog code based on the selected parts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.




