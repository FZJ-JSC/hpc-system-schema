# HPC System Description Collecting Tools

A collection of tools that gather hardware information from a running HPC system
and format it according to the system-definition schema (v0.5.0).

This code is AI-generated.

## Overview

These tools automate the collection of system specifications that would otherwise
require manual lookup from vendor documentation. Each tool targets specific schema
fields and produces JSON output that can be merged into a system description.

**Usage:**
```bash
# Run all available collectors
python3 collect.py --output system-hardware.json

# Run specific collectors
python3 collect.py --tools lscpu,nvidia-smi --output partial.json

# Merge with an existing description
python3 collect.py --merge existing-description.json --output combined.json

# List available collectors
python3 collect.py --list
```

## Tool → Schema Field Mapping

| Tool | What it collects | Schema fields filled |
|------|-----------------|---------------------|
| `lscpu` | CPU model, cores, threads, sockets, cache, ISA, architecture | `CPU`, `CacheLevel` |
| `lstopo` | NUMA topology, cache hierarchy, GPU placement | `NumaDomain`, `CacheLevel` |
| `dmidecode` | Memory slots, DIMM sizes, speeds, board info | `Memory`, `SystemPart` |
| `numactl` | NUMA domains, per-domain memory, distance matrix | `NumaDomain` |
| `nvidia-smi` | GPU model, memory, cores, clock, power, count | `Accelerator` |
| `ibv_devinfo` | InfiniBand adapter model, ports, speed | `NetworkAdapter` |
| `ethtool` | Ethernet adapter speed, driver, features | `NetworkAdapter` |
| `perftest` | InfiniBand latency and bandwidth measurements | Network performance data |
| `lsblk` | Block devices: size, type, model, mount points | `Storage` |
| `lustre` | Lustre filesystem: OSTs, MDTs, capacity | `Storage` |
| `dd` | Disk I/O sequential read/write throughput | Performance metadata |
| `ipmitool` | BMC info, power readings, thermal sensors | `SystemPart`, `FurtherMetadata` |

## Detailed Tool Descriptions

### lscpu

Parses output of `lscpu` to extract CPU specifications.

**What it collects:**
- CPU manufacturer and model name
- Architecture (e.g., x86_64, aarch64)
- ISA (e.g., x86_64, ARMv8)
- Sockets, cores per socket, threads per core
- Base and max frequencies
- Cache sizes per level (L1d, L1i, L2, L3)

**Schema output:**
```json
{
  "cpus": [{
    "id": "cpu-0",
    "manufacturer": "AMD",
    "name": "EPYC 9654",
    "architecture": "Zen 4",
    "isa": "x86_64",
    "cores_per_cpu": 96,
    "threads_per_core": 2,
    "number_of_sockets": 2,
    "base_frequency": {"quantity": 2.4, "unit": "GHz"},
    "max_frequency": {"quantity": 3.7, "unit": "GHz"},
    "cache_hierarchy": [...]
  }]
}
```

**Requires:** `lscpu` (part of util-linux, available on all Linux)

---

### lstopo

Parses output of `lstopo --of text` (or `lstopo-no-graphics`) to extract
the NUMA topology tree as reported by hwloc.

**What it collects:**
- NUMA node count and layout
- Cache hierarchy (L1, L2, L3) with sizes
- GPU placement relative to NUMA domains
- CPU-to-NUMA domain assignment

**Schema output:**
```json
{
  "numa_topology": [{
    "id": "numa-0",
    "domain_id": 0,
    "memory_size": {"quantity": 256, "unit": "GB"},
    "associated_cpus": [0, 1, 2, 3, ...]
  }]
}
```

**Requires:** `lstopo` (part of hwloc package)

---

### dmidecode

Parses `dmidecode` output to extract detailed memory configuration
and system board information.

**What it collects:**
- Memory type (DDR4, DDR5, HBM)
- Total memory per socket
- DIMM count and speed
- Memory bandwidth (from speed ratings)
- Number of memory channels
- Board manufacturer and product name
- BIOS version and release date

