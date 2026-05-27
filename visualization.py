import json

DEPENDENCY_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Project Dependency Map</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; background: #0d1117; color: #c9d1d9; font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; overflow: hidden; }
        #app { display: flex; height: 100vh; flex-direction: column; }
        #toolbar { background: #161b22; padding: 12px 20px; display: flex; align-items: center; flex-wrap: wrap; gap: 15px; border-bottom: 1px solid #30363d; z-index: 10; }
        h1 { margin: 0; font-size: 16px; color: #58a6ff; font-weight: 600; }
        select, button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        button:hover { background: #30363d; border-color: #8b949e; }
        button.active { background: #1f6feb; border-color: #58a6ff; }
        #graph-container { flex: 1; position: relative; width: 100%; height: 100%; }
        svg { width: 100%; height: 100%; }
        
        .link { stroke: #58a6ff; stroke-opacity: 0.35; stroke-width: 1.5px; }
        .node { cursor: pointer; stroke: #0d1117; stroke-width: 2px; }
        .node:hover { stroke: #c9d1d9; }
        .node-label { font-size: 11px; fill: #8b949e; pointer-events: none; font-family: monospace; }
        .highlighted { fill: #c9d1d9 !important; font-weight: bold; font-size: 12px; }
        
        #info-panel { position: absolute; right: 0; top: 0; bottom: 0; width: 360px; background: #161b22; border-left: 1px solid #30363d; padding: 25px; overflow-y: auto; display: none; box-shadow: -5px 0 15px rgba(0,0,0,0.5); z-index: 20; }
        .close-btn { position: absolute; top: 15px; right: 15px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer; }
        .close-btn:hover { color: #c9d1d9; }
        
        h3 { margin-top: 0; margin-bottom: 5px; color: #58a6ff; font-size: 18px; word-break: break-all; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; margin-bottom: 15px; background: #21262d; border: 1px solid #30363d; }
        h4 { margin: 20px 0 8px 0; color: #79c0ff; border-bottom: 1px solid #21262d; padding-bottom: 4px; font-size: 13px; text-transform: uppercase; }
        ul { margin: 0; padding-left: 20px; font-size: 13px; color: #b1bac4; }
        li { margin-bottom: 4px; font-family: monospace; word-break: break-all; }
        .path-text { font-family: monospace; font-size: 11px; color: #8b949e; background: #0d1117; padding: 6px; border-radius: 4px; word-break: break-all; margin: 10px 0; border: 1px solid #21262d; }
        
        #tooltip { position: absolute; background: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; pointer-events: none; opacity: 0; font-size: 12px; color: #c9d1d9; z-index: 30; }
        .legend { position: absolute; left: 20px; bottom: 20px; background: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 6px; font-size: 12px; display: flex; flex-direction: column; gap: 6px; }
    </style>
</head>
<body>
    <div id="app">
        <div id="toolbar">
            <h1>Project Dependency Map</h1>
            <select id="filter-group"><option value="all">All Architecture Groups</option></select>
            <button id="btn-packages" class="active">NuGet Packages: ON</button>
            <button id="btn-tests" class="active">Test Projects: ON</button>
            <button id="btn-layers">Topological Layer View</button>
            <button id="btn-reset">Reset Zoom</button>
        </div>
        <div id="graph-container">
            <svg></svg>
            <div id="tooltip"></div>
            <div id="info-panel"></div>
            <div id="legend" class="legend"></div>
        </div>
    </div>
    <script>
        const RAW_DATA = %DATA_JSON%;
        const LAYERS = %LAYERS_JSON%;
        
        const groupColors = {
            "API": "#f97583", "Tests": "#8b949e", "Shared Libraries": "#79c0ff",
            "Data Access": "#56d364", "Domain Services": "#d2a8ff",
            "Background Services": "#ffa657", "External Services": "#ff7b72",
            "NuGet Package": "#388bfd"
        };

        // CRITICAL Rule: Extract accurate IDs parsing both string and mutated D3 object representations
        function getId(obj) { return (obj && typeof obj === 'object') ? (obj.id || '') : obj; }

        const adjOut = {}, adjIn = {};
        function buildAdjacencyMaps() {
            for (let k in adjOut) delete adjOut[k];
            for (let k in adjIn) delete adjIn[k];
            
            RAW_DATA.project_edges.concat(RAW_DATA.package_edges).forEach(e => {
                const s = getId(e.source), t = getId(e.target);
                if (!adjOut[s]) adjOut[s] = [];
                if (!adjOut[s].includes(t)) adjOut[s].push(t);
                if (!adjIn[t]) adjIn[t] = [];
                if (!adjIn[t].includes(s)) adjIn[t].push(s);
            });
        }
        buildAdjacencyMaps();

        let showPackages = true, showTests = true, currentGroup = "all", layerView = false;
        
        const svg = d3.select("svg"), g = svg.append("g");
        const zoom = d3.zoom().scaleExtent([0.05, 3]).on("zoom", (e) => g.attr("transform", e.transform));
        svg.call(zoom);

        const select = d3.select("#filter-group");
        Object.keys(RAW_DATA.groups).forEach(grp => select.append("option").attr("value", grp).text(grp));

        const legend = d3.select("#legend");
        Object.entries(groupColors).forEach(([grp, col]) => {
            legend.append("div").html(`<span style="display:inline-block;width:12px;height:12px;background:${col};margin-right:8px;border-radius:2px;"></span>${grp}`);
        });

        let simulation = null;

        function resetZoom() {
            const bounds = g.node().getBBox();
            const parent = svg.node().getBoundingClientRect();
            const width = bounds.width, height = bounds.height;
            
            if (width === 0 || height === 0) return;
            
            const midX = bounds.x + width / 2;
            const midY = bounds.y + height / 2;
            
            const scale = 0.85 / Math.max(width / parent.width, height / parent.height);
            const tX = parent.width / 2 - scale * midX;
            const tY = parent.height / 2 - scale * midY;
            
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity.translate(tX, tY).scale(Math.min(scale, 1)));
        }

        function render() {
            if (simulation) simulation.stop();
            g.selectAll("*").remove();

            let nodes = RAW_DATA.project_nodes.map(n => ({...n, type: "Project"}));
            if (showPackages) nodes = nodes.concat(RAW_DATA.package_nodes.map(p => ({...p, type: "Package"})));
            
            if (!showTests) nodes = nodes.filter(n => n.group !== "Tests");
            if (currentGroup !== "all") {
                nodes = nodes.filter(n => n.group === currentGroup || n.type === "Package");
            }

            const nodeIds = new Set(nodes.map(n => n.id));
            let edges = RAW_DATA.project_edges.concat(showPackages ? RAW_DATA.package_edges : []).map(e => ({...e}));
            edges = edges.filter(e => nodeIds.has(getId(e.source)) && nodeIds.has(getId(e.target)));

            const link = g.append("g").selectAll("line").data(edges).enter().append("line").attr("class", "link");

            const nodeGroup = g.append("g").selectAll("g").data(nodes).enter().append("g");

            const nodeEls = nodeGroup.append("circle")
                .attr("class", "node")
                .attr("r", d => d.type === "Package" ? 6 : 12 + (d.ref_count || 0) * 1.2)
                .attr("fill", d => groupColors[d.group] || "#d1d5db")
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

            const labelEls = nodeGroup.append("text")
                .attr("class", "node-label")
                .attr("id", d => `lbl-${d.id}`)
                .attr("dx", d => d.type === "Package" ? 10 : 16)
                .attr("dy", ".35em")
                .text(d => d.label);

            nodeEls.on("mouseover", (e, d) => {
                d3.select("#tooltip").style("opacity", 1)
                    .html(`<strong>${d.label}</strong><br/>Category: ${d.group}`)
                    .style("left", (e.pageX + 15) + "px").style("top", (e.pageY + 15) + "px");
            }).on("mousemove", (e) => {
                d3.select("#tooltip").style("left", (e.pageX + 15) + "px").style("top", (e.pageY + 15) + "px");
            }).on("mouseout", () => d3.select("#tooltip").style("opacity", 0))
              .on("click", (e, d) => { e.stopPropagation(); showDetails(d); highlightConnections(d.id); });

            svg.on("click", () => { 
                document.getElementById("info-panel").style.display = "none"; 
                g.selectAll(".link").style("stroke-opacity", 0.35); 
                g.selectAll(".node-label").classed("highlighted", false); 
            });

            // Tighter structural gravity forces to keep groups unified rather than spread out
            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(edges).id(d => d.id).distance(d => d.type === "Package" ? 40 : 80))
                .force("charge", d3.forceManyBody().strength(-140))
                .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2))
                .force("collide", d3.forceCollide().radius(d => d.type === "Package" ? 12 : 30));

            let ticks = 0;
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                
                nodeEls.attr("cx", d => d.x).attr("cy", d => d.y);
                labelEls.attr("x", d => d.x).attr("y", d => d.y);
                
                // Auto reset view boundaries cleanly right after initial positions solidify
                if (ticks++ === 35) { resetZoom(); }
            });

            if (layerView) {
                const layerPos = {};
                LAYERS.forEach((layer, idx) => layer.forEach(id => layerPos[id] = idx));
                const maxLayer = LAYERS.length || 1;
                simulation.force("x", d3.forceX(d => d.type === "Package" ? window.innerWidth / 2 : ((layerPos[d.id] || 0) / maxLayer) * (window.innerWidth - 320) + 100).strength(1.2));
                simulation.alphaTarget(0.1).restart();
            }
        }

        function showDetails(d) {
            const panel = document.getElementById("info-panel");
            panel.style.display = "block";
            
            const outDeps = adjOut[d.id] || [];
            const inDeps = adjIn[d.id] || [];
            
            let metaBlock = d.type === "Project" ? 
                `<h4>Target Framework</h4><div class="path-text">${d.framework || 'Unknown'}</div>
                 <h4>Project Sdk Spec</h4><div class="path-text">${d.sdk || 'Microsoft.NET.Sdk'}</div>
                 <h4>File System Context Location</h4><div class="path-text">${d.path}</div>` :
                `<h4>Package Context Category</h4><div class="path-text">${d.category || 'Third-Party Dependency'}</div>
                 <h4>Detected Installed Version</h4><div class="path-text">${d.version || 'Latest Stable'}</div>`;

            panel.innerHTML = `
                <button class="close-btn" onclick="document.getElementById('info-panel').style.display='none'">×</button>
                <h3>${d.label}</h3>
                <div class="tag" style="border-color:${groupColors[d.group]}">${d.group}</div>
                ${metaBlock}
                <h4>Downstream Dependencies (${outDeps.length})</h4>
                <ul>${outDeps.length ? outDeps.map(id => `<li>${id.replace('pkg:','')}</li>`).join('') : '<li>None</li>'}</ul>
                <h4>Upstream Incoming References (${inDeps.length})</h4>
                <ul>${inDeps.length ? inDeps.map(id => `<li>${id.replace('pkg:','')}</li>`).join('') : '<li>None</li>'}</ul>
            `;
        }

        function highlightConnections(id) {
            g.selectAll(".link").style("stroke-opacity", l => {
                const sId = getId(l.source), tId = getId(l.target);
                return (sId === id || tId === id) ? 1.0 : 0.05;
            });
            
            const targets = new Set(adjOut[id] || []);
            const sources = new Set(adjIn[id] || []);
            
            g.selectAll(".node-label").each(function(l) {
                const active = l.id === id || targets.has(l.id) || sources.has(l.id);
                d3.select(this).classed("highlighted", active);
            });
        }

        function dragstarted(e) { if (!e.active) simulation.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; }
        function dragged(e) { e.subject.fx = e.x; e.subject.fy = e.y; }
        function dragended(e) { if (!e.active) simulation.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; }

        d3.select("#btn-packages").on("click", function() { showPackages = !showPackages; d3.select(this).classed("active", showPackages).text(`NuGet Packages: ${showPackages ? 'ON' : 'OFF'}`); buildAdjacencyMaps(); render(); });
        d3.select("#btn-tests").on("click", function() { showTests = !showTests; d3.select(this).classed("active", showTests).text(`Test Projects: ${showTests ? 'ON' : 'OFF'}`); buildAdjacencyMaps(); render(); });
        d3.select("#btn-layers").on("click", function() { layerView = !layerView; d3.select(this).classed("active", layerView); render(); });
        d3.select("#btn-reset").on("click", resetZoom);
        select.on("change", (e) => { currentGroup = e.target.value; render(); });

        render();
    </script>
</body>
</html>
"""

DATAFLOW_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Architecture Data Flow Map</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; background: #0d1117; color: #c9d1d9; font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; overflow: hidden; }
        #app { display: flex; height: 100vh; flex-direction: column; }
        #toolbar { background: #161b22; padding: 12px 20px; display: flex; align-items: center; flex-wrap: wrap; gap: 15px; border-bottom: 1px solid #30363d; z-index: 10; }
        h1 { margin: 0; font-size: 16px; color: #79c0ff; font-weight: 600; }
        select, button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        #graph-container { flex: 1; position: relative; }
        svg { width: 100%; height: 100%; }
        
        .link { stroke: #58a6ff; stroke-opacity: 0.4; stroke-width: 1.5px; fill: none; }
        .node { cursor: pointer; stroke: #161b22; stroke-width: 2px; }
        .node-label { font-size: 11px; fill: #8b949e; pointer-events: none; font-family: monospace; }
        
        #info-panel { position: absolute; right: 0; top: 0; bottom: 0; width: 380px; background: #161b22; border-left: 1px solid #30363d; padding: 25px; overflow-y: auto; display: none; box-shadow: -5px 0 15px rgba(0,0,0,0.5); z-index: 20; }
        .close-btn { position: absolute; top: 15px; right: 15px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer; }
        h3 { margin: 0 0 5px 0; color: #79c0ff; font-size: 18px; word-break: break-all; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-bottom: 15px; background: #21262d; border: 1px solid #30363d; }
        h4 { margin: 15px 0 6px 0; color: #58a6ff; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
        .panel-block { font-family: monospace; font-size: 12px; color: #b1bac4; background: #0d1117; padding: 8px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #21262d; max-height: 150px; overflow-y: auto; word-break: break-all; }
        
        #tooltip { position: absolute; background: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; pointer-events: none; opacity: 0; font-size: 12px; z-index: 30; }
        .legend { position: absolute; left: 20px; bottom: 20px; background: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 6px; font-size: 12px; display: flex; flex-direction: column; gap: 6px; }
    </style>
</head>
<body>
    <div id="app">
        <div id="toolbar">
            <h1>Architecture Data Flow Map</h1>
            <select id="filter-type">
                <option value="all">All Node Component Types</option>
                <option value="Controller">Controllers (API Handlers)</option>
                <option value="Service">Internal Services / Logic</option>
                <option value="External">External Infra (Clouds / DBs)</option>
            </select>
            <select id="filter-version">
                <option value="all">All API Runtime Versions</option>
                <option value="V1.0">Version 1.0</option>
                <option value="V2.0">Version 2.0</option>
                <option value="V3.0">Version 3.0</option>
            </select>
            <select id="filter-category"><option value="all">All Sub-Categories</option></select>
            <button id="btn-reset">Reset Zoom</button>
        </div>
        <div id="graph-container">
            <svg></svg>
            <div id="tooltip"></div>
            <div id="info-panel"></div>
            <div id="legend" class="legend"></div>
        </div>
    </div>
    <script>
        const RAW_DATA = %DATA_JSON%;
        
        const typeColors = { "Controller": "#f97583", "Service": "#79c0ff", "External": "#56d364", "Placeholder": "#8b949e" };
        
        function getId(obj) { return (obj && typeof obj === 'object') ? (obj.id || '') : obj; }

        const adjOut = {}, adjIn = {};
        RAW_DATA.edges.forEach(e => {
            const s = getId(e.source), t = getId(e.target);
            if (!adjOut[s]) adjOut[s] = [];
            if (!adjOut[s].includes(t)) adjOut[s].push(t);
            if (!adjIn[t]) adjIn[t] = [];
            if (!adjIn[t].includes(s)) adjIn[t].push(s);
        });

        const categories = new Set();
        RAW_DATA.nodes.forEach(n => { if(n.category) categories.add(n.category); });
        const catSelect = d3.select("#filter-category");
        categories.forEach(cat => catSelect.append("option").attr("value", cat).text(cat));

        const legend = d3.select("#legend");
        Object.entries(typeColors).forEach(([t, col]) => {
            legend.append("div").html(`<span style="display:inline-block;width:12px;height:12px;background:${col};margin-right:8px;border-radius:5px;"></span>${t}`);
        });

        let filterType = "all", filterVer = "all", filterCat = "all";
        const svg = d3.select("svg"), g = svg.append("g");
        const zoom = d3.zoom().scaleExtent([0.05, 3]).on("zoom", (e) => g.attr("transform", e.transform));
        svg.call(zoom);

        let simulation = null;

        function resetZoom() {
            const bounds = g.node().getBBox();
            const parent = svg.node().getBoundingClientRect();
            const width = bounds.width, height = bounds.height;
            
            if (width === 0 || height === 0) return;
            
            const midX = bounds.x + width / 2;
            const midY = bounds.y + height / 2;
            
            const scale = 0.85 / Math.max(width / parent.width, height / parent.height);
            const tX = parent.width / 2 - scale * midX;
            const tY = parent.height / 2 - scale * midY;
            
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity.translate(tX, tY).scale(Math.min(scale, 1)));
        }

        function render() {
            if (simulation) simulation.stop();
            g.selectAll("*").remove();

            let nodes = RAW_DATA.nodes.map(n => ({...n}));
            
            if (filterType !== "all") nodes = nodes.filter(n => n.type === filterType);
            if (filterVer !== "all") nodes = nodes.filter(n => n.type !== "Controller" || n.version === filterVer);
            if (filterCat !== "all") nodes = nodes.filter(n => n.category === filterCat);

            const nodeIds = new Set(nodes.map(n => n.id));
            let edges = RAW_DATA.edges.map(e => ({...e})).filter(e => nodeIds.has(getId(e.source)) && nodeIds.has(getId(e.target)));

            g.append("defs").append("marker")
                .attr("id", "arrow").attr("viewBox", "0 -5 10 10").attr("refX", 22).attr("refY", 0)
                .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
                .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#58a6ff").style("opacity", 0.6);

            const link = g.append("g").selectAll("line").data(edges).enter().append("line")
                .attr("class", "link").attr("marker-end", "url(#arrow)");

            const nodeGroup = g.append("g").selectAll("g").data(nodes).enter().append("g");

            const nodeEls = nodeGroup.append("path")
                .attr("class", "node")
                .attr("d", d => {
                    if (d.type === "External") return d3.symbol().type(d3.symbolDiamond).size(160)();
                    let radius = d.type === "Controller" ? 12 : 8;
                    return d3.symbol().type(d3.symbolCircle).size(radius * radius * Math.PI)();
                })
                .attr("fill", d => typeColors[d.type] || "#d1d5db")
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

            const labelEls = nodeGroup.append("text")
                .attr("class", "node-label")
                .attr("dx", d => d.type === "External" ? 14 : 16)
                .attr("dy", ".35em")
                .text(d => d.label);

            nodeEls.on("mouseover", (e, d) => {
                d3.select("#tooltip").style("opacity", 1)
                    .html(`<strong>${d.label}</strong><br/>Type: ${d.type}`)
                    .style("left", (e.pageX + 15) + "px").style("top", (e.pageY + 15) + "px");
            }).on("mousemove", (e) => {
                d3.select("#tooltip").style("left", (e.pageX + 15) + "px").style("top", (e.pageY + 15) + "px");
            }).on("mouseout", () => d3.select("#tooltip").style("opacity", 0))
              .on("click", (e, d) => { e.stopPropagation(); inspectDataNode(d); highlightFlows(d.id); });

            svg.on("click", () => { 
                document.getElementById("info-panel").style.display = "none"; 
                link.style("stroke-opacity", 0.4); 
            });

            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(edges).id(d => d.id).distance(90))
                .force("charge", d3.forceManyBody().strength(-160))
                .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2))
                .force("collide", d3.forceCollide().radius(35));

            let ticks = 0;
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                nodeEls.attr("transform", d => `translate(${d.x},${d.y})`);
                labelEls.attr("x", d => d.x).attr("y", d => d.y);
                
                if (ticks++ === 35) { resetZoom(); }
            });
        }

        function inspectDataNode(n) {
            const panel = document.getElementById("info-panel");
            panel.style.display = "block";
            const downstream = adjOut[n.id] || [];
            const upstream = adjIn[n.id] || [];

            let detailContent = "";
            if (n.type === "Controller") {
                detailContent = `<h4>Route Blueprint Namespace</h4><div class="panel-block">${n.route}</div>
                                 <h4>API Route Version</h4><div class="tag">${n.version}</div>`;
            } else if (n.type === "Service") {
                detailContent = `<h4>Abstraction Interface Type</h4><div class="panel-block">${n.interface || 'Self-bound implementation'}</div>`;
            }

            panel.innerHTML = `
                <button class="close-btn" onclick="document.getElementById('info-panel').style.display='none'">×</button>
                <h3>${n.label}</h3>
                <div class="tag" style="border-color:${typeColors[n.type]}">${n.type} : ${n.category || 'General'}</div>
                ${detailContent}
                <h4>Triggers Execution Downstream To:</h4>
                <div class="panel-block">${downstream.length ? downstream.map(id => `• ${id.split(':')[1]}`).join('<br/>') : 'Terminal Node Execution Target'}</div>
                <h4>Invoked Vertically Upstream By:</h4>
                <div class="panel-block">${upstream.length ? upstream.map(id => `• ${id.split(':')[1]}`).join('<br/>') : 'Runtime Execution Entry Point'}</div>
            `;
        }

        function highlightFlows(id) {
            g.selectAll(".link").style("stroke-opacity", l => {
                const sId = getId(l.source), tId = getId(l.target);
                return (sId === id || tId === id) ? 1.0 : 0.05;
            });
        }

        function dragstarted(e) { if (!e.active) simulation.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; }
        function dragged(e) { e.subject.fx = e.x; e.subject.fy = e.y; }
        function dragended(e) { if (!e.active) simulation.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; }

        d3.select("#filter-type").on("change", (e) => { filterType = e.target.value; render(); });
        d3.select("#filter-version").on("change", (e) => { filterVer = e.target.value; render(); });
        d3.select("#filter-category").on("change", (e) => { filterCat = e.target.value; render(); });
        d3.select("#btn-reset").on("click", resetZoom);

        render();
    </script>
</body>
</html>
"""

def generate_dependency_html(dep_graph: dict, layers: list, output_path: str):
    html = DEPENDENCY_TEMPLATE.replace("%DATA_JSON%", json.dumps(dep_graph))
    html = html.replace("%LAYERS_JSON%", json.dumps(layers))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

def generate_dataflow_html(flow_graph: dict, output_path: str):
    html = DATAFLOW_TEMPLATE.replace("%DATA_JSON%", json.dumps(flow_graph))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)