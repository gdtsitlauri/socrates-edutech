#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_BIN="${ROOT_DIR}/.tooling/bin"

if [[ -d "${TOOLS_BIN}" ]]; then
  export PATH="${TOOLS_BIN}:${PATH}"
fi

if [[ -d "${ROOT_DIR}/.tooling/conda-env/bin" ]]; then
  export CONDA_PREFIX="${ROOT_DIR}/.tooling/conda-env"
  export PATH="${ROOT_DIR}/.tooling/conda-env/bin:${PATH}"
fi

if [[ -d "${ROOT_DIR}/.tooling/gems" ]]; then
  export GEM_HOME="${ROOT_DIR}/.tooling/gems"
  export GEM_PATH="${GEM_HOME}"
  export BUNDLE_PATH="${GEM_HOME}"
  export PATH="${GEM_HOME}/bin:${PATH}"
fi


if [[ -d "${ROOT_DIR}/.tooling/swift/usr/bin" ]]; then
  export PATH="${ROOT_DIR}/.tooling/swift/usr/bin:${PATH}"
  export LD_LIBRARY_PATH="${ROOT_DIR}/.tooling/swift/usr/lib/swift/linux:${LD_LIBRARY_PATH:-}"
fi

if [[ -d "${ROOT_DIR}/.tooling/dotnet" ]]; then
  export DOTNET_ROOT="${ROOT_DIR}/.tooling/dotnet"
  export PATH="${ROOT_DIR}/.tooling/dotnet:${PATH}"
fi
