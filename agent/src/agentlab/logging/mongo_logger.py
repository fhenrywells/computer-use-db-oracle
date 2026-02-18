class MongoLogger:
    def log_episode(self, episode: dict) -> None:
        self.last_episode = episode

    def log_step(self, step: dict) -> None:
        self.last_step = step

