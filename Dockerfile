# Minimal image for the xaudaily MCP server (stdio transport).
#
# Why this file exists: MCP catalogs — Glama (https://glama.ai/mcp/servers) and
# similar — verify a server by building it in a container, starting it, and
# reading `initialize` / `tools/list` over JSON-RPC on stdin/stdout. So the image
# only has to do one thing well: start the server and answer introspection.
# No API key, no credentials, no network access is needed for that.
#
# The server is a single standard-library Python file, so there is nothing to
# install and no dependency lockfile to keep in sync.
#
#   docker build -t xaudaily-mcp .
#   docker run -i --rm xaudaily-mcp        # then write JSON-RPC to stdin
#
# Real usage (answering questions about gold data) additionally needs outbound
# network access to xaudaily.com — see README.md for the plain-Python install.

FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Wangxian111/xaudaily-gold-data" \
      org.opencontainers.image.description="Daily gold and macro readings from xaudaily.com for AI agents (stdio MCP server)" \
      org.opencontainers.image.licenses="CC-BY-4.0" \
      org.opencontainers.image.documentation="https://xaudaily.com/data/"

WORKDIR /app

# Only the server file is needed: it imports nothing outside the standard library.
COPY mcp_server.py ./

# stdout is the JSON-RPC channel. The server flushes after every message, so an
# introspection client that writes one request and waits for one reply is never
# left waiting on a buffer; PYTHONUNBUFFERED=1 is belt-and-braces for the same
# reason (a half-written reply would be parsed as a protocol error).
ENV PYTHONUNBUFFERED=1

# Exec form, no shell wrapper: stdin/stdout/signals pass straight through to the
# server, which is what an stdio client expects.
ENTRYPOINT ["python3", "mcp_server.py"]
