<script>
  import { onMount, onDestroy } from "svelte";
  import cytoscape from "cytoscape";
  import coseBilkent from "cytoscape-cose-bilkent"; // Import the extension

  cytoscape.use(coseBilkent); // Register the extension

  export let graphData; // Input property: the graph data
  let cy = null;
  let container;

  function renderGraph() {
    if (!graphData) return;

    if (cy) {
      cy.destroy();
    }

    cy = cytoscape({
      container: container,
      elements: {
        nodes: graphData.nodes.map((node) => ({
          data: { id: node.id, ...node.attributes },
        })),
        edges: graphData.edges.map((edge) => ({
          data: {
            source: edge.source,
            target: edge.target,
            value: edge.value,
            from_address: edge.from_address,
          },
        })),
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#666",
            label: "data(id)",
            "font-size": "12px",
            "text-valign": "center",
            "text-halign": "center",
            color: "#fff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#ccc",
            "target-arrow-color": "#ccc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(value)", // Show the transaction value
            "font-size": "10px",
            "text-rotation": "autorotate",
            color: "#ddd",
          },
        },
      ],
      layout: {
        name: "cose-bilkent",
      },
    });
  }

  onMount(() => {
    renderGraph();
  });

  onDestroy(() => {
    if (cy) {
      cy.destroy();
    }
  });

  $: if (graphData) {
    // React to changes in graphData
    renderGraph();
  }
</script>

<div id="cy" bind:this={container}></div>

<style>
  #cy {
    width: 100%;
    height: 100%; /* Take up the full height of the parent */
    border: 1px solid #555;
  }
</style>
