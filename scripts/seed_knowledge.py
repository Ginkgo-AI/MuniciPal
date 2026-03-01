import sys
from pathlib import Path

# Ensure the project source is importable when running the script directly.
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from municipal.core.config import Settings
from municipal.rag.pipeline import create_rag_pipeline

# All directories to ingest, in order
SOURCE_DIRS = [
    _project_root / "data" / "sample_ordinances",
    _project_root / "data" / "ordinances" / "roanoke",
]

def main():
    settings = Settings()
    pipeline = create_rag_pipeline(settings)

    total = 0
    for data_dir in SOURCE_DIRS:
        if not data_dir.exists():
            print(f"Skipping {data_dir} (not found)")
            continue
        md_files = list(data_dir.glob("*.md"))
        if not md_files:
            print(f"Skipping {data_dir} (no .md files)")
            continue
        print(f"Ingesting {len(md_files)} documents from {data_dir}...")
        results = pipeline.ingest(str(data_dir))
        count = len(results) if isinstance(results, list) else 1
        total += count
        print(f"  ✅ Ingested {count} documents")

    print(f"\nDone! Total: {total} documents ingested.")

if __name__ == "__main__":
    main()

