export default function ProductPage({ params }: { params: { asin: string } }) {
  return (
    <main data-testid="view-product-detail">
      <div data-testid="product-asin">{params.asin}</div>
      <div data-testid="product-title">Placeholder title</div>
      <div data-testid="product-brand">Placeholder brand</div>
      <div data-testid="product-price">0.0</div>
      <button data-testid="add-to-cart">Add to cart</button>
      <span data-testid="cart-count">0</span>
    </main>
  );
}

