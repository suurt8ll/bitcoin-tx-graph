<script>
  import { onMount } from "svelte";
  import Graph from "./lib/Graph.svelte";

  let txid = "62dab6759190a1f60ff0c43eb48bbbaeb5d5f16928e724b73c9d466e0bd1e850"; // Default TXID
  let depth = 3;
  let graphData = null;
  let error = null;

  async function fetchGraph() {
    error = null;
    try {
      const response = await fetch(
        `http://localhost:5555/api/v1/transaction/${txid}?depth=${depth}`,
      );
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      graphData = await response.json();
    } catch (e) {
      error = e.message;
      graphData = null;
    }
  }

  onMount(fetchGraph);

  function handleSubmit() {
    fetchGraph();
  }
</script>

<main>
  <h1>Bitcoin Transaction Graph</h1>

  <form on:submit|preventDefault={handleSubmit}>
    <label for="txid">Transaction ID:</label>
    <input type="text" id="txid" bind:value={txid} />

    <label for="depth">Depth:</label>
    <input type="number" id="depth" bind:value={depth} min="0" />

    <button type="submit">Fetch Graph</button>
  </form>

  {#if error}
    <p class="error">Error: {error}</p>
  {/if}

  <div class="graph-container">
    <Graph {graphData} />
  </div>
</main>

<style>
  :root {
    color-scheme: dark;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background-color: #121212;
    height: 100vh;
    overflow: hidden;
  }

  main {
    color: #fff;
    font-family: sans-serif;
    padding: 20px;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 40px);
  }

  input,
  button {
    background-color: #333;
    color: #fff;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 8px;
  }

  button:hover {
    background-color: #1a43b3;
  }

  .error {
    color: #f44336;
    margin-top: 10px;
  }

  .graph-container {
    width: 100%;
    flex-grow: 1;
  }
</style>
