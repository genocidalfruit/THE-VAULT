Tags: [[Tech]]

## 🔧 Fine Tuning

Fine tuning is the process of training an LLM on data to bake it into its weights. This allows for less contextualization in the prompts (shorter prompts). Fine tuning is useful in scenarios where the model has to be specialized for one purpose.

## 🧰 Tools

- **QLoRA** - Quantization, Parameter efficient fine tuning (Drastically improves memory efficiency)
- **[Hugging Face PEFT](https://huggingface.co/docs/peft/en/index)** - PEFT (Parameter-Efficient Fine-Tuning) is a library for efficiently adapting large pretrained models to various downstream applications without fine-tuning all of a model's parameters because it is prohibitively costly. PEFT methods only fine-tune a small number of (extra) model parameters - significantly decreasing computational and storage costs - while yielding performance comparable to a fully fine-tuned model. This makes it more accessible to train and store large language models (LLMs) on consumer hardware. PEFT is integrated with the Transformers, Diffusers, and Accelerate libraries to provide a faster and easier way to load, train, and use large models for inference.

## 🔗 Useful Pages for Fine Tuning Process

- [Geek Out Time Part 2: Super Cheap Fine-Tuning Deepseek-7b](https://www.linkedin.com/pulse/geek-out-time-part-2-super-cheap-fine-tuning-deepseek-7b-nedved-yang-xe0jc) - Describes fine tuning of Deepseek-7b to serve as a Chinese tutoring QA chatbot
- [Perplexity Chat: LLM-powered DND Application](https://www.perplexity.ai/search/how-do-i-fine-tune-an-llm-for-LJ4TQG5hQsKuJ2o3EuNexQ) - Contains steps for LLM powered DND application
- [Fine-Tuning Deepseek Coder 6.7B](https://kennycason.com/posts/2025-03-10-finetuning-deepseek-coder-6.7b.html) - Code for a coding based Deepseek-6.7B model fine tuning
