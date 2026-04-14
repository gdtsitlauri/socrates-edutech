#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/toolchain_env.sh"
status=0

check_command() {
  local name="$1"
  shift
  echo "==> ${name}"
  if "$@"; then
    echo
  else
    status=1
    echo
  fi
}

require_version() {
  local label="$1"
  local cmd="$2"
  local version_cmd="$3"

  if command -v "${cmd}" >/dev/null 2>&1; then
    check_command "${label}" bash -lc "${version_cmd}"
  else
    echo "==> ${label}"
    echo "missing: ${cmd}"
    echo
    status=1
  fi
}

require_version "Python" "python3" "python3 --version"
require_version ".NET" "dotnet" "dotnet --version"
require_version "PHP" "php" "php --version | head -n 1"
require_version "Ruby" "ruby" "ruby --version"
require_version "Bundler" "bundle" "bundle --version"
require_version "Swift" "swift" "swift --version"
require_version "Kotlin" "kotlinc" "kotlinc -version"
require_version "Perl" "perl" "perl -v | head -n 2 | tail -n 1"
require_version "gfortran" "gfortran" "gfortran --version | head -n 1"
require_version "f2py" "f2py" "f2py -v"
require_version "SQLite" "sqlite3" "sqlite3 --version"

if [[ -f "${ROOT_DIR}/src/php/lms_api.php" ]] && command -v php >/dev/null 2>&1; then
  check_command "PHP syntax" php -l "${ROOT_DIR}/src/php/lms_api.php"
fi

if [[ -f "${ROOT_DIR}/src/perl/content_processor.pl" ]] && command -v perl >/dev/null 2>&1; then
  check_command "Perl syntax" perl -c "${ROOT_DIR}/src/perl/content_processor.pl"
fi

exit "${status}"