**Schema output:**
```json
{
  "memory": [{
    "id": "mem-0",
    "amount": {"quantity": 512, "unit": "GB"},
    "type": "DDR5-4800",
    "memory_pieces": 16,
    "memory_channels": 8
  }]
}
```

**Requires:** `dmidecode` (root access typically required)

---

### numactl

Parses `numactl --hardware` output to extract NUMA topology details.

**What it collects:**
- Number of NUMA nodes
- Available CPUs per node
- Memory size per node
- NUMA distance matrix (latency between nodes)

**Schema output:**
```json
{
  "numa_topology": [{
    "id": "numa-0",
    "domain_id": 0,
    "memory_size": {"quantity": 256, "unit": "GB"},
    "associated_cpus": [0, 1, 2, 3, 4, 5, 6, 7, ...],
    "distance_matrix": {"0": "10", "1": "21"}
  }]
}
```

**Requires:** `numactl` (from numactl package)

---

### nvidia-smi

Parses `nvidia-smi --query-gpu=... --format=csv` to extract GPU specifications.

**What it collects:**
- GPU manufacturer (NVIDIA)
- GPU model name (e.g., H100, A100)
- Memory size and type (HBM2e, HBM3)
- CUDA cores / SM count
- Clock rates (base, boost)
- TDP / power limit
- Driver version
- GPU count per node

**Schema output:**
```json
{
  "accelerators": [{
    "id": "gpu-0",
    "kind": "GPU",
    "manufacturer": "NVIDIA",
    "name": "H100",
    "count_per_node": 4,
    "cores": 132,
    "clock_rate": {"quantity": 1980, "unit": "MHz"},
    "tdp": {"quantity": 700, "unit": "W"},
    "memory": {
      "id": "mem-gpu-hbm3",
      "amount": {"quantity": 80, "unit": "GB"},
      "type": "HBM3"
    }
  }]
}
```

**Requires:** `nvidia-smi` (from NVIDIA driver package)

---

### ibv_devinfo

Parses `ibv_devinfo` output to extract InfiniBand/RoCE adapter information.

**What it collects:**
- Adapter vendor and device name
- Port count and state
- Link speed (e.g., 200 Gb/s for NDR)
- Port width
- Active protocol

**Schema output:**
```json
{
  "network": [{
    "id": "net-ib-0",
    "type": "InfiniBand NDR",
    "manufacturer": "NVIDIA",
    "model": "ConnectX-7",
    "adapters_per_node": 4
  }]
}
```

**Requires:** `ibv_devinfo` (from rdma-core or libibverbs-utils)

---

### ethtool

Parses `ethtool <interface>` output to extract Ethernet adapter information.

**What it collects:**
- Adapter speed (e.g., 100 Gb/s)
- Driver name and version
- Link mode / duplex
- Offload features

**Schema output:**
```json
{
  "network": [{
    "id": "net-eth-0",
    "type": "Ethernet 100GbE",
    "bandwidth": {"quantity": 100, "unit": "Gb/s"}
  }]
}
```

**Requires:** `ethtool` (from ethtool package)

---

### perftest

Parses output from InfiniBand perftest benchmarks (ib_write_bw, ib_read_lat,
etc.) to collect network performance data.

**What it collects:**
- Unidirectional bandwidth (Gb/s)
- Bidirectional bandwidth (Gb/s)
- Latency (microseconds)
- Message sizes tested

**Usage:**
```bash
# Run on server node:
ib_write_bw -d mlx5_0 -s 1048576 --report_gbits

# On client node:
ib_write_bw -d mlx5_0 -s 1048576 --report_gbits <server_ip>
```

**Schema output:** Stored in `FurtherMetadata` as performance data.

---

### lsblk

Parses `lsblk -J -b -o ...` (JSON output) to extract block device information.

**What it collects:**
- Device names and sizes
- Device type (disk, partition, loop)
- Model and vendor
- Filesystem type and mount point
- Serial number

