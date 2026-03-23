"""
Knowledge base loader for Tastyz Bakery AI System.

Loads FAQ and price list documents, chunks them, embeds them,
and stores them in a vector store (ChromaDB local or Pinecone cloud)
for RAG retrieval.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Lazy imports — only pulled in when actually needed
# so Django can start without all AI deps installed
# ──────────────────────────────────────────────────────────────


def _get_chroma_client(persist_dir: str):
    import chromadb

    return chromadb.PersistentClient(path=persist_dir)


def _get_embeddings(api_key: str, model: str):
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(openai_api_key=api_key, model=model)


def _get_chroma_vectorstore(persist_dir: str, collection_name: str, embeddings):
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def _get_pinecone_vectorstore(index_name: str, embeddings):
    """Return a LangChain vectorstore backed by Pinecone."""
    from django.conf import settings as django_settings
    from pinecone import Pinecone

    pc = Pinecone(api_key=django_settings.PINECONE_API_KEY)

    # Create index if it doesn't exist (1536 dims for text-embedding-3-small)
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        from pinecone import ServerlessSpec

        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=django_settings.PINECONE_ENVIRONMENT or "us-east-1",
            ),
        )
        logger.info("Created Pinecone index: %s", index_name)

    index = pc.Index(index_name)

    from langchain_pinecone import PineconeVectorStore

    return PineconeVectorStore(index=index, embedding=embeddings)


# ──────────────────────────────────────────────────────────────
# Document loading & chunking
# ──────────────────────────────────────────────────────────────

KB_DIR = Path(__file__).parent


def load_documents() -> list[dict]:
    """Load all knowledge base text files and return as list of dicts."""
    docs = []
    for filepath in KB_DIR.glob("*.txt"):
        text = filepath.read_text(encoding="utf-8")
        # Simple paragraph-based chunking
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        for i, chunk in enumerate(chunks):
            docs.append(
                {
                    "id": f"{filepath.stem}_{i}",
                    "text": chunk,
                    "metadata": {"source": filepath.name, "chunk": i},
                }
            )
        logger.info("Loaded %d chunks from %s", len(chunks), filepath.name)
    return docs


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


# ──────────────────────────────────────────────────────────────
# Build / refresh the vector store
# ──────────────────────────────────────────────────────────────


def _use_pinecone() -> bool:
    """Check if Pinecone is configured and should be used."""
    try:
        from django.conf import settings as django_settings

        return bool(getattr(django_settings, "PINECONE_API_KEY", ""))
    except Exception:
        return False


def build_knowledge_base(persist_dir: str, api_key: str, embedding_model: str) -> None:
    """
    Embed all knowledge base documents and persist them.
    Uses Pinecone if configured, otherwise falls back to ChromaDB (local).
    Safe to call multiple times — clears and rebuilds.
    """
    logger.info("Building Tastyz Bakery knowledge base …")

    embeddings = _get_embeddings(api_key, embedding_model)

    if _use_pinecone():
        logger.info("Using Pinecone vector store")
        vectorstore = _get_pinecone_vectorstore("tastyz-kb", embeddings)
    else:
        logger.info("Using ChromaDB vector store (local)")
        vectorstore = _get_chroma_vectorstore(persist_dir, "tastyz_kb", embeddings)

    docs = load_documents()
    if not docs:
        logger.warning("No documents found in knowledge base directory.")
        return

    texts = [d["text"] for d in docs]
    metadatas = [d["metadata"] for d in docs]
    ids = [d["id"] for d in docs]

    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    logger.info("Knowledge base built with %d chunks.", len(docs))


def get_retriever(persist_dir: str, api_key: str, embedding_model: str, k: int = 4):
    """
    Return a LangChain retriever.
    Uses Pinecone if configured, otherwise ChromaDB (local).
    """
    embeddings = _get_embeddings(api_key, embedding_model)

    if _use_pinecone():
        logger.info("Retriever using Pinecone")
        vectorstore = _get_pinecone_vectorstore("tastyz-kb", embeddings)
    else:
        vectorstore = _get_chroma_vectorstore(persist_dir, "tastyz_kb", embeddings)

    return vectorstore.as_retriever(search_kwargs={"k": k})
