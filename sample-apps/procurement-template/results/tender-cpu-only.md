# System description for tender

Generated from the HPC system description schema (version `0.5.0`).
Fields marked *(optional)* may be left empty; all others are mandatory.
Suggested values are examples from the schema, not an enumeration: a vendor
may answer with any value of the given type.

Blocks marked 1..N repeat, once per object they describe. Blocks marked 0..N are
left empty when the system has none of that component -- a CPU-only procurement
keeps the accelerator block and marks it not applicable, rather than deleting it,
so that one questionnaire covers every system and no answer goes into free text.


### System

*Occurrence:* once.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `installed_at` | string | `2024-06-01T00:00:00Z`, `2023-03-15T00:00:00Z`, `2022-11-01T00:00:00Z` |
| `location` | string | `Jülich, Germany`, `Berkeley, CA`, `Oak Ridge, TN`, `Espoo, Finland` |
| `name` | string | `JUPITER Booster`, `Perlmutter`, `Frontier`, `LUMI` |
| `parts` | SystemPart[] |  |
| `provider` | Provider |  |
| `schema_version` | string | `0.5.0` |
| `version` | string | `1.0.0`, `1.0.1`, `1.1.0` |
| `website` *(optional)* | string | `https://juwel.fz-juelich.de`, `https://perlmutter.nersc.gov`, `https://www.lumi-supercomputer.eu` |

### Part

*Occurrence:* 1..N -- repeat for every partition of the system.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `id` | string | `sys-a1b2c3d4e5f6`, `part-cpu-001`, `part-gpu-001`, `part-storage-001` |
| `name` | string | `Compute Partition`, `Login Partition`, `Storage Partition`, `GPU Partition` |
| `part_type` | string | `compute`, `other`, `storage` |
| `accepted_at` *(optional)* | string | `2025-02-01T00:00:00Z` |
| `cooling` *(optional)* | Cooling |  |
| `funders` *(optional)* | string[] | `BMFTR`, `DOE`, `NSF` |
| `inherits_from` *(optional)* | string | `compute-partition-1`, `gpu-partition-main`, `storage-partition-1` |
| `installed_at` *(optional)* | string | `2024-06-01T00:00:00Z` |
| `network` *(optional)* | GlobalNetwork[] |  |
| `node_count` *(optional)* | integer | `4096`, `128`, `16`, `1024` |
| `node_types` *(optional)* | NodeDesign[] |  |
| `other_type_name` *(optional)* | string | `login`, `management`, `interconnect`, `service` |
| `physical_location` *(optional)* | PhysicalLocation |  |
| `power_details` *(optional)* | object |  |
| `power_draw_average` *(optional)* | QuantityWithUnit | `350 kW`, `1.5 MW` |
| `power_draw_peak` *(optional)* | QuantityWithUnit | `500 kW`, `2 MW` |
| `product_name` *(optional)* | string | `Apollo 6500`, `PowerEdge C6525`, `ThinkSystem SR670` |
| `provider` *(optional)* | string | `HPE`, `Dell`, `Lenovo`, `Supermicro`, … |
| `software_stack` *(optional)* | SoftwareStack |  |
| `storage_system` *(optional)* | Storage |  |

### Node type

*Occurrence:* 1..N -- repeat for every node type in a part.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `cpus` | CPU[] |  |
| `id` | string | `node-std-001`, `node-gpu-a100`, `node-hmem-001` |
| `memory` | Memory[] |  |
| `node_type_name` | string | `standard-node`, `highmem-node`, `gpu-node`, `login-node` |
| `accelerators` *(optional)* | Accelerator[] |  |
| `inherits_from` *(optional)* | string | `standard-node`, `gpu-node`, `highmem-node` |
| `network` *(optional)* | NetworkAdapter[] |  |
| `node_count` *(optional)* | integer | `4096`, `128`, `16`, `1024` |
| `numa_topology` *(optional)* | NumaDomain[] |  |
| `on_node_storage` *(optional)* | Storage[] |  |

### CPU

