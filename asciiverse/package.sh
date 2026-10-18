#!/bin/sh
# Packs the build into dist/bastet-<target>.tar.gz (.zip for Windows) for
# av: the binary at the top, with the man page, LICENSE and README.
#
#   asciiverse/package.sh x86_64-unknown-linux-musl
set -eu
cd "$(dirname "$0")/.."
target="$1"
case "$target" in *windows*) exe=.exe ;; *) exe= ;; esac
stage=stage/bastet
rm -rf "$stage" && mkdir -p "$stage" dist
cp "out/bastet$exe" out/bastet.6 LICENSE README "$stage/"
if [ -n "$exe" ]; then
  (cd "$stage" && zip -qr "../../dist/bastet-$target.zip" .)
else
  tar -czf "dist/bastet-$target.tar.gz" -C "$stage" .
fi
ls dist
