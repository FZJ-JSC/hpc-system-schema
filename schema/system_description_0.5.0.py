"""
System schemas using custom fields with x_suggested support.
"""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError, INCLUDE
from .custom_fields import (
    Str, Int, Float, Bool, List, Dict, Date, DateTime, Nested, Url,
    extract_x_suggested, schema_to_json_schema_dict
)
from marshmallow.validate import Length, Range, OneOf


class QuantityWithUnitSchema(Schema):
    """Schema for quantity with unit."""
    quantity = Float(required=True)
    unit = Str(required=True, validate=Length(min=1))


class FurtherMetadataSchema(Schema):
    """Free-form key-value metadata for extensibility."""
    class Meta:
        unknown = INCLUDE  # Accept arbitrary key-value pairs

    def dump(self, obj, *, many=None):
        """Passthrough dump — return the dict as-is."""
        many = many if many is not None else self.many
        if many:
            return [self._dump_one(o) for o in obj]
        return self._dump_one(obj)

    def _dump_one(self, obj):
        """Return the dict as-is for FurtherMetadata."""
        if isinstance(obj, dict):
            return dict(obj)
        return {}


class PersistentIdentifierSchema(Schema):
    """Persistent identifier for a provider (e.g. ROR)."""
    identifier_name = Str(x_suggested=["ROR", "ISNI", "VIAF", "Wikidata"],
                          comment="Type / name of the identifier")
    id = Str(x_suggested=["05a28rw58", "03w6m5361"],
             comment="Value of identifier (the actual ID)")


class ProviderSchema(Schema):
    """Hosting facility / provider information."""
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["Jülich Supercomputing Centre", "NERSC", "OLCF", "CSC"])
    location = Str(x_suggested=["Jülich, Germany", "Berkeley, CA", "Oak Ridge, TN", "Espoo, Finland"])
    persistent_identifier = Nested(PersistentIdentifierSchema, load_default=None)
    website = Url(x_suggested=["https://www.fz-juelich.de/jsc", "https://www.nersc.gov", "https://www.olcf.ornl.gov"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class LinkSchema(Schema):
    """Link specification schema."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["link-pcie5-x16", "link-nvlink4", "link-infinity-fabric"])
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["PCIe 5.0 x16", "PCIe 4.0 x16", "NVLink 4.0", "Infinity Fabric", "CXL 2.0"])
    bandwidth = Nested(QuantityWithUnitSchema, required=True, x_suggested={"quantity": 200, "unit": "Gb/s"})
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class CacheLevelSchema(Schema):
    """Cache level specification."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["cache-l1-data", "cache-l2-unified", "cache-l3-llc"])
    level_name = Str(required=True, validate=Length(min=1),
                     x_suggested=["L1", "L2", "L3", "LLC"])
    cache_type = Str(required=True, validate=Length(min=1),
                     x_suggested=["instruction", "data", "unified"])
    size = Nested(QuantityWithUnitSchema, required=True, x_suggested={"quantity": 2, "unit": "MB"})
    associativity = Str(x_suggested=["8-way", "16-way", "32-way", "direct-mapped", "fully-associative"])
    line_size = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 128, "unit": "B"})
    instances_per_cpu = Int(validate=Range(min=1), x_suggested=[1, 2, 4, 8])
    comment = Str(x_suggested=["Private L1", "Shared L3", "Last-level cache"])
    further_metadata = Nested(FurtherMetadataSchema)


