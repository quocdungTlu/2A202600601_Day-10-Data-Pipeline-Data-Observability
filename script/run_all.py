from __future__ import annotations

import time

from pipelines.phase1 import main as phase1_main
from pipelines.corruption_flow import main as corruption_main


if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 60)
    print("STEP 1/2 — Phase 1: Baseline Pipeline")
    print("=" * 60)
    phase1_main()

    print("\n" + "=" * 60)
    print("STEP 2/2 — Corruption & Repair Flow")
    print("=" * 60)
    corruption_main()

    total = time.perf_counter() - t0
    print(f"\nAll pipelines finished in {total:.1f}s")
