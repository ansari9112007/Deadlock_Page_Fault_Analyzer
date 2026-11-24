# Deadlock Detector and Page Fault Analyzer

A Python command-line simulator that:
- Builds a wait-for graph from allocation and outstanding-request matrices.
- Detects deadlocked processes using the multiple-instance deadlock detection algorithm.
- Simulates FIFO and LRU page replacement.
- Prints step-by-step page traces and total page-fault counts.
- Accepts JSON input from a file or standard input.

## Requirements
- Python 3.10 or newer
- No third-party packages are required.

## Project files
- `main.py` — application and algorithms
- `sample_input.json` — ready-to-run example input

## Run on Windows (VS Code terminal)
1. Open this project folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Run:

```bash
python main.py --file sample_input.json
```

If `python` does not work on your computer, try `py main.py --file sample_input.json`.

## Run from standard input
Run:

```bash
python main.py
```

Then paste JSON in the terminal and finish input with **Ctrl+Z**, then **Enter** on Windows. On macOS/Linux, use **Ctrl+D**.

## Optional modes

```bash
python main.py --file sample_input.json --deadlock-only
python main.py --file sample_input.json --pages-only
```

## Input format

```json
{
  "allocation": [
    [1, 0],
    [0, 1]
  ],
  "request": [
    [0, 1],
    [1, 0]
  ],
  "available": [0, 0],
  "page_references": [1, 2, 3, 1, 2, 4, 1, 2, 3, 4],
  "frame_count": 3
}
```

### Deadlock fields
- `allocation[i][r]`: number of instances of resource `r` currently held by process `i`.
- `request[i][r]`: additional instances of resource `r` currently requested by process `i`.
- `available[r]`: currently available instances of resource `r`.

The allocation and request matrices must have the same number of rows and columns. The available vector must have one entry per resource. Values must be non-negative integers.

The tool prints wait-for graph edges from a waiting process to processes holding the requested resource. It then applies the standard multiple-instance detection algorithm to identify processes that cannot complete.

**Important:** with multiple instances of a resource type, a wait-for graph cycle alone is not always sufficient to prove deadlock. The multiple-instance detection result is used as the authoritative status.

### Page analysis fields
- `page_references`: non-empty sequence of non-negative page numbers.
- `frame_count`: positive number of memory frames.

A page fault occurs when a referenced page is not currently in memory. FIFO replaces the page that entered memory earliest. LRU replaces the page that has not been used for the longest time.

## Example interpretation
The sample resource state creates a circular wait between P0 and P1, so the detector reports a deadlock. The page analyzer prints each reference, the frame contents, whether it was a hit or fault, and the replaced page (if any).

## Error handling
The program reports invalid JSON, missing files, mismatched matrix dimensions, negative/non-integer values, empty page-reference lists, and invalid frame counts.
