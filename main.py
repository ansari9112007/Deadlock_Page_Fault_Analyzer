"""
Deadlock Detector and Page Fault Analyzer
A command-line educational simulator for resource deadlocks and demand paging.
"""

import argparse
import json
import sys
from typing import Any


def validate_matrix(name: str, matrix: Any, rows: int, cols: int) -> list[list[int]]:
    if not isinstance(matrix, list) or len(matrix) != rows:
        raise ValueError(f"{name} must contain exactly {rows} rows.")
    cleaned = []
    for row_index, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != cols:
            raise ValueError(f"{name} row {row_index} must contain exactly {cols} values.")
        if any(type(value) is not int or value < 0 for value in row):
            raise ValueError(f"{name} values must be non-negative integers.")
        cleaned.append(row[:])
    return cleaned


def validate_vector(name: str, vector: Any, size: int) -> list[int]:
    if not isinstance(vector, list) or len(vector) != size:
        raise ValueError(f"{name} must contain exactly {size} values.")
    if any(type(value) is not int or value < 0 for value in vector):
        raise ValueError(f"{name} values must be non-negative integers.")
    return vector[:]


def build_wait_for_graph(allocation: list[list[int]],
                         request: list[list[int]]) -> dict[int, set[int]]:
    """Add Pi -> Pj when Pi is waiting for a resource currently held by Pj."""
    process_count = len(allocation)
    resource_count = len(allocation[0]) if allocation else 0
    graph = {process: set() for process in range(process_count)}

    for waiting_process in range(process_count):
        for resource in range(resource_count):
            if request[waiting_process][resource] > 0:
                for holding_process in range(process_count):
                    if (holding_process != waiting_process
                            and allocation[holding_process][resource] > 0):
                        graph[waiting_process].add(holding_process)
    return graph


def find_cycle(graph: dict[int, set[int]]) -> list[int] | None:
    """Return one directed cycle, if present, using depth-first search."""
    state = {node: 0 for node in graph}  # 0=unvisited, 1=active, 2=finished
    stack: list[int] = []

    def visit(node: int):
        state[node] = 1
        stack.append(node)
        for neighbor in sorted(graph[node]):
            if state[neighbor] == 0:
                result = visit(neighbor)
                if result:
                    return result
            elif state[neighbor] == 1:
                start = stack.index(neighbor)
                return stack[start:] + [neighbor]
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if state[node] == 0:
            result = visit(node)
            if result:
                return result
    return None


def detect_deadlock(allocation: list[list[int]], request: list[list[int]],
                    available: list[int]) -> tuple[list[int], list[int]]:
    """
    Multiple-instance deadlock detection algorithm.
    Returns (deadlocked process indexes, safe completion order).
    """
    process_count = len(allocation)
    work = available[:]
    finish = [not any(row) for row in allocation]
    order = []

    changed = True
    while changed:
        changed = False
        for process in range(process_count):
            if not finish[process] and all(
                request[process][r] <= work[r] for r in range(len(work))
            ):
                work = [work[r] + allocation[process][r] for r in range(len(work))]
                finish[process] = True
                order.append(process)
                changed = True

    deadlocked = [p for p, completed in enumerate(finish) if not completed]
    return deadlocked, order


def run_deadlock_analysis(data: dict[str, Any]) -> None:
    allocation = data.get("allocation")
    request = data.get("request")
    available = data.get("available")

    if not isinstance(allocation, list) or not allocation:
        raise ValueError("'allocation' must be a non-empty matrix.")
    process_count = len(allocation)
    if not isinstance(allocation[0], list) or not allocation[0]:
        raise ValueError("'allocation' must have at least one resource column.")
    resource_count = len(allocation[0])

    allocation = validate_matrix("allocation", allocation, process_count, resource_count)
    request = validate_matrix("request", request, process_count, resource_count)
    available = validate_vector("available", available, resource_count)

    graph = build_wait_for_graph(allocation, request)
    deadlocked, completion_order = detect_deadlock(allocation, request, available)
    cycle = find_cycle(graph)

    print("\n" + "=" * 58)
    print("DEADLOCK ANALYSIS")
    print("=" * 58)
    print("Wait-for graph (Pi -> processes currently holding needed resources):")
    for process, neighbors in graph.items():
        targets = ", ".join(f"P{p}" for p in sorted(neighbors)) or "none"
        print(f"  P{process} -> {targets}")

    if cycle:
        print("Wait-for graph cycle:", " -> ".join(f"P{p}" for p in cycle))
    else:
        print("Wait-for graph cycle: none found")

    if deadlocked:
        print("Deadlock status: DEADLOCK DETECTED")
        print("Processes unable to finish:", ", ".join(f"P{p}" for p in deadlocked))
    else:
        print("Deadlock status: NO DEADLOCK DETECTED")
        print("All processes can finish with the supplied state.")

    if completion_order:
        print("Possible completion order:", " -> ".join(f"P{p}" for p in completion_order))
    else:
        print("Possible completion order: none")
    print("\nNote: The multiple-instance detection algorithm above determines the")
    print("deadlocked processes. A wait-for graph cycle is a useful diagnostic;")
    print("with multiple resource instances, a cycle alone is not always conclusive.")


