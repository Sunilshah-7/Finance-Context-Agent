# AMD GPU Plan (This plan is obsolete, no need to work on this plan)

## The Hardware Advantage We Are Demonstrating

AMD MI300X has 192 GB of HBM3 VRAM. Qwen2.5-72B in FP16 requires approximately 144 GB. This means a single MI300X runs the full 72B model with 48 GB of remaining VRAM headroom for KV cache.

NVIDIA H100 SXM has 80 GB. It cannot hold a 72B FP16 model on a single card. It requires:

- 2-GPU tensor-parallel setup (doubles cost, adds NVLink overhead)
- OR INT8 quantization (reduces model quality)
- OR reduced context length to fit within 80 GB

We never need to benchmark against NVIDIA directly. Published benchmarks from independent reviewers document this limitation. Our demo simply shows the capability: full FP16 70B class model, 65,536 token context window, single GPU. The hardware spec does the comparison for us.

## GPU Workloads (Why GPU Matters for Each)

| Workload                    | Why GPU is better than CPU                                                                   |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| 72B LLM inference           | CPU inference is 10-50x slower; impractical for any interactive use                          |
| 14B LLM inference           | CPU acceptable for very short calls, but GPU gives sub-second latency for structured outputs |
| BGE-large embedding (1024d) | Batch of 256 texts: GPU <1s vs CPU ~10s                                                      |
| BGE reranker cross-encoder  | 40 candidates: GPU ~200ms vs CPU ~3s                                                         |
| Parallel agent calls        | GPU serves multiple concurrent LLM requests efficiently; CPU cannot                          |

The embedding and reranking workloads are small but run frequently (every query triggers reranking). At GPU latency these are fast enough to be invisible to users. At CPU latency they dominate total response time.

## Model Serving Architecture

```
Docker Compose on AMD VM
├── vllm-72b (port 8000)     — Qwen/Qwen2.5-72B-Instruct
│   --tensor-parallel-size 1
│   --max-model-len 65536
│   --gpu-memory-utilization 0.85
│   --served-model-name fincontext-reasoner
│
├── vllm-14b (port 8001)     — Qwen/Qwen2.5-14B-Instruct
│   --tensor-parallel-size 1
│   --max-model-len 32768
│   --gpu-memory-utilization 0.45   (14B needs ~28 GB)
│   --served-model-name fincontext-planner
│
├── tei-embedding (port 8002) — BAAI/bge-large-en-v1.5
│   HuggingFace TEI image with ROCm backend
│
└── tei-reranker (port 8003)  — BAAI/bge-reranker-large
    HuggingFace TEI image with ROCm backend
```

Note: If the MI300X has enough VRAM to run 72B and 14B simultaneously (192 GB total, 72B uses ~144 GB, 14B uses ~28 GB, total ~172 GB), run both models simultaneously. If VRAM is tight, use a single vLLM instance with model swapping — but this adds ~2 minutes per swap which is unusable for interactive demos.

For MI300X (192 GB): run both simultaneously. For MI250X (128 GB): 72B may need to be FP8/INT8 quantized, or run only one model at a time.

## vLLM ROCm Startup Commands

Reference configuration:

```bash
# 72B reasoner — full FP16, long context
docker run --rm --device=/dev/kfd --device=/dev/dri \
  --group-add video --ipc=host \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e HF_HOME=/models/huggingface \
  -v ${MODEL_CACHE_DIR}:/models \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-72B-Instruct \
  --served-model-name fincontext-reasoner \
  --tensor-parallel-size 1 \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.85 \
  --host 0.0.0.0 \
  --port 8000

# 14B planner — lower GPU memory allocation, faster
docker run --rm --device=/dev/kfd --device=/dev/dri \
  --group-add video --ipc=host \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8001:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e HF_HOME=/models/huggingface \
  -v ${MODEL_CACHE_DIR}:/models \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-14B-Instruct \
  --served-model-name fincontext-planner \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.45 \
  --host 0.0.0.0 \
  --port 8000
```

These are managed by Docker Compose in `infra/amd-gpu/docker-compose.yml`. Use the Compose file in production.

## ROCm Troubleshooting

Common issues when first setting up vLLM on ROCm:

**`/dev/kfd not found`**
ROCm is not installed or the current user is not in the `video` group.

```bash
sudo usermod -aG video $USER && newgrp video
ls /dev/kfd  # should exist
```

