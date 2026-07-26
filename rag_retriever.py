"""
RAG RETRIEVER
-----------------
"Agentic RAG" means: the agent retrieves relevant knowledge BEFORE
reasoning, instead of relying only on what the model already knows.

We use TF-IDF (a classic, lightweight text-similarity method from
scikit-learn) instead of a heavy embedding model, so this works
immediately with no extra downloads or API calls.

Install: pip install scikit-learn
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from knowledge_base import KNOWLEDGE_BASE

# Build the TF-IDF index once, when this module is imported
_doc_texts = [doc["text"] for doc in KNOWLEDGE_BASE]
_vectorizer = TfidfVectorizer(stop_words="english")
_doc_matrix = _vectorizer.fit_transform(_doc_texts)


def retrieve_relevant_docs(query, top_k=2):
    """
    Given a query (e.g. a description of the instance's current situation),
    returns the top_k most relevant knowledge base documents.

    This is the actual "retrieval" step of RAG: we search our knowledge
    source for what's relevant BEFORE handing anything to the LLM.
    """
    query_vector = _vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, _doc_matrix)[0]

    # Rank documents by similarity score, highest first
    ranked_indices = similarities.argsort()[::-1][:top_k]

    results = []
    for i in ranked_indices:
        results.append({
            "title": KNOWLEDGE_BASE[i]["title"],
            "text": KNOWLEDGE_BASE[i]["text"],
            "score": round(float(similarities[i]), 3)
        })
    return results


if __name__ == "__main__":
    # Quick manual test
    test_query = "instance running at 0% CPU after training completed"
    results = retrieve_relevant_docs(test_query)
    print(f"Query: {test_query}\n")
    for r in results:
        print(f"[{r['score']}] {r['title']}")
        print(f"  {r['text']}\n")