*Occurrence:* 1..N -- repeat per socket; a node with two sockets answers twice.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `cores_per_cpu` | integer | `64`, `96`, `128`, `32` |
| `id` | string | `cpu-epyc-9654`, `cpu-xeon-8480`, `cpu-graviton3` |
| `manufacturer` | string | `AMD`, `Intel`, `ARM`, `IBM`, … |
| `name` | string | `EPYC 9654`, `Xeon Platinum 8480+`, `Graviton 3`, `A64FX` |
| `threads_per_core` | integer | `1`, `2` |
| `architecture` *(optional)* | string | `Zen 4`, `Sapphire Rapids`, `Ampere`, `Ponte Vecchio`, … |
| `base_frequency` *(optional)* | QuantityWithUnit | `2.4 GHz` |
| `cache_hierarchy` *(optional)* | CacheLevel[] |  |
| `cpu_to_cpu_link` *(optional)* | Link | `{'type': 'UPI', 'bandwidth': {'quantity': 112, 'unit': 'GB/s'}}`, `{'type': 'QPI', 'bandwidth': {'quantity': 64, 'unit': 'GB/s'}}`, `{'type': 'Infinity Fabric', 'bandwidth': {'quantity': 256, 'unit': 'GB/s'}}` |
| `isa` *(optional)* | string | `x86_64`, `ARMv8`, `ARMv9`, `RISC-V`, … |
| `max_frequency` *(optional)* | QuantityWithUnit | `3.7 GHz` |
| `number_of_sockets` *(optional)* | integer | `1`, `2`, `4` |
| `power_modes` *(optional)* | string[] | `Performance`, `Balanced`, `Power Saving` |
| `sku` *(optional)* | string | `EPYC 9654`, `Xeon Platinum 8480`, `Neoverse V2` |
| `tdp` *(optional)* | QuantityWithUnit | `280 W` |

### Memory

*Occurrence:* 1..N -- repeat per memory tier (e.g. DDR and HBM).

| Field | Type | Answer (suggested values) |
|---|---|---|
| `amount` | QuantityWithUnit |  |
| `id` | string | `mem-ddr5-4800`, `mem-hbm3-80gb`, `mem-gddr6-24gb` |
| `type` | string | `DDR4-3200`, `DDR5-4800`, `HBM2e`, `HBM3`, … |
| `bandwidth` *(optional)* | QuantityWithUnit | `800 GB/s` |
| `memory_channels` *(optional)* | integer | `8`, `6`, `4`, `1` |
| `memory_pieces` *(optional)* | integer | `48`, `16`, `8`, `32` |
| `numa_domains` *(optional)* | integer | `1`, `2`, `4`, `8` |

### Network adapter

*Occurrence:* 0..N -- repeat per adapter kind in a node.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `id` | string | `net-hpe-slingshot`, `net-mlx-ndr`, `net-cisco-200g` |
| `type` | string | `HPE Slingshot-11`, `InfiniBand NDR`, `InfiniBand HDR`, `Ethernet 200GbE` |
| `adapter_to_switch_link` *(optional)* | Link |  |
| `adapters_per_node` *(optional)* | integer | `1`, `2`, `4` |
| `cpu_to_network_link` *(optional)* | Link |  |
| `manufacturer` *(optional)* | string | `HPE`, `Mellanox`, `NVIDIA`, `Cisco` |
| `model` *(optional)* | string | `SL-11-200G-Adapter`, `ConnectX-6 Dx`, `BlueField-3` |

### Link

*Occurrence:* 0..N -- repeat per link kind.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `bandwidth` | QuantityWithUnit | `200 Gb/s` |
| `id` | string | `link-pcie5-x16`, `link-nvlink4`, `link-infinity-fabric` |
| `type` | string | `PCIe 5.0 x16`, `PCIe 4.0 x16`, `NVLink 4.0`, `Infinity Fabric`, … |

### Storage

