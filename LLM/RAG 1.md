Tags: [[Tech]]

# 🧠 Retrieval Augmented Generation (RAG)

Retrieval Augmented Generation (RAG) is a technique that enhances large language models by integrating external knowledge sources, improving accuracy, reliability, and reducing hallucinations. It allows models to cite sources and clarify ambiguous queries, making it faster and less expensive than retraining models.

It is a technique to enhance the accuracy and reliability of genAI models. It can be used by nearly any LLM to connect with practically any external resource.

Retrieval-augmented generation gives models sources they can cite, like footnotes in a research paper, so users can check any claims. That builds trust.

What's more, the technique can help models clear up ambiguity in a user query. It also reduces the possibility that a model will give a very plausible but incorrect answer, a phenomenon called hallucination.

That makes the method faster and less expensive than retraining a model with additional datasets. And it lets users hot-swap new sources on the fly.

![[Pasted image 20250625164623.png]]

# ⚙️ RAG Functioning

This section explains how RAG works, including the use of embeddings and vector databases to match queries with relevant knowledge.

When users ask an LLM a question:
1. The AI model sends the query to another model that converts it into a numeric format (embedding/vector)
2. The embedding model compares the embeddings to attached knowledge bases
3. Related data is passed to the LLM in human-readable format along with the user query

In the background:
- The embedding model continuously creates/updates machine-readable indices (vector databases)
- Updates occur as new knowledge bases become available or existing ones change

![[Pasted image 20250625165433.png]]

# 🔗 Links for Further Reference

This section provides external links for deeper understanding of RAG:

- [Langchain Blog - ChatGPT Over Your Data Tutorial](https://blog.langchain.com/tutorial-chatgpt-over-your-data/)
- [Meta AI Blog - RAG Explanation](https://ai.meta.com/blog/retrieval-augmented-generation-streamlining-the-creation-of-intelligent-natural-language-processing-models/)