class NumaDomainSchema(Schema):
    """NUMA domain specification."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["numa-domain-0", "numa-domain-1", "numa-socket0"])
    domain_id = Int(required=True, validate=Range(min=0), x_suggested=[0, 1, 2, 3])
    memory_size = Nested(QuantityWithUnitSchema, required=True, x_suggested={"quantity": 5, "unit": "GB"})
    associated_cpus = List(Int(), x_suggested=[0, 1, 2, 3, 4, 5, 6])
    distance_matrix = Dict()
    associated_accelerators = List(Int(), x_suggested=[0, 1])
    comment = Str(x_suggested=["NUMA Node 0", "NUMA Node 1", "Socket 0 Domain"])
    further_metadata = Nested(FurtherMetadataSchema)


class CPUSchema(Schema):
    """CPU specification schema."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["cpu-epyc-9654", "cpu-xeon-8480", "cpu-graviton3"])
    manufacturer = Str(required=True, validate=Length(min=1),
                       x_suggested=["AMD", "Intel", "ARM", "IBM", "Fujitsu"])
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["EPYC 9654", "Xeon Platinum 8480+", "Graviton 3"])
    sku = Str(x_suggested=["EPYC 9654", "Xeon Platinum 8480", "Neoverse V2"])
    architecture = Str(x_suggested=["Zen 4", "Sapphire Rapids", "Ampere", "Graviton"])
    isa = Str(x_suggested=["x86_64", "ARM64", "AArch64", "RISC-V"])
    cores_per_cpu = Int(required=True, validate=Range(min=1),
                        x_suggested=[64, 96, 128, 32])
    threads_per_core = Int(validate=Range(min=1), x_suggested=[1, 2])
    base_frequency = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 2.4, "unit": "GHz"})
    max_frequency = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 3.7, "unit": "GHz"})
    tdp = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 280, "unit": "W"})
    power_modes = List(Str(), x_suggested=["Performance", "Balanced", "Power Saving"])
    number_of_sockets = Int(validate=Range(min=1), x_suggested=[1, 2, 4])
    cpu_to_cpu_link = Nested(LinkSchema, x_suggested={"type": "UPI", "bandwidth": {"quantity": 112, "unit": "GB/s"}})
    cache_hierarchy = List(Nested(CacheLevelSchema))
    comment = Str()
    further_metadata = Nested(FurtherMetadataSchema)