*Occurrence:* 0..N -- repeat per file system.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `id` | string | `stor-nvme-001`, `stor-lustre-001`, `stor-ssd-local` |
| `name` | string | `ParFi`, `ExaJUST` |
| `type` | string | `NVMe`, `NVMe-oF`, `SATA SSD`, `SAS SSD`, … |
| `amount_per_node` *(optional)* | QuantityWithUnit | `3 PB` |
| `bandwidth` *(optional)* | QuantityWithUnit | `2.1 TB/s` |
| `blocksize` *(optional)* | QuantityWithUnit | `4 MB` |
| `cpu_to_storage_link` *(optional)* | Link |  |
| `iops` *(optional)* | integer | `100000`, `500000`, `1000000` |
| `manufacturer` *(optional)* | string | `IBM`, `Weka`, `VAST` |
| `product_name` *(optional)* | string | `Super Store 3000` |
| `storage_role` *(optional)* | string | `local`, `parallel`, `archive`, `home`, … |
| `total_amount` *(optional)* | QuantityWithUnit | `30 PB` |

### Global network

*Occurrence:* 0..1 -- one per part.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `id` | string | `net-hs-001`, `net-admin-001`, `net-storage-001` |
| `name` | string | `Admin network`, `High-Speed Network`, `IB net` |
| `type` | string | `HPE Slingshot-11`, `InfiniBand NDR`, `InfiniBand HDR`, `Ethernet 200GbE` |
| `adapters_per_node` *(optional)* | integer | `1`, `2`, `4` |
| `bisection_bandwidth` *(optional)* | QuantityWithUnit | `1.2 PB/s` |
| `manufacturer` *(optional)* | string | `HPE`, `Mellanox`, `NVIDIA`, `Cisco` |
| `sku` *(optional)* | string | `SL-11-200G`, `IB-NDR-400G`, `ETH-200G` |
| `topology` *(optional)* | string | `Dragonfly+`, `Fat Tree`, `Torus`, `Mesh`, … |
| `topology_parts` *(optional)* | TopologyPart[] |  |

### Topology part

*Occurrence:* 0..N -- repeat per topology segment.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `bandwidth_per_link` | Link | `200 Gb/s` |
| `id` | string | `top-rack-001`, `top-group-001`, `top-dragonfly-001` |
| `name` | string | `Rack-local network`, `Global network`, `Dragonfly+ Group` |
| `bisection_bandwidth` *(optional)* | QuantityWithUnit | `1.9 TB/s` |
| `features` *(optional)* | string[] | `Adaptive Routing`, `SHARP` |
| `rail_type` *(optional)* | string | `Full Rail`, `Partial Rail`, `Optimized Rail` |
| `total_links` *(optional)* | integer | `100`, `1000` |
| `total_switches` *(optional)* | integer | `1000` |

### Cooling

*Occurrence:* 0..1 -- one per part.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `capacity` *(optional)* | QuantityWithUnit | `20 MW` |
| `efficiency` *(optional)* | number | `1.05` |
| `type` *(optional)* | string | `liquid`, `DLC`, `air`, `immersion` |

### Physical location

*Occurrence:* 0..1 -- one per part.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `datacenter` *(optional)* | string | `North`, `South`, `DC1`, `Building A` |
| `hall` *(optional)* | string | `Hall 1`, `Hall 2`, `Main Hall` |
| `rack` *(optional)* | string | `R001`, `R002`, `A1`, `B5` |
| `row` *(optional)* | string | `Row A`, `Row B`, `Row 1`, `Row 2` |
| `site` *(optional)* | string | `Jülich`, `Berkeley`, `Oak Ridge`, `Edinburgh` |
| `unit` *(optional)* | string | `U1-U42`, `U10-U20`, `Top`, `Bottom` |

### Software stack

*Occurrence:* 0..1 -- one per part.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `system_software` | SystemSoftware |  |
| `user_software` *(optional)* | UserSoftware |  |

### Provider

*Occurrence:* once.

| Field | Type | Answer (suggested values) |
|---|---|---|
| `name` | string | `Jülich Supercomputing Centre`, `NERSC`, `OLCF`, `CSC` |
| `location` *(optional)* | string | `Jülich, Germany`, `Berkeley, CA`, `Oak Ridge, TN`, `Espoo, Finland` |
| `persistent_identifier` *(optional)* | object | `{'ror': '05a28rw58'}` |
| `website` *(optional)* | string | `https://www.fz-juelich.de/jsc`, `https://www.nersc.gov`, `https://www.olcf.ornl.gov` |