**`Out of memory` during model load**

- Check current GPU memory: `rocm-smi`
- If another process is using the GPU: `fuser /dev/kfd` and kill it
- Reduce `--gpu-memory-utilization` to 0.80

**`CUDA_VISIBLE_DEVICES` errors in vLLM ROCm**
vLLM ROCm uses `HIP_VISIBLE_DEVICES` or `ROCR_VISIBLE_DEVICES`, not `CUDA_VISIBLE_DEVICES`.

```bash
export HIP_VISIBLE_DEVICES=0
```

**Model download fails**

- Check HF_TOKEN is set and valid
- Check HuggingFace model access (Qwen2.5-72B requires accepting model terms)
- Try `huggingface-cli download Qwen/Qwen2.5-72B-Instruct` interactively first

**vLLM build from source (if Docker image has ROCm compatibility issues)**

```bash
git clone https://github.com/vllm-project/vllm.git
cd vllm
pip install -e ".[rocm]"
```

## TEI (Text Embeddings Inference) for ROCm

HuggingFace TEI is the recommended way to serve BGE models on AMD GPUs.

```bash
# BGE-large embedding service
docker run --device=/dev/kfd --device=/dev/dri \
  --group-add video \
  -p 8002:80 \
  -v ${MODEL_CACHE_DIR}/tei:/data \
  -e HF_TOKEN="${HF_TOKEN}" \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id BAAI/bge-large-en-v1.5 \
  --port 80

# BGE reranker service
docker run --device=/dev/kfd --device=/dev/dri \
  --group-add video \
  -p 8003:80 \
  -v ${MODEL_CACHE_DIR}/tei-reranker:/data \
  -e HF_TOKEN="${HF_TOKEN}" \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id BAAI/bge-reranker-large \
  --port 80
```

If the ROCm TEI image doesn't support your GPU model, fall back to CPU for embedding and reranking — the quality is the same, only throughput differs. For the demo, the embedding is pre-computed (pre-ingestion) so reranker latency is the only real-time bottleneck.

## Benchmark Plan

Run these 5 scenarios and record metrics for the benchmark panel:

| Scenario                         | Description                                    |
| -------------------------------- | ---------------------------------------------- |
| 1. Single 10-K analysis          | AMD 2025 10-K, one question about risk factors |
| 2. Disclosure diff               | AMD 2022 vs 2025 10-K, Item 1A comparison      |
| 3. 5-stock portfolio review      | Full demo portfolio, general portfolio review  |
| 4. Interactive Q&A (3 questions) | Streaming chat over pre-analyzed portfolio     |
| 5. Batch embedding               | Embed 1,000 chunks, measure throughput         |

Metrics to record for each:

```python
{
    "scenario": str,
    "input_tokens": int,
    "output_tokens": int,
    "time_to_first_token_ms": float,
    "total_latency_ms": float,
    "tokens_per_second": float,
    "gpu_memory_peak_gb": float,
    "concurrent_requests": int,
    "citation_pass_rate": float,  # for scenarios 1, 2, 3
}
```

Save results to `packages/evals/benchmark_results.json`. The React benchmark panel reads from this file.

## $100 Credit Usage Strategy

Rough GPU hour cost: ~$2/hr (check actual AMD Developer Cloud pricing at provisioning time).

$100 = ~50 GPU hours.

| Activity                                       | Estimated GPU hours |
| ---------------------------------------------- | ------------------- |
| Initial model download and vLLM startup tests  | 2 hours             |
| Pre-ingestion (embedding 15,000 chunks)        | 1 hour              |
| Development iterations (agent graph debugging) | 8 hours             |
| End-to-end testing and benchmark collection    | 3 hours             |
| Demo day prep and practice runs                | 2 hours             |
| **Total estimated**                            | **16 hours**        |
| **Buffer remaining**                           | **~34 hours**       |

The buffer is large because we use 14B for most LLM calls and only 72B for the final memo. Every development call that doesn't need 72B quality should use the 14B model.

**Stop the vLLM containers when not actively coding.** The AMD VM itself does not cost money when idle, but GPU time does.

```bash
docker compose stop vllm-72b vllm-14b   # stop GPU work, Qdrant stays running
docker compose start vllm-72b vllm-14b  # restart when needed (3-5 min to reload 72B)
```
