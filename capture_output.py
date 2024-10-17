from contextlib import contextmanager, redirect_stdout, redirect_stderr
import io

class Out:
    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.stdout_str = ''
        self.stderr_str = ''
    def finalize(self):
        self.stdout_str = self.stdout.getvalue()
        self.stderr_str = self.stderr.getvalue()

@contextmanager
def capture_output(print_out = None, print_err = None):
    try:
        out = Out()
        with redirect_stdout(out.stdout), redirect_stderr(out.stderr):
            yield out
    finally:
        out.finalize()
        if callable(print_out): print_out(out.stdout_str)
        if callable(print_err): print_err(out.stderr_str)
