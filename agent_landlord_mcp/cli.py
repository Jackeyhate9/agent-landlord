from __future__ import annotations

import argparse
import signal
import time

from .bridge import DEFAULT_ARENA_URL, SUPPORTED_ADAPTERS, manager


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect a local agent to Agent Landlord and enter the queue")
    parser.add_argument("--name", required=True, help="public agent name")
    parser.add_argument("--adapter", choices=sorted(SUPPORTED_ADAPTERS), default="codex")
    parser.add_argument("--server", default=DEFAULT_ARENA_URL)
    parser.add_argument("--max-stake", type=int, choices=[100, 200, 500, 1000], default=100)
    parser.add_argument("--pov", action="store_true", help="allow the delayed public POV to show this agent's hand")
    args = parser.parse_args()
    result = manager.start(args.name, args.adapter, args.server, args.max_stake, args.pov)
    print(f"Connected and queued: {result['agent_name']} (PID {result['pid']})")
    print("Press Ctrl+C to leave the Arena.")
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        while manager.process and manager.process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()


if __name__ == "__main__":
    main()
