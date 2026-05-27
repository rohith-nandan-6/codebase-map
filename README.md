# .NET Codebase Map Generator

A high-performance, zero-dependency static analysis CLI tool written in Python 3.8+ (standard library only) that scans any .NET/C# repository. It extracts solution-wide project reference matrices, third-party package profiles, and runtime data flow chains, outputting them as self-contained interactive D3.js v7 HTML visualizations and an LLM-optimized markdown knowledge base.

## Preview
![Dependency Map](assets/dependency-map.png)
![Dependency Map](assets/dependency-map.png)

## What It Is & Key Features

- Zero Setup, Zero External Libraries: Works out of the box on any machine with Python 3.8+ installed. No pip install, no virtual environments, and no local .NET SDK installation required.

- Topological Reference Sorting: Parses every .csproj XML file to build a project dependency tree, utilizing Kahn's Algorithm to compute topological layer views (leaf nodes at the bottom, heavily-dependent projects at the top).

- Regex-Powered Static Runtime Inspection: Scans C# source code to catalog:

 - API Controllers: Routes, verbs, action methods, return types (including asynchronous Task<T> types), and version branches (v1, v2, v3).

 - DI Service Registration: Parses Scoped, Singleton, and Transient interface mappings (services.Add<T, TImpl>()).

 - Pipeline Middleware Order: Scans Startup files to extract ordered request middleware, identifying conditional activations (UseWhen).

 - External Integrations: Patterns matching Azure Cosmos DB, Blob Storage, Redis, gRPC, Service Bus, and third-party APIs.

- Interactive D3.js Dark Theme Visualizations:

 - Project Dependency Graph: Explorable node diagram mapping references and NuGet dependencies. Features topological row-snapping, NuGet/Test project visibility filters, and selection highlights.

 - Runtime Data Flow Diagram: Maps API request executions from Controller endpoints ➔ Business Logic Services ➔ Storage Repositories ➔ Cloud Resources.

- LLM-Optimized Architecture Brain: Synthesizes a structured, token-efficient, table-heavy Markdown profile designed specifically to fit into LLM context windows (Claude, GPT, or Copilot) to power instant architectural impact analysis.

## File Structure

```
codebase-map/
│
├── __init__.py           # Empty package initialization marker
├── generate_map.py       # Main system orchestrator (CLI entrypoint)
├── dependency_scanner.py # Phase 1: Parses .csproj XML, builds dependency layers
├── data_flow_analyzer.py # Phase 2: Regex-parses C# classes for runtime entities
├── visualization.py      # Phase 3a: Generates D3.js interactive HTML diagrams
└── markdown_generator.py # Phase 3b: Produces token-optimized context .md files
```

## How It Works Under the Hood

- Phase 1: Dependency Mapping

The scanner parses project files using Python's standard xml.etree.ElementTree. It extracts target frameworks, platform SDKs, and tracks upstream project reference nodes. It identifies third-party packages and groups your projects into logical categories (API, Background Services, Data Access, Shared Libraries, or Tests) based on directory structures and naming schemes.

- Phase 2: Runtime Flow & Injection Tracing

The analyzer parses C# files using compiled multiline regular expressions. It maps service dependencies by inspecting constructors and finding injected interfaces. To build the data flow map, the engine resolves implementations using a custom 4-level deep Breadth-First Search (BFS) Traversal algorithm starting from the Controller API entry points, routing down through nested service layers.

- Phase 3: Compilation and Rendering

Visual templates: Embedded raw, immutable adjacency lookup tables (depAdjOut and depAdjIn) prevent D3.js v7's in-place link mutations from corrupting interactive trace actions.

The "Brain" generation: Outputs structural layouts and reverse-dependency matrices so AI models can easily calculate the blast radius of any modification.

## Setup & Usage

- Prerequisites

 - Python 3.8+ (Uses standard library elements only).

 - A .NET repository containing .csproj and .cs files.

- Installation

 - No installation needed. Simply clone this repository to a local directory:

 - cd C:\Users\YourUser\source\repos\codebase-map


## Running the Analyzer

To scan a target .NET repository, invoke generate_map.py pointing --repo-root to the target directory:

### Scan a repo and automatically open visualizations in your default browser
`python generate_map.py --repo-root "C:\Users\YourUser\source\repos\my-dotnet-api" --open`


### CLI Arguments
- `--repo-root <path>` : Required - Absolute or relative path to the .NET solution folder.
- `--output-dir <path>` : Optional - Location to save generated assets. Defaults to `<repo-root>/.codebase-map/.`
- `--open` : Optional - Auto-opens the resulting HTML visualizations in your browser.
- `--skip-html` : Optional - Skip generating visual HTML graphs (creates only the Markdown Brain and JSON).
- `--skip-md` : Optional - Skip generating the Markdown files (creates only the HTML Graphs and JSON).


## Output Files

All output is saved to <your-repo-root>/.codebase-map/ by default:

1. `dependency-map.html`
An interactive zoomable project graph. Toggle NuGet packages or Tests, filter by logical layer group, click any project node to view upstream/downstream connections in the side drawer, or click Layers to watch nodes physically slide and snap into their topological sort rows.

2. `data-flow-map.html`
An interactive trace mapping showing how data moves. Filter by API Version, Node Type, or logical Categories. Click any class box to expand its endpoints and trace upstream triggers and downstream calls. Click Spread Out if node clusters become too dense.

3. `codebase-brain-latest.md`
The core markdown system file designed for AI. Contains logic directories, middleware sequences, reverse matrices, DI registration bindings, and dependency inventories.

4. `codebase-brain-[timestamp].md`
A timestamped snapshot of the codebase history (ideal for running diff comparisons over time).

5. `raw-analysis.json`
Contains all raw serialized data structures for custom integrations.

## Unleashing AI with the Codebase Brain

To supercharge your development with Large Language Models (Claude, ChatGPT, or GitHub Copilot Chat), upload or paste the contents of .codebase-map/codebase-brain-latest.md as context, and ask prompt questions:

### Impact Analysis:

"Using the reverse dependencies matrix in Section 2, what is the architectural blast radius if I modify Reporting.Common? What projects or services will be affected?"

### API Flow Tracing:

"Trace the complete execution path for the endpoint GET /v3/agreements using the Service and Controller catalogs."

### Dependency Diagnostics:

"According to the DI Service Registry, what implementation gets mapped to IReportExecutionService, and what dependencies does its concrete class require?"

### Request Lifecycle Audits:

"What middleware will execute, and in what sequence, before the request reaches my controllers?"

## Best Practices

Add to Gitignore: Since codebase-map generates visual snapshots of your system, add .codebase-map/ to your target repository's .gitignore to prevent committing generated output files.

Run on Every Major Branch Shifting: Run the script as a pre-commit hook or before any deep-refactoring work to ensure your LLM is working with fresh structural layouts.