# References

These references were checked on 2026-05-06.

## AMD and ROCm

- AMD ROCm vLLM inference documentation: https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm.html
- AMD ROCm vLLM performance testing: https://rocmdocs.amd.com/en/latest/how-to/rocm-for-ai/inference/vllm-benchmark.html
- AMD Instinct MI300X performance guides: https://rocmdocs.amd.com/en/develop/how-to/gpu-performance/mi300x.html
- vLLM GPU installation documentation with AMD ROCm support: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/

Useful implementation notes from the official docs:

- ROCm provides prebuilt vLLM Docker environments for AMD Instinct GPUs.
- vLLM exposes OpenAI-compatible serving, which simplifies integration with existing agent frameworks.
- Current vLLM docs list AMD ROCm support for Linux environments and ROCm 6.3+.

## HuggingFace

- HuggingFace Static Spaces documentation: https://huggingface.co/docs/hub/spaces-sdks-static
- HuggingFace Text Embeddings Inference documentation: https://huggingface.co/docs/text-embeddings-inference/index

Useful implementation notes:

- HuggingFace Static Spaces provide the public React demo surface for judges.
- HuggingFace Hub hosts the Qwen and BGE models used by the AMD GPU backend.
