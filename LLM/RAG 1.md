Tags: [[Tech]]

# 🚀 Retrieval Augmented Generation (RAG) 

Retrieval Augmented Generation (RAG) is a technique that enhances large language models by integrating external knowledge sources, improving accuracy, reliability, and reducing hallucinations. It allows models to cite sources and clarify ambiguous queries, making it faster and less expensive than retraining models.

It is a technique to enhance the accuracy and reliability of genAI models. It can be used by nearly any LLM to connect with practically any external resource.

Retrieval-augmented generation gives models sources they can cite, like footnotes in a research paper, so users can check any claims. That builds trust.

What's more, the technique can help models clear up ambiguity in a user query. It also reduces the possibility that a model will give a very plausible but incorrect answer, a phenomenon called hallucination.

That makes the method faster and less expensive than retraining a model with additional datasets. And it lets users hot-swap new sources on the fly.

![[Pasted image 20250625164623.png]]

## RAG Functioning

This section explains how RAG works, including the use of embeddings and vector databases to match queries with relevant knowledge.

When users ask an LLM a question, the AI model sends the query to another model that converts it into a numeric format so machines can read it. The numeric version of the query is sometimes called an embedding or a vector.

Embedding model compares the embeddings to the attached knowledge bases and passes any related data to the LLM in human readable format along with the user query.

In the background, the embedding model continuously creates and updates machine-readable indices, sometimes called vector databases, for new and updated knowledge bases as they become available.

![[Pasted image 20250625165433.png]]

## Links for further reference

This section provides external links for deeper understanding of RAG.

- [Langchain Blog](https://blog.langchain.com/tutorial-chatgpt-over-your-data/)
- [Meta AI Blog](https://ai.meta.com/blog/retrieval-augmented-generation-streamlining-the-creation-of-intelligent-natural-language-processing-models/)
