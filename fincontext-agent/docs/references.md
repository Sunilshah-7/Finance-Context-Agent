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

## Cloudflare

- Cloudflare Pages overview: https://developers.cloudflare.com/pages/
- Cloudflare Pages Functions: https://developers.cloudflare.com/pages/functions/
- Cloudflare Pages Functions get started: https://developers.cloudflare.com/pages/functions/get-started/
- Cloudflare Workers overview: https://developers.cloudflare.com/workers/
- Cloudflare Workers AI product page: https://www.cloudflare.com/developer-platform/products/workers-ai/

Useful implementation notes from the official docs:

- Pages can deploy full-stack applications to Cloudflare's global network.
- Pages Functions run server-side code with Workers.
- Workers provide a serverless execution environment.
- Cloudflare's developer platform includes storage and AI-adjacent services such as R2, D1, Vectorize, and AI Gateway.

