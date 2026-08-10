# HPC System Description API

A lightweight, read-only REST API for querying HPC system descriptions.

## Overview

This tool creates a simple HTTP API that serves data from a JSON system description file (conforming to the system-definition schema v0.5.0). It's designed for quick exploration and testing of system data without requiring a full database or complex infrastructure.

## Features

- **Zero database** - Reads directly from JSON file
- **Lightweight** - Single Python file, minimal dependencies (Flask only)
- **RESTful API** - Clean, hierarchical endpoints
- **Read-only** - Safe for sharing and testing
- **Instant startup** - No migrations or initialization required

## Installation

Short:

```bash
uv run sample-apps/api/main.py descriptions/system-jupiter.json
```

Longer:

```bash
cd sample-apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py ../../descriptions/system-jupiter.json --port=9000 --host=0.0.0.0 --debug
```

## Usage

### Command-line Options

```
usage: main.py [-h] [--port PORT] [--host HOST] [--debug] system_file

positional arguments:
  system_file    Path to the system description JSON file

options:
  -h, --help     show this help message and exit
  --port PORT    Port to run the API on (default: 8080)
  --host HOST    Host to bind to (default: 127.0.0.1)
  --debug        Enable debug mode
```

## API Endpoints

### System Information

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check |
| `/system` | GET | Full system description (entire JSON) |
| `/system/name` | GET | System name |
| `/system/provider` | GET | Provider information |
| `/system/location` | GET | System location |

### Parts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/system/parts` | GET | List all parts with IDs and types |
| `/system/parts/<id>` | GET | Get specific part by ID |
| `/system/parts/<id>/nodes` | GET | List node types in a part |
| `/system/parts/<id>/nodes/<type_id>` | GET | Get specific node type |
| `/system/parts/<id>/nodes/<type_id>/cpus` | GET | List CPUs in node type |
| `/system/parts/<id>/nodes/<type_id>/memory` | GET | List memory configurations |
| `/system/parts/<id>/nodes/<type_id>/accelerators` | GET | List accelerators (GPUs) |

### Statistics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | System statistics (node count, CPU/GPU totals) |

## Examples

### Using curl

```bash
# Start the server in one terminal
python main.py ../../descriptions/system-jupiter.json

# In another terminal:

# Health check
curl http://127.0.0.1:8080/health

# Get system name
curl http://127.0.0.1:8080/system/name

# Get all parts
curl http://127.0.0.1:8080/system/parts

# Get specific part (JUPITER Booster)
curl http://127.0.0.1:8080/system/parts/part-jupiter-booster

# Get node types for Booster part
curl http://127.0.0.1:8080/system/parts/part-jupiter-booster/nodes

# Get CPUs for GPU node type
curl http://127.0.0.1:8080/system/parts/part-jupiter-booster/nodes/node-jupiter-booster-gpu/cpus

# Get memory configurations
curl http://127.0.0.1:8080/system/parts/part-jupiter-booster/nodes/node-jupiter-booster-gpu/memory

# Get GPU information
curl http://127.0.0.1:8080/system/parts/part-jupiter-booster/nodes/node-jupiter-booster-gpu/accelerators

# Get system statistics
curl http://127.0.0.1:8080/stats

# Prettify output
curl http://127.0.0.1:8080/stats | python -m json.tool
```

## Response Format

All responses are JSON with appropriate HTTP status codes:

- **200 OK** - Successful request
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

### Example Responses

```json
// GET /system/name
{
  "name": "JUPITER"
}

// GET /system/parts
{
  "count": 4,
  "parts": [
    {"id": "part-jupiter-booster", "name": "JUPITER Booster", "type": "compute"},
    {"id": "part-jupiter-booster-login", "name": "JUPITER Login Nodes", "type": "other"},
    {"id": "part-jupiter-storage-exastore", "name": "JUPITER Storage (ExaSTORE)", "type": "storage"},
    {"id": "part-jupiter-storage-exaflash", "name": "JUPITER Storage (ExaFLASH)", "type": "storage"}
  ]
}

// GET /stats
{
  "system_name": "JUPITER",
  "schema_version": "0.5.0",
  "parts_count": 4,
  "total_nodes": 5919,
  "total_cpus": 23536,
  "total_gpus": 23536,
  "parts": [
    {"id": "part-jupiter-booster", "name": "JUPITER Booster", "type": "compute", "node_count": 5884},
    {"id": "part-jupiter-booster-login", "name": "JUPITER Login Nodes", "type": "other", "node_count": 12},
    {"id": "part-jupiter-storage-exastore", "name": "JUPITER Storage (ExaSTORE)", "type": "storage", "node_count": 20},
    {"id": "part-jupiter-storage-exaflash", "name": "JUPITER Storage (ExaFLASH)", "type": "storage", "node_count": 3}
  ]
}
```

## Use Cases

1. **Quick Data Exploration** - Browse system descriptions without parsing JSON manually
2. **Testing** - Validate system description structure
3. **Documentation** - Generate API documentation for system data
4. **Prototyping** - Build frontend tools on top of system data
5. **Education** - Teach HPC system architecture concepts

## Limitations

- **Read-only** - Cannot modify system data
- **Single system** - Only one system description loaded at a time
- **In-memory** - Data is lost when server stops

## Development

### Running in Debug Mode

```bash
python main.py ../../descriptions/system-jupiter.json --debug
```

Debug mode provides:
- Auto-reload on code changes
- Interactive debugger in browser
- Detailed error messages

### Adding New Endpoints

Edit `main.py` and add new route handlers:

```python
@app.route('/system/parts/<part_id>/node_count', methods=['GET'])
def get_node_count(part_id: str):
    """Return node count for a part."""
    if not SYSTEM_DATA:
        return jsonify({'error': 'No system loaded'}), 404
    parts = SYSTEM_DATA.get('parts', [])
    part = next((p for p in parts if p.get('id') == part_id), None)
    if not part:
        return jsonify({'error': f'Part not found: {part_id}'}), 404
    return jsonify({'node_count': part.get('node_count', 0)})
```

## License

MIT License - See LICENSE file for details.
