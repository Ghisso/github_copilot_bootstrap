FROM node:22-bookworm-slim AS nodejs

FROM nvcr.io/nvidia/cuda-dl-base:26.03-cuda13.2-devel-ubuntu24.04

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV UV_BREAK_SYSTEM_PACKAGES=1

COPY --from=nodejs /usr/local /usr/local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        bubblewrap \
        ca-certificates \
        curl \
        git \
        openssh-client \
        python3 \
        python3-pip \
        python3-venv \
        sudo \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g context-mode \
    && command -v context-mode \
    && context-mode --help >/dev/null

RUN set -eux; \
    if id -u "${USERNAME}" >/dev/null 2>&1; then \
        usermod --shell /bin/bash "${USERNAME}"; \
    else \
        existing_user="$(getent passwd "${USER_UID}" | cut -d: -f1 || true)"; \
        if [ -n "${existing_user}" ]; then \
            usermod -l "${USERNAME}" "${existing_user}"; \
            usermod -d "/home/${USERNAME}" -m "${USERNAME}"; \
            usermod --shell /bin/bash "${USERNAME}"; \
        else \
            if ! getent group "${USER_GID}" >/dev/null; then \
                groupadd --gid "${USER_GID}" "${USERNAME}"; \
            fi; \
            useradd --uid "${USER_UID}" --gid "${USER_GID}" -m --shell /bin/bash "${USERNAME}"; \
        fi; \
    fi; \
    mkdir -p "/home/${USERNAME}"; \
    chown -R "${USERNAME}:$(id -gn "${USERNAME}")" "/home/${USERNAME}"; \
    getent passwd "${USERNAME}"; \
    printf '%s ALL=(ALL) NOPASSWD:ALL\n' "${USERNAME}" > "/etc/sudoers.d/${USERNAME}"; \
    chmod 0440 "/etc/sudoers.d/${USERNAME}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN uv pip install --system --no-cache \
        "huggingface_hub>=1.0" \
        "semble[mcp]" \
    && python3 -c "import huggingface_hub, semble" \
    && command -v hf \
    && command -v semble

RUN mkdir -p "/home/${USERNAME}/.cache/huggingface" \
    && chown -R "${USERNAME}:$(id -gn "${USERNAME}")" "/home/${USERNAME}/.cache"

USER ${USERNAME}
WORKDIR /workspaces
