#!/bin/bash
set -euo pipefail
exec poetry -C "$(dirname "${0}")" run main "$@"
