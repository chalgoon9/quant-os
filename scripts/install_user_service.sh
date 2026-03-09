#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
template_path="$repo_root/deploy/systemd/quant-os.service.in"
target_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
target_path="$target_dir/quant-os.service"
uv_bin="${UV_BIN:-$(command -v uv || true)}"

if [[ -z "${uv_bin}" ]]; then
  echo "uv binary not found" >&2
  exit 1
fi

mkdir -p "$target_dir"

sed \
  -e "s|@REPO_ROOT@|$repo_root|g" \
  -e "s|@UV_BIN@|$uv_bin|g" \
  "$template_path" > "$target_path"

systemctl --user daemon-reload
systemctl --user enable --now quant-os.service
systemctl --user restart quant-os.service
systemctl --user --no-pager --full status quant-os.service
