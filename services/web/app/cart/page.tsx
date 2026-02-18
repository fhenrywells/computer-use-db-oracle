export default function CartPage() {
  return (
    <main data-testid="view-cart">
      <div data-testid="cart-items" />
      <div data-testid="cart-subtotal">0.0</div>
      <button data-testid="proceed-checkout">Checkout</button>
      <span data-testid="cart-count">0</span>
    </main>
  );
}

