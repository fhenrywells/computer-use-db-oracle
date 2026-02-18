export default function HomePage() {
  return (
    <main data-testid="view-home">
      <input data-testid="search-input" />
      <button data-testid="search-submit">Search</button>
      <a href="/cart" data-testid="nav-cart">Cart</a>
      <span data-testid="cart-count">0</span>
    </main>
  );
}

