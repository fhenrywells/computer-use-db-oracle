export default function SearchPage() {
  return (
    <main data-testid="view-search-results">
      <div data-testid="facet-panel" />
      <div data-testid="results-list" />
      <select data-testid="sort-select" defaultValue="relevance">
        <option value="relevance">Relevance</option>
      </select>
      <span data-testid="result-count">0</span>
    </main>
  );
}

