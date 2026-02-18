import unittest

from agentlab.control.priors import get_workload_view_priors, update_priors_from_episodes


def _episode(workload: str, view: str, action: str) -> dict:
    return {
        "workload_type": workload,
        "success": True,
        "steps": [{"view_pred": view, "action": {"type": action}}],
    }


class PriorsConvergenceTest(unittest.TestCase):
    def test_converges_for_each_workload(self) -> None:
        targets = {
            "buy_exact_sku": ("PRODUCT_DETAIL", "AddToCart"),
            "find_cheapest_under_constraints": ("SEARCH_RESULTS", "SortBy"),
            "find_highest_rated_in_brand_category": ("SEARCH_RESULTS", "ApplyFacet"),
            "graph_browse_related": ("PRODUCT_DETAIL", "OpenRelated"),
        }

        priors = {"version": "1", "by_workload_view": {}}
        for workload, (view, action) in targets.items():
            episodes = [_episode(workload, view, action) for _ in range(10)]
            probs = []
            for _ in range(5):
                priors = update_priors_from_episodes(priors, episodes, lr=0.5)
                p = get_workload_view_priors(priors, workload, view).get(action, 0.0)
                probs.append(p)

            self.assertGreater(probs[-1], 0.90, f"{workload} did not converge toward {action}")
            self.assertTrue(all(probs[i] <= probs[i + 1] + 1e-9 for i in range(len(probs) - 1)))


if __name__ == "__main__":
    unittest.main()
