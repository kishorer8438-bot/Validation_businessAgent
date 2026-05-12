import sys
from pathlib import Path
p = Path(sys.argv[1])
start = int(sys.argv[2]) if len(sys.argv)>2 else 1
end = int(sys.argv[3]) if len(sys.argv)>3 else None
lines = p.read_text().splitlines()
if end is None:
    end = len(lines)
for i in range(start-1, end):
    print(f"{i+1:04d}: {lines[i]}")
