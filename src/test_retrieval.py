import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from municipal.core.config import Settings
from municipal.vectordb.store import VectorStore
from municipal.rag.retrieve import Retriever

def main():
    settings = Settings()
    store = VectorStore(settings.vectordb)
    retriever = Retriever(store)
    
    question = "can you help me get trash service?"
    print(f"Querying: {question}")
    results = retriever.retrieve(question, collection="ordinances")
    print(f"Found {len(results)} results.")
    for r in results:
        print(f"---")
        print(f"Score: {r.confidence_score}")
        print(f"Source: {r.source}")
        print(f"Text: {r.content[:200]}...")

if __name__ == "__main__":
    main()
