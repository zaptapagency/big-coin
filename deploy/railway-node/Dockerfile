# MoonBite seed node for Railway.
# Build context MUST be the repo root (so we can COPY release/bin/bigcoind).
# In Railway: set the service Root Directory to "/" and Dockerfile Path to
# "deploy/railway-node/Dockerfile".
FROM ubuntu:22.04

# Runtime shared libraries the prebuilt bigcoind links against
# (from `ldd release/bin/bigcoind` — Ubuntu 22.04 / boost 1.74 build).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libboost-filesystem1.74.0 \
        libboost-thread1.74.0 \
        libdb5.3++ \
        libevent-2.1-7 \
        libevent-pthreads-2.1-7 \
        libfmt8 \
        libsqlite3-0 \
        libssl3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY release/bin/bigcoind /usr/local/bin/bigcoind
COPY release/bin/bigcoin-cli /usr/local/bin/bigcoin-cli
COPY deploy/railway-node/entrypoint.sh /entrypoint.sh
RUN chmod +x /usr/local/bin/bigcoind /usr/local/bin/bigcoin-cli /entrypoint.sh

# 9444 = P2P (expose publicly via Railway TCP Proxy).
# 9445 = JSON-RPC (keep PRIVATE — only the explorer service reaches it over
#        Railway's internal network; never attach a public domain to it).
EXPOSE 9444 9445

ENTRYPOINT ["/entrypoint.sh"]
