# Schema

The core of this repository: the HPC System Description Schema, used to
describe HPC systems in a structured, machine-readable way.

| File | Description |
|------|-------------|
| `system-description-0.5.0.json` | The canonical schema, written in JSON Schema Draft-07. |
| `system_description_0.5.0.py` | The same schema expressed as Marshmallow classes for use in Python tooling. |

## Structure

The schema is organized into hierarchical, namespaced definitions:

- `hardware/` — system parts, node designs and their components: CPUs, memory, accelerators, cache, NUMA domains, network adapters, storage, cooling.
- `software/` — software stacks: system software, schedulers, user software, firmware, OS versions.
- `common/` — shared building blocks: `QuantityWithUnit` (quantity + unit pairs), `Provider`, `FurtherMetadata`.

Notable features:

- Inheritance between parts and node types (`inherits_from`).
- Suggested values (`x-suggested`) embedded in the schema to guide editors and tooling.
- Free-form extension points (`further_metadata`, `comment`) throughout.
- Timestamps in RFC3339 format; document and schema versions tracked separately.

## Usage

The JSON schema is the canonical definition. It is consumed by the
validation tooling in [`../validation/`](../validation/), rendered as HTML
documentation in [`../docs/`](../docs/), and drives the sample applications
in [`../sample-apps/`](../sample-apps/).

New schema versions are added as new files (`system-description-<version>.json`)
rather than replacing existing ones, keeping older descriptions valid.
