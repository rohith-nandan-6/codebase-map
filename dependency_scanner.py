import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set

@dataclass
class PackageInfo:
    name: str
    version: str
    category: str

@dataclass
class ProjectInfo:
    name: str
    path: str
    relative_path: str
    sdk: str
    target_framework: str
    is_test: bool
    is_web: bool
    project_references: List[str]
    package_references: List[PackageInfo]
    folder_group: str

def categorize_package(name: str) -> str:
    name_lower = name.lower()
    if any(k in name_lower for k in ["xunit", "moq", "test", "nunit", "fluentassertions"]):
        return "Testing"
    if any(k in name_lower for k in ["azure", "cosmos", "blob", "servicebus"]):
        return "Azure"
    if "opentelemetry" in name_lower:
        return "Observability"
    if "mapster" in name_lower or "automapper" in name_lower:
        return "Mapping"
    if "swagger" in name_lower or "swashbuckle" in name_lower:
        return "API Docs"
    if "polly" in name_lower:
        return "Resilience"
    if any(k in name_lower for k in ["serilog", "nlog", "log"]):
        return "Logging"
    if any(k in name_lower for k in ["entityframework", "dapper", "sqlclient", "storage"]):
        return "Data Access"
    if any(k in name_lower for k in ["identity", "auth", "jwt", "crypto"]):
        return "Authentication"
    return "Other"

def categorize_project(name: str, sdk: str, path: str) -> str:
    name_lower = name.lower()
    sdk_lower = sdk.lower()
    if ".test" in name_lower or ".tests" in name_lower:
        return "Tests"
    if "web" in sdk_lower or "api" in name_lower:
        return "API"
    if "worker" in name_lower or "job" in name_lower:
        return "Background Services"
    if any(k in name_lower for k in ["common", "contracts", "models", "core", "shared"]):
        return "Shared Libraries"
    if any(k in name_lower for k in ["external", "client", "proxy"]):
        return "External Services"
    return "Domain Services"

def scan_csproj_files(root_dir: str) -> Dict[str, ProjectInfo]:
    projects = {}
    root_path = Path(root_dir).resolve()
    
    for csproj_path in root_path.rglob("*.csproj"):
        parts = csproj_path.parts
        if any(k in parts for k in ["obj", "bin", "node_modules"]):
            continue
            
        try:
            tree = ET.parse(csproj_path)
            root = tree.getroot()
            
            sdk = root.attrib.get("Sdk", "")
            proj_name = csproj_path.stem
            
            tf_element = root.find(".//TargetFramework")
            tf = tf_element.text if tf_element is not None else "unknown"
            
            proj_refs = []
            for ref in root.findall(".//ProjectReference"):
                inc = ref.attrib.get("Include", "")
                ref_name = Path(inc).stem
                proj_refs.append(ref_name)
                
            pkg_refs = []
            for ref in root.findall(".//PackageReference"):
                pkg_name = ref.attrib.get("Include", "")
                version = ref.attrib.get("Version", "") or ref.get("version", "latest")
                pkg_refs.append(PackageInfo(
                    name=pkg_name,
                    version=version,
                    category=categorize_package(pkg_name)
                ))
                
            rel_path = str(csproj_path.relative_to(root_path)).replace("\\", "/")
            is_test = ".test" in proj_name.lower() or ".tests" in proj_name.lower()
            is_web = "web" in sdk.lower()
            group = categorize_project(proj_name, sdk, rel_path)
            
            projects[proj_name] = ProjectInfo(
                name=proj_name,
                path=str(csproj_path.resolve()).replace("\\", "/"),
                relative_path=rel_path,
                sdk=sdk,
                target_framework=tf,
                is_test=is_test,
                is_web=is_web,
                project_references=proj_refs,
                package_references=pkg_refs,
                folder_group=group
            )
        except Exception:
            continue
            
    return projects

def build_dependency_graph(projects: Dict[str, ProjectInfo]) -> dict:
    project_nodes = []
    package_nodes = {}
    project_edges = []
    package_edges = []
    groups = {}
    
    # Calculate inverted reference count metrics
    ref_counts = {name: 0 for name in projects}
    for p in projects.values():
        for r in p.project_references:
            if r in ref_counts:
                ref_counts[r] += 1

    for name, p in projects.items():
        if p.folder_group not in groups:
            groups[p.folder_group] = []
        groups[p.folder_group].append(name)
        
        project_nodes.append({
            "id": name,
            "label": name,
            "group": p.folder_group,
            "sdk": p.sdk,
            "framework": p.target_framework,
            "is_test": p.is_test,
            "is_web": p.is_web,
            "package_count": len(p.package_references),
            "ref_count": ref_counts[name],
            "path": p.relative_path
        })
        
        for r in p.project_references:
            project_edges.append({
                "source": name,
                "target": r,
                "type": "project_reference"
            })
            
        for pkg in p.package_references:
            pkg_id = f"pkg:{pkg.name}"
            if pkg_id not in package_nodes:
                package_nodes[pkg_id] = {
                    "id": pkg_id,
                    "label": pkg.name,
                    "group": "NuGet Package",
                    "is_package": True,
                    "version": pkg.version,
                    "category": pkg.category
                }
            package_edges.append({
                "source": name,
                "target": pkg_id,
                "type": "package_reference",
                "category": pkg.category
            })
            
    return {
        "project_nodes": project_nodes,
        "package_nodes": list(package_nodes.values()),
        "project_edges": project_edges,
        "package_edges": package_edges,
        "groups": groups
    }

def get_dependency_layers(projects: Dict[str, ProjectInfo]) -> List[List[str]]:
    # Kahn's Algorithm Implementation for Topological Sort
    adj = {name: set() for name in projects}
    in_degree = {name: 0 for name in projects}
    
    for name, p in projects.items():
        for ref in p.project_references:
            if ref in projects:
                adj[ref].add(name)
                in_degree[name] += 1
                
    queue = [name for name, degree in in_degree.items() if degree == 0]
    layers = []
    
    while queue:
        queue.sort()
        layers.append(list(queue))
        next_queue = []
        for node in queue:
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)
        queue = next_queue
        
    return layers