def simulate_fifo(references: list[int], frame_count: int):
    frames: list[int] = []
    next_to_replace = 0
    faults = 0
    trace = []

    for page in references:
        hit = page in frames
        replaced = None
        if not hit:
            faults += 1
            if len(frames) < frame_count:
                frames.append(page)
            else:
                replaced = frames[next_to_replace]
                frames[next_to_replace] = page
                next_to_replace = (next_to_replace + 1) % frame_count
        trace.append((page, frames[:], "HIT" if hit else "FAULT", replaced))
    return faults, trace


def simulate_lru(references: list[int], frame_count: int):
    frames: list[int] = []
    last_used: dict[int, int] = {}
    faults = 0
    trace = []

    for time, page in enumerate(references):
        hit = page in frames
        replaced = None
        if not hit:
            faults += 1
            if len(frames) < frame_count:
                frames.append(page)
            else:
                least_recent_page = min(frames, key=lambda item: last_used[item])
                replaced = least_recent_page
                frames[frames.index(least_recent_page)] = page
        last_used[page] = time
        trace.append((page, frames[:], "HIT" if hit else "FAULT", replaced))
    return faults, trace


def print_page_trace(title: str, result: tuple[int, list]) -> None:
    faults, trace = result
    print(f"\n{title}")
    print("-" * 58)
    print(f"{'Step':<6}{'Page':<8}{'Frames':<22}{'Result':<10}{'Replaced'}")
    for step, (page, frames, status, replaced) in enumerate(trace, start=1):
        frame_text = str(frames)
        replaced_text = str(replaced) if replaced is not None else "-"
        print(f"{step:<6}{page:<8}{frame_text:<22}{status:<10}{replaced_text}")
    print(f"Total page faults: {faults}")


def run_page_analysis(data: dict[str, Any]) -> None:
    references = data.get("page_references")
    frame_count = data.get("frame_count")

    if not isinstance(references, list) or not references:
        raise ValueError("'page_references' must be a non-empty list.")
    if any(type(page) is not int or page < 0 for page in references):
        raise ValueError("Page references must be non-negative integers.")
    if type(frame_count) is not int or frame_count <= 0:
        raise ValueError("'frame_count' must be a positive integer.")

    print("\n" + "=" * 58)
    print("PAGE FAULT ANALYSIS")
    print("=" * 58)
    print("Reference string:", " ".join(map(str, references)))
    print("Number of frames:", frame_count)
    fifo = simulate_fifo(references, frame_count)
    lru = simulate_lru(references, frame_count)
    print_page_trace("FIFO (First In, First Out)", fifo)
    print_page_trace("LRU (Least Recently Used)", lru)
    print("\nComparison:")
    print(f"  FIFO page faults: {fifo[0]}")
    print(f"  LRU page faults:  {lru[0]}")
    if fifo[0] < lru[0]:
        print("  FIFO produced fewer page faults for this reference string.")
    elif lru[0] < fifo[0]:
        print("  LRU produced fewer page faults for this reference string.")
    else:
        print("  Both algorithms produced the same number of page faults.")


def load_data(path: str | None) -> dict[str, Any]:
    if path:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            raise ValueError(f"Input file not found: {path}")
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in input file: {error}")
    else:
        print("Enter the input as JSON. Press Ctrl+Z then Enter (Windows),")
        print("or Ctrl+D (macOS/Linux) when finished:")
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON input: {error}")

    if not isinstance(data, dict):
        raise ValueError("The top-level JSON value must be an object.")
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Detect resource deadlocks and compare FIFO/LRU page faults."
    )
    parser.add_argument(
        "--file", "-f", help="Path to a JSON file containing the simulation input."
    )
    parser.add_argument(
        "--deadlock-only", action="store_true",
        help="Run only the deadlock detector."
    )
    parser.add_argument(
        "--pages-only", action="store_true",
        help="Run only the page fault analyzer."
    )
    args = parser.parse_args()

    if args.deadlock_only and args.pages_only:
        parser.error("Choose either --deadlock-only or --pages-only, not both.")

    try:
        data = load_data(args.file)
        if not args.pages_only:
            run_deadlock_analysis(data)
        if not args.deadlock_only:
            run_page_analysis(data)
        print("\nAnalysis completed successfully.")
    except (ValueError, TypeError) as error:
        print(f"\nInput error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
