# References

These references were checked on 2026-05-06.

## NVIDIA NIM

- NVIDIA NIM documentation: https://docs.nvidia.com/nim/
- NVIDIA NIM OpenAI-compatible API examples: https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html
- NVIDIA hosted API catalog: https://build.nvidia.com/

Useful implementation notes from the official docs:

- NIM exposes OpenAI-compatible chat completions for supported LLMs.
- Provider-specific credentials and model IDs should stay inside the Inference Gateway.
- Agent API code should use logical model names such as `fincontext-planner` and `fincontext-reasoner`.

## HuggingFace

<<<<<<< HEAD
- HuggingFace Static Spaces documentation: https://huggingface.co/docs/hub/spaces-sdks-static
=======
- HuggingFace Spaces React documentation: https://huggingface.co/docs/hub/spaces-sdks-static
>>>>>>> origin/dev
- HuggingFace Text Embeddings Inference documentation: https://huggingface.co/docs/text-embeddings-inference/index

Useful implementation notes:

<<<<<<< HEAD
- HuggingFace Static Spaces provide the public React demo surface for judges.
- HuggingFace Hub hosts the Qwen and BGE models used by the AMD GPU backend.
=======
- React Spaces provide a simple public demo surface for judges.
- HuggingFace Spaces provides the public React demo surface.
>>>>>>> origin/dev
