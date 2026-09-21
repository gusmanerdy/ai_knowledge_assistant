const fs = require("fs");

const graphPath = process.argv[2];
const outputPath = process.argv[3];
const graph = JSON.parse(fs.readFileSync(graphPath, "utf8"));
const issues = [];
const warnings = [];

if (!Array.isArray(graph.nodes)) issues.push("graph.nodes is missing or not an array");
if (!Array.isArray(graph.edges)) issues.push("graph.edges is missing or not an array");
if (!Array.isArray(graph.layers)) issues.push("graph.layers is missing or not an array");
if (!Array.isArray(graph.tour)) issues.push("graph.tour is missing or not an array");

const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
const edges = Array.isArray(graph.edges) ? graph.edges : [];
const layers = Array.isArray(graph.layers) ? graph.layers : [];
const tour = Array.isArray(graph.tour) ? graph.tour : [];
const nodeIds = new Set();
const seen = new Set();

for (const [index, node] of nodes.entries()) {
  if (!node.id) issues.push(`Node[${index}] missing id`);
  if (!node.type) issues.push(`Node[${index}] missing type`);
  if (!node.name) issues.push(`Node[${index}] missing name`);
  if (!node.summary) issues.push(`Node[${index}] missing summary`);
  if (!Array.isArray(node.tags) || node.tags.length === 0) issues.push(`Node[${index}] missing tags`);
  if (node.id) {
    if (seen.has(node.id)) issues.push(`Duplicate node ID '${node.id}'`);
    seen.add(node.id);
    nodeIds.add(node.id);
  }
}

for (const [index, edge] of edges.entries()) {
  if (!nodeIds.has(edge.source)) issues.push(`Edge[${index}] source '${edge.source}' not found`);
  if (!nodeIds.has(edge.target)) issues.push(`Edge[${index}] target '${edge.target}' not found`);
}

const fileLevelTypes = new Set(["file", "config", "document", "service", "pipeline", "table", "schema", "resource", "endpoint"]);
const fileNodeIds = nodes.filter((node) => fileLevelTypes.has(node.type)).map((node) => node.id);
const assigned = new Map();

for (const layer of layers) {
  for (const field of ["id", "name", "description", "nodeIds"]) {
    if (layer[field] === undefined) issues.push(`Layer '${layer.id || "unknown"}' missing ${field}`);
  }
  for (const id of layer.nodeIds || []) {
    if (!nodeIds.has(id)) issues.push(`Layer '${layer.id}' references missing node '${id}'`);
    if (assigned.has(id)) issues.push(`Node '${id}' appears in multiple layers`);
    assigned.set(id, layer.id);
  }
}

for (const id of fileNodeIds) {
  if (!assigned.has(id)) issues.push(`File-level node '${id}' not assigned to a layer`);
}

for (const [index, step] of tour.entries()) {
  for (const field of ["order", "title", "description", "nodeIds"]) {
    if (step[field] === undefined) issues.push(`Tour step[${index}] missing ${field}`);
  }
  for (const id of step.nodeIds || []) {
    if (!nodeIds.has(id)) issues.push(`Tour step[${index}] references missing node '${id}'`);
  }
}

const connected = new Set();
for (const edge of edges) {
  connected.add(edge.source);
  connected.add(edge.target);
}
for (const node of nodes) {
  if (!connected.has(node.id)) warnings.push(`Node '${node.id}' has no edges`);
}

const countBy = (items, key) => items.reduce((acc, item) => {
  acc[item[key]] = (acc[item[key]] || 0) + 1;
  return acc;
}, {});

fs.writeFileSync(outputPath, JSON.stringify({
  issues,
  warnings,
  stats: {
    totalNodes: nodes.length,
    totalEdges: edges.length,
    totalLayers: layers.length,
    tourSteps: tour.length,
    nodeTypes: countBy(nodes, "type"),
    edgeTypes: countBy(edges, "type"),
  },
}, null, 2));

process.exit(issues.length ? 1 : 0);