class MemorySchema(Schema):
    """Memory specification schema."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["mem-ddr5-4800", "mem-hbm3-80gb", "mem-gddr6-24gb"])
    amount = Nested(QuantityWithUnitSchema, required=True)
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["DDR4-3200", "DDR5-4800", "HBM2e", "HBM3", "GDDR6"])
    bandwidth = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 800, "unit": "GB/s"})
    memory_pieces = Int(x_suggested=[48, 16, 8, 32])
    memory_channels = Int(validate=Range(min=1), x_suggested=[8, 12, 16, 6])
    numa_domains = Int(validate=Range(min=1), x_suggested=[1, 2, 4, 8])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class AcceleratorSchema(Schema):
    """Accelerator specification schema."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["acc-h100-80gb", "acc-mi300x", "acc-max1100"])
    kind = Str(required=True, validate=OneOf(['GPU', 'FPGA', 'ASIC', 'TPU', 'Other']),
               x_suggested=["GPU", "FPGA", "ASIC", "TPU"])
    manufacturer = Str(required=True, validate=Length(min=1),
                       x_suggested=["NVIDIA", "AMD", "Intel", "Xilinx", "Cerebras"])
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["A100-SXM4-40GB", "MI250X", "Max 1100"])
    sku = Str(x_suggested=["H100", "MI300X", "Max 1100"])
    architecture = Str(x_suggested=["Ampere", "Hopper", "CDNA2", "Ponte Vecchio"])
    isa = Str(x_suggested=["CUDA", "ROCm", "oneAPI", "OpenCL"])
    count_per_node = Int(required=True, validate=Range(min=1),
                         x_suggested=[1, 2, 4, 8])
    cores = Int(x_suggested=[5120, 6912, 1376, 1024])
    clock_rate = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 1.5, "unit": "GHz"})
    memory = Nested(MemorySchema, required=True)
    tdp = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 300, "unit": "W"})
    power_modes = List(Str(), x_suggested=["Performance", "Balanced", "Power Saving"])
    cpu_to_accelerator_link = Nested(LinkSchema, x_suggested={"type": "PCIe 5.0 x16", "bandwidth": {"quantity": 64, "unit": "GB/s"}})
    accelerator_to_accelerator_link = Nested(LinkSchema, x_suggested={"type": "NVLink 4", "bandwidth": {"quantity": 900, "unit": "GB/s"}})
    cache_hierarchy = List(Nested(CacheLevelSchema))
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class NetworkAdapterSchema(Schema):
    """Network adapter specification (node-level view)."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["net-hpe-slingshot", "net-mlx-ndr", "net-cisco-200g"])
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["HPE Slingshot-11", "InfiniBand NDR", "InfiniBand HDR", "Ethernet 200GbE"])
    manufacturer = Str(x_suggested=["HPE", "Mellanox", "NVIDIA", "Cisco"])
    model = Str(x_suggested=["SL-11-200G-Adapter", "ConnectX-6 Dx", "BlueField-3"])
    adapters_per_node = Int(validate=Range(min=1), load_default=1,
                            x_suggested=[1, 2, 4])
    adapter_to_switch_link = Nested(LinkSchema, x_suggested={"type": "PCIe 5.0 x16", "bandwidth": {"quantity": 64, "unit": "GB/s"}})
    cpu_to_network_link = Nested(LinkSchema, x_suggested={"type": "PCIe 5.0 x16", "bandwidth": {"quantity": 64, "unit": "GB/s"}})
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class TopologyPartSchema(Schema):
    """Topology component specification for global network."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["top-rack-001", "top-group-001", "top-dragonfly-001"])
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["Rack-local network", "Global network", "Dragonfly+ Group"])
    bandwidth_per_link = Nested(LinkSchema, required=True, x_suggested={"type": "InfiniBand NDR", "bandwidth": {"quantity": 200, "unit": "Gb/s"}})
    rail_type = Str(x_suggested=["Full Rail", "Partial Rail", "Optimized Rail"])
    total_links = Int(x_suggested=[100, 1000])
    bisection_bandwidth = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 1.9, "unit": "TB/s"})
    total_switches = Int(x_suggested=[1000])
    features = List(Str(), x_suggested=["Adaptive Routing", "SHARP"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class GlobalNetworkSchema(Schema):
    """Global network specification (part-level view)."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["net-hs-001", "net-admin-001", "net-storage-001"])
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["Admin network", "High-Speed Network", "IB net"])
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["HPE Slingshot-11", "InfiniBand NDR", "InfiniBand HDR", "Ethernet 200GbE"])
    manufacturer = Str(x_suggested=["HPE", "Mellanox", "NVIDIA", "Cisco"])
    sku = Str(x_suggested=["SL-11-200G", "IB-NDR-400G", "ETH-200G"])
    adapters_per_node = Int(validate=Range(min=1), load_default=1,
                            x_suggested=[1, 2, 4])
    topology = Str(x_suggested=["Dragonfly+", "Fat Tree", "Torus", "Mesh", "Hybrid"])
    topology_parts = List(Nested(TopologyPartSchema))
    bisection_bandwidth = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 1.2, "unit": "PB/s"})
    comment = Str(x_suggested=["Primary high-speed network", "Management network", "Storage network"])
    further_metadata = Nested(FurtherMetadataSchema)
class PhysicalLocationSchema(Schema):
    """Physical location specification for a part."""
    site = Str(required=True, validate=Length(min=1),
               x_suggested=["Jülich", "Berkeley", "Oak Ridge", "Edinburgh"])
    datacenter = Str(required=True, validate=Length(min=1),
                     x_suggested=["North", "South", "DC1", "Building A"])
    hall = Str(x_suggested=["Hall 1", "Hall 2", "Main Hall"])
    row = Str(x_suggested=["Row A", "Row B", "Row 1", "Row 2"])
    rack = Str(x_suggested=["R001", "R002", "A1", "B5"])
    unit = Str(x_suggested=["U1-U42", "U10-U20", "Top", "Bottom"])
    comment = Str(x_suggested=["Main compute hall", "GPU partition area", "Storage cluster"])
    further_metadata = Nested(FurtherMetadataSchema)


class CoolingSchema(Schema):
    """Cooling infrastructure specification."""
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["liquid", "DLC", "air", "immersion"])
    capacity = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 20, "unit": "MW"})
    efficiency = Float(validate=Range(min=0), x_suggested=[1.05])
    comment = Str(x_suggested=["Direct-to-chip liquid cooling", "Rear door heat exchangers", "Immersion cooling tank"])
    further_metadata = Nested(FurtherMetadataSchema)


class StorageSchema(Schema):
    """Storage specification schema."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["stor-nvme-001", "stor-lustre-001", "stor-ssd-local"])
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["NVMe", "NVMe-oF", "SATA SSD", "SAS SSD", "HDD", "Lustre"])
    manufacturer = Str(x_suggested=["IBM", "Weka", "VAST"])
    product_name = Str(x_suggested=["Super Store 3000"])
    name = Str(x_suggested=["ParFi", "ExaJUST"])
    amount_per_node = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 3, "unit": "PB"})
    total_amount = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 30, "unit": "PB"})
    bandwidth = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 2.1, "unit": "TB/s"})
    iops = Int(x_suggested=[100000, 500000, 1000000])
    storage_role = Str(x_suggested=["local", "parallel", "archive", "home", "scratch", "boot"])
    blocksize = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 4, "unit": "MB"})
    cpu_to_storage_link = Nested(LinkSchema, x_suggested={"type": "PCIe 5.0 x4", "bandwidth": {"quantity": 32, "unit": "GB/s"}})
    comment = Str(x_suggested=["Local NVMe cache", "Parallel filesystem", "Archive storage"])
    further_metadata = Nested(FurtherMetadataSchema)


