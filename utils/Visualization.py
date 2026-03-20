import dash
from dash import html, dcc, Input, Output
import threading
import sys
import logging
import socket

class _ThreadAwareIO:
    """IO wrapper that suppresses output from specific threads."""
    def __init__(self, original_stream, suppress_threads):
        self.original_stream = original_stream
        self.suppress_threads = suppress_threads  # Set of thread IDs to suppress

    def write(self, message):
        if threading.get_ident() not in self.suppress_threads:
            self.original_stream.write(message)
        return len(message)

    def flush(self):
        self.original_stream.flush()

    def __getattr__(self, name):
        return getattr(self.original_stream, name)

class VisualizationServer:
    def __init__(self, port=8050):
        self.port = self._find_available_port(port)
        self.app = None
        self.current_figure = None

    def _find_available_port(self, start_port=8050, max_attempts=100):
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                # Port is in use, try next one
                continue
        raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts}")

    def start(self):
        suppress_threads = set()

        def run_app():
            self.app = dash.Dash(__name__)
            self.app.layout = html.Div([
                html.H1("SWMM-MCP Visualization Panel"),
                dcc.Graph(id='visualization-graph', style={'height': '100%'} ),
                dcc.Interval(id='interval-component', interval=2000, n_intervals=0)
            ], style={'height': '90vh'})

            @self.app.callback(
                Output('visualization-graph', 'figure'),
                Input('interval-component', 'n_intervals')
            )
            def update_graph(n):
                return self.current_figure or {}

            # Add this thread to the suppression list
            suppress_threads.add(threading.get_ident())

            log = logging.getLogger('werkzeug')
            log.disabled = True

            self.app.run(port=self.port, debug=False, use_reloader=False, threaded=True)

        # Install thread-aware wrappers
        sys.stdout = _ThreadAwareIO(sys.__stdout__, suppress_threads)
        sys.stderr = _ThreadAwareIO(sys.__stderr__, suppress_threads)

        threading.Thread(target=run_app, daemon=True).start()
        
    def update_visualization(self, fig):
        self.current_figure = fig