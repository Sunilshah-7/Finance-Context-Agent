---
title: FinContext Agent
colorFrom: slate
colorTo: blue
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
---

# FinContext Agent Demo UI

This directory contains the React/Vite demo console for FinContext Agent. It is
designed for HuggingFace Static Spaces and calls only the public Agent API.

## Local Development

```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Build

```bash
npm run build
npm run preview
```

The static build is emitted to `dist/` and is the artifact served by
HuggingFace Static Spaces.
