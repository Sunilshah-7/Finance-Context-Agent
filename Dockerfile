FROM node:20-bookworm AS ui
WORKDIR /app/apps/demo-ui
COPY apps/demo-ui/package*.json ./
RUN npm install
COPY apps/demo-ui/ ./
RUN npm run build

FROM golang:1.25-bookworm AS backend
WORKDIR /app
COPY backend/go.mod backend/go.sum* ./backend/
WORKDIR /app/backend
RUN go mod download
WORKDIR /app
COPY backend/ ./backend/
RUN cd backend && CGO_ENABLED=0 GOOS=linux go build -o /out/fincontext ./cmd/fincontext

FROM gcr.io/distroless/static-debian12
WORKDIR /app
COPY --from=backend /out/fincontext /app/fincontext
COPY --from=ui /app/apps/demo-ui/out /app/public
COPY data/fixtures /app/data/fixtures
ENV PORT=7860
ENV FIXTURE_DIR=/app/data/fixtures
ENV STATIC_DIR=/app/public
EXPOSE 7860
ENTRYPOINT ["/app/fincontext"]
