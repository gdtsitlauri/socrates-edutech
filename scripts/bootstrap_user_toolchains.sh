#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${ROOT_DIR}/.tooling"
BIN_DIR="${TOOLS_DIR}/bin"
CONDA_ENV="${TOOLS_DIR}/conda-env"
DOTNET_DIR="${TOOLS_DIR}/dotnet"
SWIFT_DIR="${TOOLS_DIR}/swift"

mkdir -p "${BIN_DIR}"

download_dotnet() {
  if [[ -x "${DOTNET_DIR}/dotnet" ]]; then
    echo "dotnet already installed"
    return
  fi

  curl -fsSL https://dot.net/v1/dotnet-install.sh -o "${TOOLS_DIR}/dotnet-install.sh"
  bash "${TOOLS_DIR}/dotnet-install.sh" --channel 8.0 --install-dir "${DOTNET_DIR}"
}

download_micromamba() {
  if [[ -x "${BIN_DIR}/micromamba" ]]; then
    echo "micromamba already installed"
    return
  fi

  curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest -o "${TOOLS_DIR}/micromamba.tar.bz2"
  tar -xjf "${TOOLS_DIR}/micromamba.tar.bz2" -C "${TOOLS_DIR}"
  cp "${TOOLS_DIR}/bin/micromamba" "${BIN_DIR}/micromamba.tmp"
  mv "${BIN_DIR}/micromamba.tmp" "${BIN_DIR}/micromamba"
  chmod +x "${BIN_DIR}/micromamba"
}

install_conda_toolchains() {
  if [[ -x "${CONDA_ENV}/bin/php" && -x "${CONDA_ENV}/bin/ruby" && -x "${CONDA_ENV}/bin/sqlite3" ]]; then
    echo "conda toolchains already installed"
    return
  fi

  "${BIN_DIR}/micromamba" create -y -p "${CONDA_ENV}" -c conda-forge \
    php ruby sqlite openjdk=17 kotlin make cmake pkg-config

  if [[ ! -x "${CONDA_ENV}/bin/gfortran" ]]; then
    "${BIN_DIR}/micromamba" install -y -p "${CONDA_ENV}" -c conda-forge fortran-compiler || true
  fi

  if [[ ! -x "${CONDA_ENV}/bin/gfortran" ]]; then
    "${BIN_DIR}/micromamba" install -y -p "${CONDA_ENV}" -c conda-forge gfortran || true
  fi

  for command in php ruby bundle sqlite3 java javac kotlinc kotlin gradle; do
    if [[ -x "${CONDA_ENV}/bin/${command}" ]]; then
      ln -sf "${CONDA_ENV}/bin/${command}" "${BIN_DIR}/${command}"
    fi
  done

  if [[ -x "${CONDA_ENV}/bin/gfortran" ]]; then
    ln -sf "${CONDA_ENV}/bin/gfortran" "${BIN_DIR}/gfortran"
  elif [[ -x "${CONDA_ENV}/bin/x86_64-conda-linux-gnu-gfortran" ]]; then
    cat > "${BIN_DIR}/gfortran" <<EOF
#!/usr/bin/env bash
exec "${CONDA_ENV}/bin/x86_64-conda-linux-gnu-gfortran" "\$@"
EOF
    chmod +x "${BIN_DIR}/gfortran"
  fi
}

install_ruby_gems() {
  if [[ ! -x "${CONDA_ENV}/bin/ruby" ]]; then
    return
  fi

  export GEM_HOME="${TOOLS_DIR}/gems"
  export GEM_PATH="${GEM_HOME}"
  export PATH="${GEM_HOME}/bin:${CONDA_ENV}/bin:${BIN_DIR}:${PATH}"

  gem install bundler rspec rack-test sinatra
  ln -sf "${GEM_HOME}/bin/bundle" "${BIN_DIR}/bundle"
  ln -sf "${GEM_HOME}/bin/rspec" "${BIN_DIR}/rspec"
}

install_swift() {
  if [[ -x "${SWIFT_DIR}/usr/bin/swift" ]]; then
    echo "swift already installed"
    return
  fi

  local archive="swift-5.10.1-RELEASE-ubuntu22.04.tar.gz"
  local url="https://download.swift.org/swift-5.10.1-release/ubuntu2204/swift-5.10.1-RELEASE/${archive}"
  curl -fsSL "${url}" -o "${TOOLS_DIR}/${archive}"
  rm -rf "${SWIFT_DIR}"
  mkdir -p "${TOOLS_DIR}"
  tar -xzf "${TOOLS_DIR}/${archive}" -C "${TOOLS_DIR}"
  mv "${TOOLS_DIR}/swift-5.10.1-RELEASE-ubuntu22.04" "${SWIFT_DIR}"
  ln -sf "${SWIFT_DIR}/usr/bin/swift" "${BIN_DIR}/swift"
  ln -sf "${SWIFT_DIR}/usr/bin/swiftc" "${BIN_DIR}/swiftc"
}

main() {
  download_dotnet
  download_micromamba
  install_conda_toolchains
  install_ruby_gems
  install_swift

  echo
  echo "User-space toolchains installed under ${TOOLS_DIR}"
  echo "Run: source scripts/toolchain_env.sh"
}

main "$@"
