Tags: [[Tech]]

# What is LangChain
Framework to create LLM based workflows in the form of chains of linked LLMs
# Steps
- **Retrieval -** Data retrieval using text splitter, doc loader etc.
- **Summarise -** Chain (prompt component to generate summary, LLM component)
- **Answer -** Chain (Memory component to store conversation history and context, prompt component , LLM component)

# LangGraph
Library in LangChain to build stateful multi agent systems. It can handle complex  non-linear workflows.
- **State component -** Maintains task list across all operations. Other components can modify this.

# LangChain vs LangGraph
- LangChain is an abstraction layer for LLM applications. LangGraph is a system for multi agent applications.
- LangChain has memory components but no robust state component. LangGraph has a state component.