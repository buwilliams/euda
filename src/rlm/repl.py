"""
RLM REPL Environment

Sandboxed Python execution for memory exploration.
Based on the Recursive Language Models paper (arXiv:2512.24601v1).
"""

import signal
import traceback
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class ExecutionResult:
    """Result of executing code in the REPL."""
    output: str  # Captured print output
    error: Optional[str] = None  # Error message if execution failed
    final_answer: Optional[str] = None  # Extracted FINAL() result
    final_var_name: Optional[str] = None  # Variable name from FINAL_VAR()
    timed_out: bool = False


class TimeoutError(Exception):
    """Raised when execution exceeds timeout."""
    pass


class REPLEnvironment:
    """Sandboxed Python execution for memory exploration.

    Provides a safe environment where the LLM can write code to:
    - Search and filter memory entries
    - Use llm_query() for semantic analysis
    - Aggregate and synthesize findings
    """

    # Safe builtins that won't allow escape
    SAFE_BUILTINS = {
        # Type constructors
        'bool': bool,
        'int': int,
        'float': float,
        'str': str,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'frozenset': frozenset,
        'bytes': bytes,
        'bytearray': bytearray,

        # Iteration and sequences
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'reversed': reversed,
        'sorted': sorted,

        # Aggregation
        'len': len,
        'min': min,
        'max': max,
        'sum': sum,
        'any': any,
        'all': all,
        'abs': abs,
        'round': round,

        # Other safe operations
        'isinstance': isinstance,
        'issubclass': issubclass,
        'hasattr': hasattr,
        'getattr': getattr,
        'repr': repr,
        'hash': hash,
        'id': id,
        'type': type,
        'callable': callable,
        'iter': iter,
        'next': next,
        'slice': slice,

        # Exceptions (for catching)
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
        'IndexError': IndexError,
        'AttributeError': AttributeError,
        'StopIteration': StopIteration,

        # Constants
        'True': True,
        'False': False,
        'None': None,
    }

    # Blocked names that could allow escape
    BLOCKED_NAMES = {
        'exec', 'eval', 'compile', 'open', 'input',
        '__import__', '__builtins__', '__loader__', '__spec__',
        'globals', 'locals', 'vars', 'dir',
        'exit', 'quit', 'help', 'license', 'copyright', 'credits',
        'breakpoint', 'memoryview', 'object', 'property',
        'staticmethod', 'classmethod', 'super',
    }

    def __init__(self, memory: dict, llm_query_fn: Callable[[str], str]):
        """
        Initialize the REPL environment.

        Args:
            memory: Memory data structure with entries, by_date, metadata
            llm_query_fn: Function for recursive semantic queries
        """
        self.memory = memory
        self.llm_query_fn = llm_query_fn
        self.output_buffer: list[str] = []
        self.final_answer: Optional[str] = None
        self.final_var_name: Optional[str] = None

        # Build execution globals
        self.globals = self._build_globals()

    def _build_globals(self) -> dict:
        """Build the globals dict for code execution."""
        globals_dict = {}

        # Add safe builtins
        globals_dict['__builtins__'] = self.SAFE_BUILTINS.copy()

        # Add safe standard library modules
        import re
        import json
        import datetime
        import collections
        import itertools
        import math
        import string

        globals_dict['re'] = re
        globals_dict['json'] = json
        globals_dict['datetime'] = datetime
        globals_dict['collections'] = collections
        globals_dict['itertools'] = itertools
        globals_dict['math'] = math
        globals_dict['string'] = string

        # Add memory data
        globals_dict['memory'] = self.memory

        # Add llm_query function
        globals_dict['llm_query'] = self.llm_query_fn

        # Add custom print that captures output
        globals_dict['print'] = self._capture_print

        # Add FINAL functions for answer extraction
        globals_dict['FINAL'] = self._final
        globals_dict['FINAL_VAR'] = self._final_var

        return globals_dict

    def _capture_print(self, *args, **kwargs):
        """Capture print output to buffer."""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        output = sep.join(str(arg) for arg in args) + end
        self.output_buffer.append(output)

    def _final(self, answer: Any):
        """Mark the final answer."""
        self.final_answer = str(answer)
        self.output_buffer.append(f"[FINAL ANSWER]: {answer}\n")

    def _final_var(self, var_name: str):
        """Mark a variable as the final answer."""
        self.final_var_name = var_name
        if var_name in self.globals:
            value = self.globals[var_name]
            self.final_answer = str(value)
            self.output_buffer.append(f"[FINAL ANSWER from {var_name}]: {value}\n")
        else:
            self.output_buffer.append(f"[ERROR]: Variable '{var_name}' not found\n")

    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout."""
        raise TimeoutError("Execution timed out")

    def _validate_code(self, code: str) -> Optional[str]:
        """Check code for blocked operations. Returns error message if blocked."""
        # Simple name-based blocking
        for blocked in self.BLOCKED_NAMES:
            # Check for the blocked name as a whole word
            import re
            if re.search(rf'\b{blocked}\b', code):
                return f"Blocked operation: '{blocked}' is not allowed"

        # Block import statements for dangerous modules
        dangerous_modules = {'os', 'sys', 'subprocess', 'socket', 'shutil',
                           'pathlib', 'importlib', 'ctypes', 'multiprocessing',
                           'threading', 'asyncio', 'signal', 'pickle'}

        # Check import statements
        import_pattern = r'(?:from\s+(\w+)|import\s+(\w+))'
        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2)
            if module in dangerous_modules:
                return f"Blocked import: '{module}' is not allowed"

        return None

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Execute code with timeout.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            ExecutionResult with output, errors, and final answer
        """
        # Reset state
        self.output_buffer = []
        self.final_answer = None
        self.final_var_name = None

        # Validate code
        validation_error = self._validate_code(code)
        if validation_error:
            return ExecutionResult(
                output="",
                error=validation_error
            )

        # Set up timeout (Unix only)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(timeout)
        except (AttributeError, ValueError):
            # signal.SIGALRM not available on Windows
            pass

        try:
            # Execute the code
            exec(code, self.globals)

            output = ''.join(self.output_buffer)
            return ExecutionResult(
                output=output,
                final_answer=self.final_answer,
                final_var_name=self.final_var_name
            )

        except TimeoutError:
            return ExecutionResult(
                output=''.join(self.output_buffer),
                error=f"Execution timed out after {timeout} seconds",
                timed_out=True
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return ExecutionResult(
                output=''.join(self.output_buffer),
                error=error_msg
            )

        finally:
            # Cancel timeout
            try:
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass

    def reset(self):
        """Reset the environment state (keeps memory and llm_query)."""
        self.output_buffer = []
        self.final_answer = None
        self.final_var_name = None
        # Rebuild globals to clear any defined variables
        self.globals = self._build_globals()
