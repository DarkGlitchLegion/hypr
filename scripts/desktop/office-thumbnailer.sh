#!/usr/bin/env bash
set -euo pipefail

input=""
output=""
size="256"

while getopts ":i:o:s:" option; do
    case "${option}" in
        i) input="${OPTARG}" ;;
        o) output="${OPTARG}" ;;
        s) size="${OPTARG}" ;;
    esac
done

if [[ -z "${input}" || -z "${output}" ]]; then
    exit 2
fi

work_dir="$(mktemp -d)"
profile_dir="$(mktemp -d)"
trap 'rm -rf -- "${work_dir}" "${profile_dir}"' EXIT

soffice --headless \
    "-env:UserInstallation=file://${profile_dir}" \
    --convert-to pdf --outdir "${work_dir}" "${input}" >/dev/null 2>&1

pdf="${work_dir}/$(basename "${input%.*}").pdf"
if [[ ! -f "${pdf}" ]]; then
    pdf="$(find "${work_dir}" -maxdepth 1 -type f -name '*.pdf' -print -quit)"
fi
[[ -n "${pdf:-}" && -f "${pdf}" ]] || exit 1

pdftoppm -f 1 -l 1 -singlefile -png -scale-to-x "${size}" -scale-to-y "-1" "${pdf}" "${work_dir}/preview" >/dev/null 2>&1
preview="${work_dir}/preview.png"
[[ -f "${preview}" ]] || exit 1

mkdir -p "$(dirname "${output}")"
cp -f -- "${preview}" "${output}"
