"""
Helps fix "unable to serialize" errors when returning data from swmmio.
Turns all numpy data types into regular ones.
"""
import json
import numpy as np

def safe_json(obj):
    """Helps fix "unable to serialize" errors when returning data from swmmio."""
    j = json.dumps(obj, cls=NpEncoder, default=str)
    return json.loads(j)

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (np.floating, float)) and np.isnan(obj):
            return None
        return super(NpEncoder, self).default(obj)