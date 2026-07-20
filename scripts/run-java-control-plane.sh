#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
sdkman_init="${SDKMAN_DIR:-${HOME}/.sdkman}/bin/sdkman-init.sh"

if [[ -r "${sdkman_init}" ]]; then
  # shellcheck source=/dev/null
  set +u
  source "${sdkman_init}"
  set -u
  if command -v sdk >/dev/null 2>&1; then
    pushd "${repo_root}" >/dev/null
    set +u
    sdk env >/dev/null
    set -u
    popd >/dev/null
  fi
fi

java_version="$(java -version 2>&1 | head -n 1)"
if [[ "${java_version}" != *'"25'* ]]; then
  printf "Java 25 is required, but current runtime is: %s\n" "${java_version}" >&2
  printf "Install/select Java 25, for example: sdk install java 25-tem && sdk use java 25-tem\n" >&2
  exit 1
fi

jar_path="${repo_root}/java/control-plane/build/libs/control-plane-0.1.0-SNAPSHOT.jar"
if [[ "${LOB_ARENA_SKIP_JAVA_BUILD:-false}" != "true" || ! -r "${jar_path}" ]]; then
  (cd "${repo_root}/java" && ./gradlew :control-plane:bootJar --no-daemon)
fi

exec java -jar "${jar_path}" "$@"
