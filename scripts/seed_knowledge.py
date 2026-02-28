import sys
from pathlib import Path

# Ensure the project source is importable when running the script directly.
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from municipal.core.config import Settings
from municipal.rag.pipeline import create_rag_pipeline

def main():
    settings = Settings()
    pipeline = create_rag_pipeline(settings)
    data_dir = _project_root / "data" / "sample_ordinances"
    print(f"Ingesting documents from {data_dir}...")
    
    if not data_dir.exists():
        print(f"Directory {data_dir} does not exist.")
        sys.exit(1)
        
    results = pipeline.ingest(str(data_dir))
    
    if isinstance(results, list):
        print(f"Ingested {len(results)} documents.")
    else:
        print(f"Ingested 1 document.")

if __name__ == "__main__":
    main()
