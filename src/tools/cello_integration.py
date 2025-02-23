# cello_integration.py
from core_algorithm.celloAlgo import CELLO3
import subprocess
import os
import time
import atexit
import logging
from typing import Dict, Optional

class CelloIntegration:
    def __init__(self, cello_args: Optional[Dict] = None, cello_config: Optional[Dict] = None):
        # Default configuration that can be overridden
        self.cello_args = {
            'v_name': '0x17.v',
            'ucf_name': 'Eco1C1G1T1.UCF.json',
            'in_name': 'Eco1C1G1T1.input.json',
            'out_name': 'Eco1C1G1T1.output.json',
            'verilogs_path': 'ext_repos/Cello-v2-1-Core/library/verilogs',
            'constraints_path': 'ext_repos/Cello-v2-1-Core/library/constraints',
            'out_path': 'outputs/cello_outputs'
        } if cello_args is None else cello_args

        self.cello_config = {
            'verbose': True,  # Enable detailed logging
            'print_iters': True,  
            'exhaustive': False,
            'test_configs': False,
            'log_overwrite': True,
            'total_iters': 1_000
        } if cello_config is None else cello_config

        self.java_process = None
        self.log_buffer = []
        self._setup_logging()
        self._start_minieugene_server()

    def _setup_logging(self):
        """Configure logging to capture Cello output"""
        self.logger = logging.getLogger('cello_integration')
        self.logger.setLevel(logging.INFO)
        
        # Handler to capture logs in memory
        class LogCaptureHandler(logging.Handler):
            def __init__(self, log_buffer):
                super().__init__()
                self.log_buffer = log_buffer

            def emit(self, record):
                self.log_buffer.append(self.format(record))

        # Add handlers for both file and memory capture
        file_handler = logging.FileHandler('outputs/cello_outputs/cello_run.log')
        capture_handler = LogCaptureHandler(self.log_buffer)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        capture_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(capture_handler)

    def _start_minieugene_server(self):
        """Start the MiniEugene Java server if not already running"""
        try:
            # Check if server is already running
            gateway_dir = os.path.join("ext_repos", "Cello-v2-1-Core", 
                                     "core_algorithm", "utils", "py4j_gateway")
            
            # Start the Java server as a subprocess
            self.java_process = subprocess.Popen(
                ["java", "-cp", 
                 ".:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src", 
                 "miniEugenePermuter"],
                cwd=gateway_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait briefly for server initialization
            time.sleep(2)
            atexit.register(self._stop_minieugene_server)  # Cleanup on exit
            
        except Exception as e:
            print(f"Failed to start MiniEugene server: {e}")
            raise

    def _stop_minieugene_server(self):
        """Stop the Java server process"""
        if self.java_process:
            self.java_process.terminate()
            try:
                self.java_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.java_process.kill()
            self.java_process = None

    def run_cello(self, verilog_code: str = None) -> Dict:
        """
        Run Cello with configured parameters and return results
        
        Args:
            verilog_code: Optional Verilog code to process. If provided, saves to temp file.
        
        Returns:
            Dict containing:
            - success: bool
            - log: str (captured log output)
            - results: Dict (Cello results including DNA design)
        """
        try:
            if verilog_code:
                # Save verilog code to temporary file
                verilog_path = os.path.join(self.cello_args['verilogs_path'], 
                                          self.cello_args['v_name'])
                os.makedirs(os.path.dirname(verilog_path), exist_ok=True)
                with open(verilog_path, 'w') as f:
                    f.write(verilog_code)

            self.logger.info("Starting Cello run with configuration: %s", self.cello_config)
            
            # Run Cello
            cello = CELLO3(**self.cello_args, options=self.cello_config)
            
            # Get output path
            output_path = os.path.join(self.cello_args['out_path'], 
                                     self.cello_args['v_name'])

            return {
                'success': True,
                'log': '\n'.join(self.log_buffer),
                'results': {
                    'output_path': output_path,
                    'dna_design': self._parse_cello_output(output_path)
                }
            }

        except Exception as e:
            self.logger.error(f"Cello run failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'log': '\n'.join(self.log_buffer),
                'error': str(e)
            }
        finally:
            self._stop_minieugene_server()

    def _parse_cello_output(self, output_path: str) -> Dict:
        """Parse Cello output files to extract design information"""
        results = {
            'sbol_file': None,
            'eugene_script': None,
            'dna_sequences': None,
            'activity_table': None,
            'circuit_score': None,
            'visualizations': [],
            'all_files_zip': None
        }

        # Check for expected files
        base_name = os.path.basename(output_path).replace('.v', '')
        search_patterns = {
            'sbol_file': f'{base_name}._pySBOL3.nt',
            'eugene_script': f'{base_name}._eugene.eug',
            'dna_sequences': f'{base_name}._dna-sequences.csv',
            'activity_table': f'{base_name}._activity-table.csv',
            'circuit_score': f'{base_name}._circuit-score.csv',
            'all_files_zip': f'{base_name}._all-files.zip'
        }

        # Find matching files
        for file_type, pattern in search_patterns.items():
            full_path = os.path.join(output_path, pattern)
            if os.path.exists(full_path):
                results[file_type] = full_path

        # Find visualizations
        vis_files = [
            f'{base_name}._response-plots.pdf',
            f'{base_name}._tech-mapping.pdf',
            f'{base_name}._dpl-sbol.pdf'
        ]
        results['visualizations'] = [
            os.path.join(output_path, f) for f in vis_files
            if os.path.exists(os.path.join(output_path, f))
        ]

        return results

if __name__ == "__main__":
    cello_args = {
        'v_name': '0x17.v',
        'ucf_name': 'Eco1C1G1T1.UCF.json',
        'in_name': 'Eco1C1G1T1.input.json',
        'out_name': 'Eco1C1G1T1.output.json',
        'verilogs_path': 'ext_repos/Cello-v2-1-Core/library/verilogs',
        'constraints_path': 'ext_repos/Cello-v2-1-Core/library/constraints',
        'out_path': 'outputs/cello_outputs'
    }
    cello_config ={
        'verbose': False,  # Print more info to console & log. See logging.config to change verbosity
        'print_iters': False,  # Print to console info on *all* tested iters (produces copious amounts of text)
        'exhaustive': False,  # Run *all* possible permutes to find true optimum score (*long* run time)
        'test_configs': False,  # Runs brief tests of all configs, producing logs and a csv summary of all tests
        'log_overwrite': True,  # Removes date/time from file name, allowing overwrite of logs
        'total_iters': 1_000  #
    }
    cello = CelloIntegration(cello_args, cello_config)
    cello.run_cello()
