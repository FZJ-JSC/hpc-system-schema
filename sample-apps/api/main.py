#!/usr/bin/env python3
# /// script
# dependencies = [
#   "Flask>=3.0"
# ]
# ///
"""
system-api - A lightweight queryable API for HPC system descriptions.

Usage:
    python main.py <system.json> [--port=8080]

Example:
    python main.py ../../descriptions/system-jupiter.json --port=8080

The API provides read-only endpoints to query system information:
    GET /health                    - Health check
    GET /                          - API info
    GET /system                    - Full system description
    GET /system/name               - System name
    GET /system/provider           - Provider info
    GET /system/location           - Location
    GET /system/parts              - List of parts
    GET /system/parts/<id>         - Specific part
    GET /system/parts/<id>/nodes   - Node types for a part
    GET /system/parts/<id>/nodes/<type_id> - Specific node type
    GET /system/parts/<id>/nodes/<type_id>/cpus   - CPUs in node type
    GET /system/parts/<id>/nodes/<type_id>/memory - Memory in node type
    GET /system/parts/<id>/nodes/<type_id>/accelerators - GPUs/accelerators
    GET /stats                     - System statistics
"""

import argparse
import json
import os
import sys
from pathlib import Path
from flask import Flask, g, jsonify, request

app = Flask(__name__)
SYSTEM_DATA = None

# This is a mock service: the key travels with the repository on purpose.
# A real deployment reads it from the environment or a secret store.
API_KEY = os.environ.get('SYSTEM_API_KEY', 'mock-api-key')


# Markers are instructions to this service, not data: they are removed from
# every response, so neither view advertises what is hidden.
HELPER_KEYS = ('x-secret', 'x-secret-alternative-value')


def render_view(node, internal):
    """Render a description for one audience.

    In the public view, a field is dropped when the object that owns it carries
    {"x-secret": {"<field>": "private"}}. In both views the marker keys
    themselves are dropped; the values stay untouched, so authors keep writing
    plain numbers and paths.
    """
    if isinstance(node, dict):
        secret = node.get('x-secret') or {}
        alternatives = node.get('x-secret-alternative-value') or {}
        hidden = set() if internal else {k for k, level in secret.items()
                                         if level == 'private'}
        rendered = {}
        for key, value in node.items():
            if key in HELPER_KEYS:
                continue
            if key in hidden:
                # A private field with a publishable substitute is replaced, not
                # dropped: "roughly 6000" answers the question that 5884 would.
                if key in alternatives:
                    rendered[key] = alternatives[key]
                continue
            rendered[key] = render_view(value, internal)
        return rendered
    if isinstance(node, list):
        return [render_view(v, internal) for v in node]
    return node


@app.before_request
def _authorise():
    """An absent key means the public view; a wrong key is an error, not a
    silent downgrade -- silence would hide a broken client."""
    supplied = request.headers.get('X-API-Key')
    if supplied is None:
        g.internal = False
    elif supplied == API_KEY:
        g.internal = True
    else:
        return jsonify({'error': 'invalid API key'}), 401


@app.after_request
def _apply_view(response):
    if not response.is_json:
        return response
    response.set_data(json.dumps(render_view(response.get_json(),
                                             g.get('internal', False)), indent=2))
    return response


def load_system(path: str) -> dict:
    """Load a system description from a JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"System file not found: {path}")
    with open(p) as f:
        return json.load(f)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'system-api'})


@app.route('/', methods=['GET'])
def index():
    """API information endpoint."""
    return jsonify({
        'name': 'HPC System Description API',
        'version': '1.0.0',
        'system': SYSTEM_DATA.get('name', 'Unknown') if SYSTEM_DATA else 'Not loaded',
        'endpoints': [
            {'path': '/health', 'method': 'GET', 'desc': 'Health check'},
            {'path': '/system', 'method': 'GET', 'desc': 'Full system description'},
            {'path': '/system/name', 'method': 'GET', 'desc': 'System name'},
            {'path': '/system/provider', 'method': 'GET', 'desc': 'Provider info'},
            {'path': '/system/location', 'method': 'GET', 'desc': 'Location'},
            {'path': '/system/parts', 'method': 'GET', 'desc': 'List of parts'},
            {'path': '/system/parts/<id>', 'method': 'GET', 'desc': 'Specific part'},
            {'path': '/system/parts/<id>/nodes', 'method': 'GET', 'desc': 'Node types'},
            {'path': '/system/parts/<id>/nodes/<type_id>', 'method': 'GET', 'desc': 'Specific node type'},
            {'path': '/stats', 'method': 'GET', 'desc': 'System statistics'},
        ]
    })


@app.route('/system', methods=['GET'])
def get_system():
    """Return the full system description."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    return jsonify(SYSTEM_DATA)


@app.route('/system/name', methods=['GET'])
def get_name():
    """Return system name."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    return jsonify({'name': SYSTEM_DATA.get('name')})


@app.route('/system/provider', methods=['GET'])
def get_provider():
    """Return provider information."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    return jsonify({'provider': SYSTEM_DATA.get('provider')})


@app.route('/system/location', methods=['GET'])
def get_location():
    """Return system location."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    return jsonify({'location': SYSTEM_DATA.get('location')})


@app.route('/system/parts', methods=['GET'])
def get_parts():
    """Return list of all parts."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    return jsonify({
        'count': len(parts),
        'parts': [
            {'id': p.get('id'), 'name': p.get('name'), 'type': p.get('part_type')}
            for p in parts
        ]
    })


