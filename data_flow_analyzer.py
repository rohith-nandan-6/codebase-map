import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set

@dataclass
class EndpointInfo:
    method: str
    route: str
    action_name: str
    return_type: str

@dataclass
class ControllerInfo:
    name: str
    file_path: str
    route: str
    api_version: str
    endpoints: List[EndpointInfo]
    injected_services: List[str]
    calls_to: List[str]

@dataclass
class ServiceInfo:
    name: str
    interface_name: str
    file_path: str
    injected_services: List[str]
    calls_to: List[str]
    category: str

@dataclass
class MiddlewareInfo:
    name: str
    file_path: str
    order: int
    conditional: bool

@dataclass
class ExternalDependency:
    name: str
    type: str
    usage_context: str

RE_CLASS_DECL = re.compile(r'(?:public|internal)\s+(?:sealed\s+|abstract\s+)?class\s+(\w+)\s*(?::\s*([^{]+))?')
RE_CONSTRUCTOR = re.compile(r'public\s+(\w+)\s*\(([\s\S]*?)\)\s*(?:\{|=>)')
RE_CTOR_PARAM = re.compile(r'(?:\[.*?\]\s*)?(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)')
RE_HTTP_METHOD = re.compile(r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\s*(?:\("([^"]*?)"\))?\]')
RE_ROUTE_ATTR = re.compile(r'\[Route\("([^"]+)"\)\]')
RE_DI_REGISTRATION = re.compile(r'services\.Add(Scoped|Singleton|Transient)<(\w+),\s*(\w+)>')
RE_MIDDLEWARE = re.compile(r'app\.UseMiddleware<(\w+)>')
RE_METHOD_CALL = re.compile(r'(?:await\s+)?(?:this\.)?(\w+)\.(\w+Async|\w+)\s*\(')

def infer_version(path: str, route: str) -> str:
    combined = (path + "/" + route).lower()
    match = re.search(r'v(\d+(?:\.\d+)?)', combined)
    return match.group(0).upper() if match else "v1.0"

def parse_constructor_injections(content: str, class_name: str) -> List[str]:
    injected = []
    for ctor_match in RE_CONSTRUCTOR.finditer(content):
        if ctor_match.group(1) == class_name:
            params_block = ctor_match.group(2)
            for param in RE_CTOR_PARAM.finditer(params_block):
                type_name = param.group(1)
                if type_name.startswith("I") and len(type_name) > 1 and type_name[1].isupper():
                    injected.append(type_name)
    return injected

def parse_method_calls(content: str) -> List[str]:
    calls = []
    for match in RE_METHOD_CALL.finditer(content):
        inst, method = match.group(1), match.group(2)
        if inst not in ["logger", "console", "context", "this"]:
            calls.append(f"{inst}.{method}")
    return list(set(calls))

def scan_controllers(src_dir: Path) -> List[ControllerInfo]:
    controllers = []
    for p in src_dir.rglob("*.cs"):
        if any(k in p.parts for k in ["obj", "bin", "Tests"]): continue
        if not (p.stem.endswith("Controller") or "EntryPoint" in p.stem): continue
        
        try:
            content = p.read_text(encoding="utf-8-sig")
            if "[ApiController]" not in content and "Controller" not in content: continue
            
            class_match = RE_CLASS_DECL.search(content)
            if not class_match: continue
            c_name = class_match.group(1)
            
            route_match = RE_ROUTE_ATTR.search(content)
            base_route = route_match.group(1) if route_match else "api/[controller]"
            
            injected = parse_constructor_injections(content, c_name)
            calls = parse_method_calls(content)
            
            # Simple Endpoint Parser
            endpoints = []
            lines = content.splitlines()
            for idx, line in enumerate(lines):
                m_http = RE_HTTP_METHOD.search(line)
                if m_http:
                    method = m_http.group(1).replace("Http", "").upper()
                    sub_route = m_http.group(2) or ""
                    
                    act_name = "Unknown"
                    ret_type = "IActionResult"
                    for next_line in lines[idx+1:idx+5]:
                        if "public" in next_line and "(" in next_line:
                            m_decl = re.search(r'public\s+(?:async\s+)?([^\s]+)\s+(\w+)\s*\(', next_line)
                            if m_decl:
                                ret_type, act_name = m_decl.group(1), m_decl.group(2)
                                break
                    endpoints.append(EndpointInfo(method, sub_route, act_name, ret_type))
            
            rel_path = str(p.relative_to(src_dir)).replace("\\", "/")
            controllers.append(ControllerInfo(
                name=c_name, file_path=rel_path, route=base_route,
                api_version=infer_version(rel_path, base_route),
                endpoints=endpoints, injected_services=injected, calls_to=calls
            ))
        except Exception: continue
    return controllers

def scan_services(src_dir: Path) -> List[ServiceInfo]:
    services = []
    suffixes = ("Service.cs", "Repository.cs", "Handler.cs", "Builder.cs", "Factory.cs", "Manager.cs", "Validator.cs", "Converter.cs")
    for p in src_dir.rglob("*.cs"):
        if any(k in p.parts for k in ["obj", "bin", "Tests", "Models"]): continue
        if not p.name.endswith(suffixes): continue
        
        try:
            content = p.read_text(encoding="utf-8-sig")
            if any(k in content for k in ["[Fact]", "[Theory]", "xunit"]): continue
            
            class_match = RE_CLASS_DECL.search(content)
            if not class_match: continue
            c_name = class_match.group(1)
            
            base_types = class_match.group(2) or ""
            interface_name = "None"
            for b_type in [b.strip() for b in base_types.split(",")]:
                if b_type.startswith("I") and len(b_type) > 1 and b_type[1].isupper():
                    interface_name = b_type
                    break
            
            injected = parse_constructor_injections(content, c_name)
            calls = parse_method_calls(content)
            
            category = "Business Logic"
            if "Repository" in c_name or "Store" in c_name: category = "Data Access"
            elif "Client" in c_name or "Proxy" in c_name: category = "External Service"
            
            services.append(ServiceInfo(
                name=c_name, interface_name=interface_name if interface_name != "None" else "I" + c_name,
                file_path=str(p.relative_to(src_dir)).replace("\\", "/"),
                injected_services=injected, calls_to=calls, category=category
            ))
        except Exception: continue
    return services

def scan_middleware(src_dir: Path) -> List[MiddlewareInfo]:
    pipeline = []
    order = 1
    for p in src_dir.rglob("*.cs"):
        if "Startup" in p.name or "Program" in p.name:
            try:
                content = p.read_text(encoding="utf-8-sig")
                for match in RE_MIDDLEWARE.finditer(content):
                    mw_name = match.group(1)
                    conditional = "UseWhen" in content or "If" in content
                    pipeline.append(MiddlewareInfo(
                        name=mw_name, file_path=str(p.relative_to(src_dir)).replace("\\", "/"),
                        order=order, conditional=conditional
                    ))
                    order += 1
            except Exception: continue
    return pipeline

def scan_di_registrations(src_dir: Path) -> List[dict]:
    regs = []
    for p in src_dir.rglob("*.cs"):
        if any(k in p.parts for k in ["obj", "bin"]): continue
        try:
            content = p.read_text(encoding="utf-8-sig")
            for match in RE_DI_REGISTRATION.finditer(content):
                regs.append({
                    "lifetime": match.group(1),
                    "interface": match.group(2),
                    "implementation": match.group(3),
                    "file": str(p.relative_to(src_dir)).replace("\\", "/")
                })
        except Exception: continue
    return regs

def detect_external_dependencies(src_dir: Path) -> List[ExternalDependency]:
    found = {}
    patterns = {
        "Azure Cosmos DB": (["CosmosClient", "Container.", "GetItemLinqQueryable"], "Database"),
        "Azure Blob Storage": (["BlobServiceClient", "BlobContainerClient"], "Storage"),
        "Azure Event Hub": (["EventHubProducerClient"], "Messaging"),
        "Azure Service Bus": (["ServiceBusClient"], "Messaging"),
        "Redis Cache": (["IDistributedCache", "StackExchange.Redis"], "Caching"),
        "HTTP External API": (["IHttpClientFactory", "HttpClient."], "API External"),
        "gRPC Service": (["GrpcChannel", ".Protos."], "gRPC RPC"),
        "Optimizely": (["IOptimizely", "IsFeatureEnabled"], "Feature Flags"),
        "Memory Cache": (["IMemoryCache"], "In-Memory Storage")
    }
    
    for p in src_dir.rglob("*.cs"):
        if any(k in p.parts for k in ["obj", "bin", "Tests"]): continue
        try:
            content = p.read_text(encoding="utf-8-sig")
            for name, (indicators, dep_type) in patterns.items():
                if any(ind in content for ind in indicators):
                    if name not in found:
                        found[name] = ExternalDependency(name, dep_type, str(p.relative_to(src_dir)).replace("\\", "/"))
        except Exception: continue
    return list(found.values())

def build_data_flow_graph(controllers, services, middleware, externals, di_registrations) -> dict:
    nodes = []
    edges = []
    
    # Store dynamic UI mapping structures
    di_map = {r["implementation"]: r["interface"] for r in di_registrations}
    interface_to_service = {s.interface_name: s for s in services}
    
    for c in controllers:
        nodes.append({"id": f"ctrl:{c.name}", "label": c.name, "type": "Controller", "category": "API", "version": c.api_version, "route": c.route})
        for s in c.injected_services:
            edges.append({"source": f"ctrl:{c.name}", "target": f"svc:{s}", "type": "injects"})
            
    for s in services:
        nodes.append({"id": f"svc:{s.interface_name}", "label": s.name, "type": "Service", "category": s.category, "interface": s.interface_name})
        for dep in s.injected_services:
            edges.append({"source": f"svc:{s.interface_name}", "target": f"svc:{dep}", "type": "injects"})
            
    for ext in externals:
        nodes.append({"id": f"ext:{ext.name}", "label": ext.name, "type": "External", "category": ext.type})
        # Infer dependency connection mapping
        for s in services:
            if ext.name.split()[0].lower() in s.name.lower():
                edges.append({"source": f"svc:{s.interface_name}", "target": f"ext:{ext.name}", "type": "calls"})

    for mw in middleware:
        nodes.append({"id": f"mw:{mw.name}", "label": mw.name, "type": "Middleware", "category": "Pipeline"})

    existing_node_ids = {n["id"] for n in nodes}
    deduped_edges = []
    seen_edges = set()
    
    for e in edges:
        edge_key = (e["source"], e["target"])
        if edge_key in seen_edges: continue
        seen_edges.add(edge_key)
        
        for endpoint in [e["source"], e["target"]]:
            if endpoint not in existing_node_ids:
                prefix, token = endpoint.split(":", 1)
                inferred_type = "Service" if prefix == "svc" else "External" if prefix == "ext" else "Controller"
                nodes.append({
                    "id": endpoint,
                    "label": token,
                    "type": inferred_type,
                    "category": "Placeholder Engine Reference",
                    "is_placeholder": True
                })
                existing_node_ids.add(endpoint)
        deduped_edges.append(e)

    return {
        "nodes": nodes,
        "edges": deduped_edges,
        "middleware_pipeline": [asdict(m) for m in middleware]
    }