from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from agentlab.perception.screenshot_view_classifier import screenshot_features


class BrowserPlaywrightEnv:
    def __init__(self, base_url: str, artifacts_dir: str = "experiments/artifacts") -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "playwright is required for screenshot-based browser env. Install with `pip install playwright`."
            ) from exc
        self._sync_playwright = sync_playwright
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None
        self.base_url = base_url.rstrip("/")
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.sid = f"s{int(time.time())}"

    def _ensure(self) -> None:
        if self._pw is not None:
            return
        self._pw = self._sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._ctx = self._browser.new_context(viewport={"width": 1440, "height": 1024})
        self._page = self._ctx.new_page()

    def close(self) -> None:
        if self._ctx:
            self._ctx.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None

    def reset(self, start_asin: str | None = None, related_edge: str | None = None) -> dict[str, Any]:
        self._ensure()
        if start_asin:
            edge_q = f"&edge={related_edge}" if related_edge else ""
            url = f"{self.base_url}/ui/product/{start_asin}?sid={self.sid}{edge_q}"
        else:
            url = f"{self.base_url}/ui?sid={self.sid}"
        self._page.goto(url, wait_until="networkidle")
        return self._observation(step_idx=0)

    def _shot(self, step_idx: int) -> Path:
        fname = f"shot_{self.sid}_{step_idx:04d}.png"
        out = self.artifacts_dir / fname
        self._page.screenshot(path=str(out), full_page=True)
        return out

    def _observation(self, step_idx: int) -> dict[str, Any]:
        shot_path = self._shot(step_idx)
        feats = screenshot_features(shot_path)
        # Keep replay paths relative to the /artifacts static mount.
        feats["screenshot_path"] = shot_path.name
        feats["step_idx"] = step_idx
        return feats

    def _click_nth(self, selector: str, idx: int) -> bool:
        els = self._page.locator(selector)
        n = els.count()
        if n <= idx:
            return False
        els.nth(idx).click()
        return True

    def step(self, action: dict[str, Any], step_idx: int) -> tuple[dict[str, Any], dict[str, Any]]:
        kind = action.get("type", "NoOp")
        args = action.get("args", {})
        ok = True
        event = None

        try:
            if kind == "Search":
                query = str(args.get("query", "")).strip()
                self._page.fill('[data-testid="search-input"]', query)
                self._page.click('[data-testid="search-submit"]')
                event = "Searched"
            elif kind == "OpenResult":
                rank = max(1, int(args.get("rank", 1)))
                ok = self._click_nth('[data-testid="open-product"]', rank - 1)
                event = "OpenedProduct"
            elif kind == "OpenRelated":
                rank = max(1, int(args.get("rank", 1)))
                ok = self._click_nth('[data-testid="related-item"]', rank - 1)
                event = "OpenedRelated"
            elif kind == "AddToCart":
                self._page.click('[data-testid="add-to-cart"]')
                event = "AddedToCart"
            elif kind == "BackToResults":
                self._page.click('[data-testid="back-to-results"]')
                event = "BackToResults"
            elif kind == "GoToCart":
                self._page.click('[data-testid="nav-cart"]')
                event = "GoToCart"
            elif kind == "NoOp":
                event = "NoOp"
            else:
                ok = False
                event = "UnknownAction"
        except Exception:
            ok = False

        # settle navigation
        try:
            self._page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        obs = self._observation(step_idx=step_idx)
        # extract cart ASINs from hidden attr to support oracle verification
        cart_csv = ""
        try:
            cart_csv = self._page.get_attribute('[data-testid="cart-asins"]', "data-asins") or ""
        except Exception:
            cart_csv = ""
        obs["cart_asins"] = [x for x in cart_csv.split(",") if x]
        return obs, {"postcondition_ok": ok, "event": event, "screenshot_path": obs.get("screenshot_path")}

    def compute_oracle_target_asin(self, task: dict[str, Any]) -> str | None:
        spec = task.get("spec", {})
        oracle = task.get("oracle", {})
        expected = oracle.get("expected_asin")
        if isinstance(expected, str) and expected:
            return expected
        if isinstance(spec.get("target_asin"), str):
            return spec["target_asin"]
        return None