@app.route('/system/parts/<part_id>', methods=['GET'])
def get_part(part_id: str):
    """Return a specific part by ID."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    return jsonify(part)


@app.route('/system/parts/<part_id>/nodes', methods=['GET'])
def get_node_types(part_id: str):
    """Return node types for a specific part."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    node_types = part.get('node_types', [])
    return jsonify({
        'part_id': part_id,
        'count': len(node_types),
        'node_types': [
            {'id': nt.get('id'), 'name': nt.get('node_type_name')}
            for nt in node_types
        ]
    })


@app.route('/system/parts/<part_id>/nodes/<type_id>', methods=['GET'])
def get_node_type(part_id: str, type_id: str):
    """Return a specific node type."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    node_types = part.get('node_types', [])
    node_type = next((nt for nt in node_types if nt.get('id') == type_id), None)
    if not node_type:
        return jsonify({'error': f'Node type not found: {type_id}'}), 404
    return jsonify(node_type)


@app.route('/system/parts/<part_id>/nodes/<type_id>/cpus', methods=['GET'])
def get_cpus(part_id: str, type_id: str):
    """Return CPUs for a specific node type."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    node_types = part.get('node_types', [])
    node_type = next((nt for nt in node_types if nt.get('id') == type_id), None)
    if not node_type:
        return jsonify({'error': f'Node type not found: {type_id}'}), 404
    cpus = node_type.get('cpus', [])
    return jsonify({
        'part_id': part_id,
        'node_type_id': type_id,
        'count': len(cpus),
        'cpus': [
            {
                'id': c.get('id'),
                'manufacturer': c.get('manufacturer'),
                'name': c.get('name'),
                'cores_per_cpu': c.get('cores_per_cpu'),
                'number_of_sockets': c.get('number_of_sockets'),
            }
            for c in cpus
        ]
    })


@app.route('/system/parts/<part_id>/nodes/<type_id>/memory', methods=['GET'])
def get_memory(part_id: str, type_id: str):
    """Return memory configurations for a specific node type."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    node_types = part.get('node_types', [])
    node_type = next((nt for nt in node_types if nt.get('id') == type_id), None)
    if not node_type:
        return jsonify({'error': f'Node type not found: {type_id}'}), 404
    memory = node_type.get('memory', [])
    return jsonify({
        'part_id': part_id,
        'node_type_id': type_id,
        'count': len(memory),
        'memory': [
            {
                'id': m.get('id'),
                'type': m.get('type'),
                'amount': m.get('amount'),
                'bandwidth': m.get('bandwidth'),
            }
            for m in memory
        ]
    })


@app.route('/system/parts/<part_id>/nodes/<type_id>/accelerators', methods=['GET'])
def get_accelerators(part_id: str, type_id: str):
    """Return accelerators for a specific node type."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    node_types = part.get('node_types', [])
    node_type = next((nt for nt in node_types if nt.get('id') == type_id), None)
    if not node_type:
        return jsonify({'error': f'Node type not found: {type_id}'}), 404
    accelerators = node_type.get('accelerators', [])
    return jsonify({
        'part_id': part_id,
        'node_type_id': type_id,
        'count': len(accelerators),
        'accelerators': [
            {
                'id': a.get('id'),
                'kind': a.get('kind'),
                'manufacturer': a.get('manufacturer'),
                'name': a.get('name'),
                'count_per_node': a.get('count_per_node'),
                'memory': a.get('memory'),
            }
            for a in accelerators
        ]
    })


@app.route('/stats', methods=['GET'])
def get_stats():
    """Return system statistics."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    
    parts = SYSTEM_DATA.get('parts', [])
    total_nodes = 0
    total_cpus = 0
    total_gpus = 0
    part_stats = []
    
    for part in parts:
        part_info = {
            'id': part.get('id'),
            'name': part.get('name'),
            'type': part.get('part_type'),
            'node_count': part.get('node_count', 0),
        }
        total_nodes += part.get('node_count', 0)
        
        # Count CPUs and GPUs across node types
        for nt in part.get('node_types', []):
            cpus = nt.get('cpus', [])
            for cpu in cpus:
                sockets = cpu.get('number_of_sockets', 1)
                total_cpus += sockets
            
            accelerators = nt.get('accelerators', [])
            for acc in accelerators:
                count = acc.get('count_per_node', 0)
                total_gpus += count
        
        part_stats.append(part_info)
    
    return jsonify({
        'system_name': SYSTEM_DATA.get('name'),
        'schema_version': SYSTEM_DATA.get('schema_version'),
        'parts_count': len(parts),
        'total_nodes': total_nodes,
        'total_cpus': total_cpus,
        'total_gpus': total_gpus,
        'parts': part_stats,
    })


def main():
    parser = argparse.ArgumentParser(
        description='Lightweight API for querying HPC system descriptions'
    )
    parser.add_argument(
        'system_file',
        help='Path to the system description JSON file'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to run the API on (default: 8080)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    # Load the system
    try:
        global SYSTEM_DATA
        SYSTEM_DATA = load_system(args.system_file)
        print(f"Loaded system: {SYSTEM_DATA.get('name', 'Unknown')}")
        print(f"Schema version: {SYSTEM_DATA.get('schema_version', 'Unknown')}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.system_file}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run the API
    print(f"Starting API server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