class OSVersionSchema(Schema):
    """Operating system version."""
    type = Str(required=True, validate=Length(min=1),
               x_suggested=["Linux", "Windows", "FreeBSD", "AIX"])
    flavor = Str(x_suggested=["RHEL", "Ubuntu", "SLES", "Rocky", "Debian"])
    version = Str(required=True, validate=Length(min=1),
                  x_suggested=["8.6", "22.04", "15.3"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class FirmwareVersionSchema(Schema):
    """Firmware version."""
    component = Str(required=True, validate=Length(min=1),
                    x_suggested=["BIOS", "BMC", "NIC", "GPU"])
    version = Str(required=True, validate=Length(min=1),
                  x_suggested=["2.14.0", "2.80.00"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class SchedulerSchema(Schema):
    """Job scheduler."""
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["Slurm", "PBS Pro", "LSF", "Torque"])
    version = Str(required=True, validate=Length(min=1),
                  x_suggested=["22.05.9", "20.11.7", "10.1.0"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class SystemSoftwareSchema(Schema):
    """System-level software."""
    operating_system = Nested(OSVersionSchema, required=True)
    kernel_version = Str(x_suggested=["5.15.0-56-generic", "4.18.0-348.el8"])
    firmware_versions = List(Nested(FirmwareVersionSchema))
    scheduler = Nested(SchedulerSchema)
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class SoftwarePackageSchema(Schema):
    """Software package."""
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["GCC", "Intel OneAPI", "OpenMPI", "CUDA"])
    version = Str(required=True, validate=Length(min=1),
                  x_suggested=["12.2.0", "2023.2", "4.1.5"])
    variant = Str(x_suggested=["system", "module", "container", "source"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class UserSoftwareSchema(Schema):
    """User-level software."""
    compilers = List(Nested(SoftwarePackageSchema))
    libc_version = Str()
    mpis = List(Nested(SoftwarePackageSchema))
    blas = List(Nested(SoftwarePackageSchema))
    libraries = List(Nested(SoftwarePackageSchema))
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class SoftwareStackSchema(Schema):
    """Software stack."""
    system_software = Nested(SystemSoftwareSchema, required=True)
    user_software = Nested(UserSoftwareSchema)
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()


class NodeDesignSchema(Schema):
    """Node type design specification (1..N per part)."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["node-std-001", "node-gpu-a100", "node-hmem-001"])
    node_type_name = Str(required=True, validate=Length(min=1),
                         x_suggested=["standard-node", "highmem-node", "gpu-node", "login-node"])
    node_count = Int(validate=Range(min=1),
                     x_suggested=[4096, 128, 16, 1024])
    cpus = List(Nested(CPUSchema), required=True, validate=Length(min=1))
    memory = List(Nested(MemorySchema), required=True, validate=Length(min=1))
    accelerators = List(Nested(AcceleratorSchema))
    network = List(Nested(NetworkAdapterSchema))
    on_node_storage = List(Nested(StorageSchema))
    numa_topology = List(Nested(NumaDomainSchema))
    comment = Str(x_suggested=["Standard compute node", "High-memory configuration", "GPU nodes for AI workloads"])
    inherits_from = Str(load_default=None,
                        x_suggested=["standard-node", "gpu-node", "highmem-node"])
    further_metadata = Nested(FurtherMetadataSchema)


class SystemPartSchema(Schema):
    """System partition with node type designs (1..N node types per part)."""
    id = Str(required=True, validate=Length(min=1),
             x_suggested=["sys-a1b2c3d4e5f6", "part-cpu-001", "part-gpu-001", "part-storage-001"])
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["Compute Partition", "Login Partition", "Storage Partition"])
    provider = Str(x_suggested=["HPE", "Dell", "Lenovo", "Supermicro", "Cisco"])
    product_name = Str(x_suggested=["Apollo 6500", "PowerEdge C6525", "ThinkSystem SR670"])
    installed_at = DateTime(load_default=None, x_suggested=["2024-06-01T00:00:00Z"])
    accepted_at = DateTime(load_default=None, x_suggested=["2025-02-01T00:00:00Z"])
    funders = List(Str(), x_suggested=["BMFTR", "EuroHPC JU", "NRW-MKW"])
    part_type = Str(required=True, validate=OneOf(['compute', 'other', 'storage']),
                    x_suggested=["compute", "other", "storage"])
    other_type_name = Str(x_suggested=["login", "management", "interconnect", "service"])
    storage_role = Str(x_suggested=["local", "parallel", "archive", "home", "scratch"])
    node_count = Int(required=True, validate=Range(min=1),
                     x_suggested=[4096, 128, 16, 1024])
    power_draw_peak = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 500, "unit": "kW"})
    power_draw_average = Nested(QuantityWithUnitSchema, x_suggested={"quantity": 350, "unit": "kW"})
    power_details = Dict()  # Will be added as nested schema if needed
    inherits_from = Str(x_suggested=["compute-partition-1", "gpu-partition-main", "storage-partition-1"],
                        load_default=None)
    comment = Str(x_suggested=["Primary compute partition", "GPU-accelerated nodes", "Legacy system"])
    physical_location = Nested(PhysicalLocationSchema)
    cooling = Nested(CoolingSchema)
    network = List(Nested(GlobalNetworkSchema))
    node_types = List(Nested(NodeDesignSchema), required=True, validate=Length(min=1))
    software_stack = Nested(SoftwareStackSchema)
    # Deprecated fields (kept for backward compatibility)
    cpus = Nested(CPUSchema, deprecated=True)
    memory = Nested(MemorySchema, deprecated=True)
    accelerators = List(Nested(AcceleratorSchema), deprecated=True)
    on_node_storage = Nested(StorageSchema, deprecated=True)
    storage_system = Nested(StorageSchema)
    numa_topology = List(Nested(NumaDomainSchema), deprecated=True)
    further_metadata = Nested(FurtherMetadataSchema)


class SystemDefinitionSchemaV1(Schema):
    """System definition schema v0.5 with both schema and document versioning."""
    name = Str(required=True, validate=Length(min=1),
               x_suggested=["JUWELS Booster", "JURECA-DC", "Perlmutter"])
    provider = Nested(ProviderSchema, required=True,
                      x_suggested=[{"name": "Jülich Supercomputing Centre", "location": "Jülich, Germany"},
                                   {"name": "NERSC", "location": "Berkeley, CA"},
                                   {"name": "OLCF", "location": "Oak Ridge, TN"}])
    location = Str(required=True, validate=Length(min=1),
                   x_suggested=["Jülich, Germany", "Berkeley, CA", "Oak Ridge, TN"])
    installed_at = DateTime(required=True, x_suggested=["2024-06-01T00:00:00Z"])
    schema_version = Str(required=True, validate=OneOf(['0.5.0']),
                         x_suggested=["0.5.0"])
    version = Str(required=True, validate=validate.Regexp(r'^[0-9]+\.[0-9]+\.[0-9]+$'),
                  x_suggested=["1.0.0", "1.0.1", "1.1.0"])
    parts = List(Nested(SystemPartSchema), required=True, validate=Length(min=1))
    website = Url(x_suggested=["https://juwel.fz-juelich.de", "https://perlmutter.nersc.gov"])
    further_metadata = Nested(FurtherMetadataSchema)
    comment = Str()
    
    @validates_schema
    def validate_part_type(self, data, **kwargs):
        """Validate part_type-specific required fields."""
        if data.get('part_type') == 'other' and not data.get('other_type_name'):
            raise ValidationError("other_type_name required when part_type is 'other'", field_name='other_type_name')
        if data.get('part_type') == 'storage' and not data.get('storage_role'):
            raise ValidationError("storage_role required when part_type is 'storage'", field_name='storage_role')
