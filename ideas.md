# 3 AMD Hackathon Project Ideas

## 1. AI DevOps Agent

**Short Description:**  
An AI agent that monitors logs, traces, failed builds, deployment errors, and incident reports, then diagnoses root causes, suggests fixes, and generates regression tests.

**Track:**  
Track 1: AI Agents & Agentic Workflows

**Why It Is Useful to AMD:**  
It shows how AMD GPUs can power real enterprise AI workflows, especially high-volume log analysis, debugging, and automated software reliability.

**How AMD Developer Cloud Can Be Used:**  
Use AMD Developer Cloud to run open-source LLMs for batch log analysis, multi-agent reasoning, and fast inference on large incident datasets.

**How Hugging Face Can Be Used:**  
Use Hugging Face models like Qwen, Llama, Mistral, or DeepSeek for reasoning, classification, and code/test generation. Deploy a demo on Hugging Face Spaces for public visibility.

---

## 2. FinContext Agent: Portfolio-Aware Financial Intelligence Platform

## Description
FinContext Agent is a large-context AI system designed for the financial sector that analyzes massive documents such as SEC filings, earnings transcripts, and financial reports, and connects them directly to a user’s portfolio. It generates risk scores, detects changes in financial disclosures over time, and produces citation-backed analyst insights on how new information impacts portfolio exposure and investment decisions.

## Track
Track 1: AI Agents & Agentic Workflows  
(Optional extension: Track 3 if multimodal PDF/table understanding is included)

## How AMD GPUs Are Used
AMD GPUs power large-context inference, enabling the system to process long financial documents (10-K, 10-Q, earnings transcripts) and run multi-agent reasoning pipelines. High memory GPUs allow efficient handling of large text inputs, batch document analysis, and comparison across multiple filings.

## How AMD Developer Cloud Can Be Used
AMD Developer Cloud is used to run open-source LLMs for document parsing, retrieval, and reasoning. It supports high-throughput processing of financial datasets, enables multi-agent workflows for risk analysis and portfolio impact evaluation, and provides scalable infrastructure for real-time inference and benchmarking.

## How Hugging Face Is Being Used
Hugging Face is used for accessing and deploying open-source LLMs (Qwen, Llama, Mistral), embeddings (BGE, E5), and rerankers for retrieval pipelines. It also supports dataset usage for financial documents and provides Hugging Face Spaces for building and showcasing the live demo interface.

## Potential Customers
- Investment firms and hedge funds  
- Financial analysts and research teams  
- Banks and asset management companies  
- FinTech startups  
- Individual investors seeking advanced portfolio insights  

---

## 3. AI Kernel Optimization Agent

**Short Description:**  
An advanced developer tool where an AI agent analyzes slow GPU code, suggests optimizations, generates improved kernels, and benchmarks performance.

**Track:**  
Track 1: AI Agents & Agentic Workflows  
Optional: Track 2 if you fine-tune a code model for ROCm/kernel optimization

**Why It Is Useful to AMD:**  
This directly supports AMD’s ROCm ecosystem by helping developers write faster GPU code and making AMD hardware easier to use.

**How AMD Developer Cloud Can Be Used:**  
Use AMD Developer Cloud to compile, run, and benchmark GPU kernels on AMD hardware. The agent can compare baseline vs optimized performance.

**How Hugging Face Can Be Used:**  
Use Hugging Face code models like DeepSeek-Coder, CodeLlama, Qwen-Coder, or StarCoder for code analysis, kernel generation, and optimization suggestions.
