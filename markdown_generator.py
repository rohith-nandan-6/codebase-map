import datetime
from typing import Dict, List

def generate_codebase_brain(projects: dict, controllers: list, services: list, middleware: list, externals: list, di_registrations: list, layers: list, output_path: str) -> str:
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    md = []
    md.append(f"# Codebase Architecture Brain")
    md.append(f"\n")
    
    md.append("## Architecture Overview")
    md.append("| Project / Layer Module | Target Framework | Group Tag | Relative Paths |")
    md.append("| :--- | :--- | :--- | :--- |")
    for name, p in projects.items():
        md.append(f"| {name} | {p.target_framework} | {p.folder_group} | `{p.relative_path}` |")
        
    md.append("\n## DI Service Registry Reference Map")
    md.append("| Interface Abstraction | Concrete Class Implementation | Lifetime Scope | Defined In File Component |")
    md.append("| :--- | :--- | :--- | :--- |")
    for di in di_registrations:
        md.append(f"| `{di['interface']}` | `{di['implementation']}` | {di['lifetime']} | `{di['file']}` |")

    md.append("\n## Middleware Pipeline Order Execution Layout")
    for mw in middleware:
        # Use object dot-notation instead of dictionary bracket notation
        cond_str = " (Conditional Pipeline Activation Mapping)" if mw.conditional else ""
        md.append(f"{mw.order}. `{mw.name}`{cond_str} - found in `{mw.file_path}`")

    md.append("\n## Controller Catalog Routing")
    md.append("| Route Template Spec | HTTP Endpoint Handler Action | Injected Service Handlers |")
    md.append("| :--- | :--- | :--- |")
    for c in controllers:
        for ep in c.endpoints:
            md.append(f"| `[{c.api_version}] {c.route}/{ep.route}` | **{ep.method}** -> `{ep.action_name}` | `{', '.join(c.injected_services)}` |")

    md.append("\n## Service Architecture Catalog Map")
    md.append("| Implementation Module Class | Interface Layer | Functional Category Category | Dependencies Injected |")
    md.append("| :--- | :--- | :--- | :--- |")
    for s in services:
        md.append(f"| `{s.name}` | `{s.interface_name}` | {s.category} | `{', '.join(s.injected_services)}` |")

    md.append("\n## External Third-Party Integration Infrastructure Dependencies")
    md.append("| Integration Resource Name | Type Target Pattern Identifier | Code Discovery Frame File Target |")
    md.append("| :--- | :--- | :--- |")
    for ext in externals:
        md.append(f"| **{ext.name}** | `{ext.type}` | `{ext.usage_context}` |")

    md.append("\n## Impact Analysis Guide & System Structural Execution Path Verification")
    md.append("> Run topological verification steps map matching when applying sweeping architecture adjustments.")
    
    out_content = "\n".join(md)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out_content)
        
    return output_path