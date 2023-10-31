#!/bin/bash

set -euo pipefail

# https://unix.stackexchange.com/questions/462156/how-do-i-find-the-line-number-in-bash-when-an-error-occured
failure() {
  local lineno=$1
  local msg=$2
  echo "Failed at $lineno: $msg"
}
trap 'failure ${LINENO} "$BASH_COMMAND"' ERR

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Using CFF=${CFF:=$(realpath "$SCRIPT_DIR/../clang-format-find.py")}"
echo "Using SRC=${SRC:=$(realpath "$SCRIPT_DIR/src")}"
echo "Using OUT=${OUT:=$(realpath "$SCRIPT_DIR/out")}"

gold=$(realpath "$SCRIPT_DIR/gold")

srcs=$(find "$SRC" -name '*.cpp')

mkdir -p "$OUT"

$CFF $srcs > "$OUT/test0.txt"

if ! cmp "$OUT/test0.txt" "$gold/test0.txt"; then
    diff -y "$gold/test0.txt" "$OUT/test0.txt" || true
    echo "TEST0 failed, see diff above (expected on left, actual on right)"
    exit 1
fi

echo "ALL TESTS PASSED"
