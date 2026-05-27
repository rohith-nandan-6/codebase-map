import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

sys.path.append(str(Path(__file__).parent.resolve()))

from dependency_scanner import scan_csproj_files, build_dependency_graph, get_dependency_layers
from data_flow_analyzer import scan_controllers, scan_services, scan_middleware, scan_di_registrations, detect_external_dependencies, build_data_flow_graph
from visualization import generate_dependency_html, generate_dataflow_html
from markdown_generator import generate_codebase_brain

def main():
    parser = argparse.ArgumentParser(description="codebase-map CLI System Engine Analyzer")
    parser.add_argument("--repo-root", required=True, help="Path to the target .NET repository root filesystem path")
    parser.add_argument("--output-dir", help="Target output folder destination location directory execution workspace")
    parser.add_argument("--open", action="store_true", help="Automatically trigger workspace rendering browsers instances")
    parser.add_argument("--skip-html", action="store_true", help="Bypass UI production pipelines")
    parser.add_argument("--skip-md", action="store_true", help="Bypass LLM document context engine output targets")
    
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    
    if not repo_root.exists():
        print(f"[-] Error: Target Repository Root Location path does not exist: {repo_root}")
        sys.exit(1)

    src_dir = repo_root / "src"
    if not src_dir.exists():
        src_dir = repo_root

    output_workspace = Path(args.output_dir) if args.output_dir else repo_root / ".codebase-map"
    output_workspace.mkdir(parents=True, exist_ok=True)

    print(f"[+] Launching Pipeline Scan execution routines against: {repo_root}")
    
    # Executing Phase 1 Pipeline Computations
    print("[+] Phase 1 Parsing: Aggregating .csproj metadata configurations...")
    projects = scan_csproj_files(str(repo_root))
    dep_graph = build_dependency_graph(projects)
    layers = get_dependency_layers(projects)

    # Executing Phase 2 Pipeline Computations
    print("[+] Phase 2 Scanning: Extrapolating source interaction structures...")
    controllers = scan_controllers(src_dir)
    services = scan_services(src_dir)
    middleware = scan_middleware(src_dir)
    di_registrations = scan_di_registrations(src_dir)
    externals = detect_external_dependencies(src_dir)
    flow_graph = build_data_flow_graph(controllers, services, middleware, externals, di_registrations)

    # Output Artifact Composition Pipeline Tasks
    raw_dump_target = output_workspace / "raw-analysis.json"
    with open(raw_dump_target, "w", encoding="utf-8") as f:
        json.dump({"dependencies": dep_graph, "data_flow": flow_graph, "layers": layers}, f, indent=2)

    dep_html_path = output_workspace / "dependency-map.html"
    flow_html_path = output_workspace / "data-flow-map.html"
    
    if not args.skip_html:
        print("[+] Phase 3a: Exporting compiled UI visualization frames...")
        generate_dependency_html(dep_graph, layers, str(dep_html_path))
        generate_dataflow_html(flow_graph, str(flow_html_path))

    if not args.skip_md:
        print("[+] Phase 3b: Writing consolidated LLM Context Target Workspace Brain Map Documents...")
        brain_latest = output_workspace / "codebase-brain-latest.md"
        generate_codebase_brain(projects, controllers, services, middleware, externals, di_registrations, layers, str(brain_latest))

    print(f"[+] Analysis pipelines completed gracefully! Workspace maps located in: {output_workspace}")

    if args.open and not args.skip_html:
        webbrowser.open(dep_html_path.as_uri())
        webbrowser.open(flow_html_path.as_uri())

if __name__ == "__main__":
    main()