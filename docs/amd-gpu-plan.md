# AMD GPU Plan

## GPU Responsibilities

Use AMD GPUs for the workloads that benefit from high memory bandwidth, large batch processing, and concurrent inference:

- LLM inference for long-context filing analysis.
- Embedding generation for document chunks.
- Reranking retrieved evidence.
- Batch summarization across filings.
- Parallel agent calls during portfolio reviews.
- Benchmarking throughput and latency.

## Recommended Runtime

- AMD Developer Cloud GPU instance with AMD Instinct class GPU.
- Linux container environment.
- ROCm.
- vLLM OpenAI-compatible server.
- Hugging Face models downloaded with access tokens where required.

## Model Choices

MVP:

- Reasoning model: `Qwen/Qwen2.5-72B-Instruct` or a smaller Qwen/Llama/Mistral model depending on available GPU memory.
- Fast summarizer: `Qwen/Qwen2.5-14B-Instruct`.
- Embeddings: `BAAI/bge-large-en-v1.5` or `intfloat/e5-large-v2`.
- Reranker: `BAAI/bge-reranker-large`.

Production exploration:

- Llama 3.1/3.3 long-context variants.
- Mistral Large-compatible open models where licensing permits.
- Finance-tuned models for classification after evaluation.

## vLLM Serving Pattern

Use vLLM with an OpenAI-compatible API so the Cloudflare Worker and Python agent service can call the same interface.

Example command template:

```bash
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -e HF_TOKEN="$HF_TOKEN" \
  vllm/vllm-openai-rocm:latest \
  --model Qwen/Qwen2.5-72B-Instruct \
  --served-model-name fincontext-reasoner \
  --tensor-parallel-size 1 \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.90 \
  --host 0.0.0.0 \
  --port 8000
```

Tune these values by GPU:

- `--tensor-parallel-size`: number of GPUs used by the model.
- `--max-model-len`: context length for filings and retrieved evidence.
- `--gpu-memory-utilization`: start at 0.85-0.90.
- batch/concurrency settings: tune after benchmark.

## Inference Gateway

Create a small internal service that hides model routing:

```text
/v1/chat/completions -> vLLM reasoner
/v1/embeddings -> embedding service
/v1/rerank -> reranker service
/health -> runtime health
/metrics -> Prometheus/OpenTelemetry metrics
```

Benefits:

- Cloudflare only needs one trusted origin.
- Models can be swapped without UI changes.
- Benchmarks can compare model variants.
- Rate limits and audit logs are centralized.

## Benchmark Plan

Benchmark scenarios:

1. Single 10-K analysis.
2. Latest vs prior 10-Q diff.
3. Five-stock portfolio review.
4. Twenty-stock portfolio review.
5. Interactive Q&A over retrieved citations.

Record:

- input tokens.
- output tokens.
- time to first token.
- total latency.
- tokens/sec.
- GPU memory usage.
- concurrent requests.
- citation verification pass rate.
- cost proxy: GPU minutes per job.

## AMD Demo Talking Points

- Large filings are context-heavy and memory-heavy.
- AMD GPUs let the system run open-source models with long context and high concurrency.
- Batch filing analysis maps naturally to GPU throughput.
- Multi-agent workflows create many model calls that can be served efficiently with vLLM.
- ROCm containers make the inference stack reproducible.

