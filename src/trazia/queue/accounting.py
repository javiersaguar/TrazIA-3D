from trazia.model import RunInfo


class Accounting:
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.runs: list[RunInfo | None] = []

    def add(self, run: RunInfo | None):
        self.runs.append(run)

    def finish(self, seconds: float) -> RunInfo:
        known = [r for r in self.runs if r is not None]
        complete = bool(known) and all(r is not None and r.accounting_complete for r in self.runs)

        def total(key):
            values = [getattr(r, key) for r in known]
            return sum(values) if complete and all(v is not None for v in values) else None

        return RunInfo(
            strategy=self.strategy,
            providers=sorted({p for r in known for p in r.providers}),
            seconds=seconds,
            gpu_seconds=total("gpu_seconds"),
            tokens_in=total("tokens_in"),
            tokens_out=total("tokens_out"),
            cost_eur=total("cost_eur"),
            external_calls=sum(r.external_calls for r in known),
            accounting_complete=complete,
        )
