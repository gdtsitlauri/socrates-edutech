#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SWIFT_VERSION="${SWIFT_VERSION:-5.10.1}"
UBUNTU_CODENAME="${UBUNTU_CODENAME:-jammy}"

require_sudo() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Re-running with sudo for package installation..."
    exec sudo --preserve-env=SWIFT_VERSION,UBUNTU_CODENAME bash "$0" "$@"
  fi
}

install_base_packages() {
  apt-get update
  apt-get install -y \
    apt-transport-https \
    build-essential \
    ca-certificates \
    curl \
    gfortran \
    git \
    gnupg \
    libsqlite3-dev \
    perl \
    php-cli \
    python3 \
    python3-pip \
    python3-venv \
    ruby-full \
    sqlite3 \
    unzip \
    wget \
    zip
}

install_dotnet() {
  if command -v dotnet >/dev/null 2>&1; then
    dotnet --version
    return
  fi

  wget -q https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O /tmp/packages-microsoft-prod.deb
  dpkg -i /tmp/packages-microsoft-prod.deb
  apt-get update
  apt-get install -y dotnet-sdk-8.0
}

install_java_and_kotlin() {
  apt-get install -y openjdk-17-jdk kotlin
}

install_python_packages() {
  python3 -m pip install --upgrade pip
  python3 -m pip install numpy pytest
}

install_ruby_packages() {
  gem install bundler
}

install_swift() {
  if command -v swift >/dev/null 2>&1; then
    swift --version
    return
  fi

  local archive="swift-${SWIFT_VERSION}-RELEASE-ubuntu22.04.tar.gz"
  local url="https://download.swift.org/swift-${SWIFT_VERSION}-release/ubuntu2204/swift-${SWIFT_VERSION}-RELEASE/${archive}"
  wget -q "${url}" -O "/tmp/${archive}"
  tar -xzf "/tmp/${archive}" -C /opt
  ln -sf "/opt/swift-${SWIFT_VERSION}-RELEASE-ubuntu22.04/usr/bin/swift" /usr/local/bin/swift
  ln -sf "/opt/swift-${SWIFT_VERSION}-RELEASE-ubuntu22.04/usr/bin/swiftc" /usr/local/bin/swiftc
}

main() {
  require_sudo "$@"
  install_base_packages
  install_dotnet
  install_java_and_kotlin
  install_python_packages
  install_ruby_packages
  install_swift

  echo
  echo "SOCRATES WSL2 toolchain setup complete."
  echo "Next steps:"
  echo "  1. bash ${ROOT_DIR}/scripts/verify_toolchains.sh"
  echo "  2. python3 ${ROOT_DIR}/scripts/run_all_checks.py"
  echo "  3. python3 ${ROOT_DIR}/scripts/generate_results.py"
}

main "$@"