**Schema output:**
```json
{
  "on_node_storage": [{
    "id": "stor-nvme-0",
    "name": "Local NVMe",
    "type": "NVMe",
    "amount_per_node": {"quantity": 960, "unit": "GB"},
    "storage_role": "boot"
  }]
}
```

**Requires:** `lsblk` (part of util-linux)

---

### lustre

Parses Lustre filesystem information from `lfs df`, `lfs getstripe`, and
`lctl get_param` commands.

**What it collects:**
- OST (Object Storage Target) count and sizes
- MDT (Metadata Target) count
- Total and available filesystem size
- Stripe size and count settings
- MGS (Management Service) node

**Schema output:**
```json
{
  "storage_system": {
    "id": "stor-lustre-0",
    "name": "Parallel Filesystem",
    "type": "Lustre",
    "total_amount": {"quantity": 40, "unit": "PB"}
  }
}
```

**Requires:** Lustre client tools (`lfs`, `lctl`)

---

### dd

Runs a sequential I/O benchmark using `dd` to measure disk throughput.

**What it collects:**
- Sequential write bandwidth (MB/s)
- Sequential read bandwidth (MB/s)
- Tested block size
- Tested file size

**Usage:**
```bash
# Write test (1GB file, 1M blocks):
dd if=/dev/zero of=testfile bs=1M count=1024 oflag=direct

# Read test:
dd if=testfile of=/dev/null bs=1M iflag=direct
```

**Schema output:** Stored in `FurtherMetadata` as performance data.

---

### ipmitool

Parses `ipmitool` output to extract BMC, power, and thermal information.

**What it collects:**
- BMC firmware version
- System manufacturer and model
- Board serial number
- Power consumption (current, peak)
- Thermal sensor readings
- Fan speeds and cooling info

**Schema output:**
```json
{
  "power_details": {
    "tdp_per_node_kw": 0.68,
    "comment": "Collected via IPMI sensors"
  },
  "cooling": {
    "type": "liquid",
    "comment": "Collected via IPMI"
  }
}
```

**Requires:** `ipmitool` (from ipmitool package, usually requires root)

---

## Running Individual Collectors

Each collector can be run standalone:

```bash
# CPU information
python3 collectors/lscpu.py --output cpu.json

# NUMA topology
python3 collectors/lstopo.py --output numa.json

# Memory configuration
python3 collectors/dmidecode.py --output memory.json

# GPU information
python3 collectors/nvidia-smi.py --output gpu.json

# InfiniBand adapter info
python3 collectors/ibv_devinfo.py --output network.json

# Storage devices
python3 collectors/lsblk.py --output storage.json

# Merge all collectors
python3 merge.py cpu.json memory.json gpu.json network.json storage.json --output node-type.json
```

## Typical Workflow

### 1. Collect on a live node

```bash
# Run all collectors (some may need root)
sudo python3 collect.py --output raw-data.json
```

### 2. Review the output

```bash
# Check what was collected
python3 collect.py --review raw-data.json
```

### 3. Merge with existing description

```bash
# Merge into an existing system description
python3 collect.py --merge ../../descriptions/system-jupiter.json \
    --output system-jupiter-updated.json
```

### 4. Edit remaining fields manually

Some fields cannot be auto-collected (names, comments, topology, funders,
etc.). Open the output in the schema editor or edit with a text editor to
fill in the remaining fields.

## Error Handling

- **Tool not found**: The collector prints a warning and skips that tool.
  Install the required package and re-run.
- **Permission denied**: Some tools (dmidecode, ipmitool) need root.
  Run with `sudo` or grant the user access via sudoers.
- **Partial data**: Collectors always produce output, even with partial data.
  Missing fields are omitted (not set to null) so they can be filled manually.

## Requirements

- Python 3.9+
- System tools installed on the target node (see per-tool requirements above)
- Root access recommended for dmidecode, ipmitool
