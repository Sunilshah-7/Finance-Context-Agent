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

- HuggingFace Spaces React documentation: https://huggingface.co/docs/hub/spaces-sdks-static
- HuggingFace Text Embeddings Inference documentation: https://huggingface.co/docs/text-embeddings-inference/index

Useful implementation notes:

- React Spaces provide a simple public demo surface for judges.
- HuggingFace Spaces provides the public React demo surface.
