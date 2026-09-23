import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
def main():
    files=list(Path("docs").rglob("*.md"))
    print(f"Documentation files: {len(files)}")
if __name__=="__main__": main()
