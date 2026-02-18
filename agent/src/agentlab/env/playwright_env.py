class PlaywrightEnv:
    def reset(self, url: str) -> None:
        self.url = url

    def step(self, action: dict) -> dict:
        return {"ok": True, "action": action}

