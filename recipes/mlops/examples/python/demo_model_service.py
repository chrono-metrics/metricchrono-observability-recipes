"""Run the event-derived MLOps adapter over the local recipe scenario."""

from __future__ import annotations

from metricchrono_mlops_adapter import build_demo_events, snapshots_for_events


def main() -> None:
    events = build_demo_events()
    snapshots = snapshots_for_events(events)
    print("phase,model_version,behavior,input,output,retrieval,agent,quality")
    for index in [10, 30, 55, 69, 70, 84, 119]:
        snapshot = snapshots[index]
        scores = snapshot.scores
        print(
            ",".join(
                [
                    snapshot.event.phase,
                    snapshot.event.model_version,
                    f"{scores['behavior']:.1f}",
                    f"{scores['input']:.1f}",
                    f"{scores['output']:.1f}",
                    f"{scores['retrieval']:.1f}",
                    f"{scores['agent']:.1f}",
                    f"{snapshot.event.quality_proxy:.1f}",
                ]
            )
        )


if __name__ == "__main__":
    main()
