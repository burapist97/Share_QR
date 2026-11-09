#!/bin/bash
# Mac'te çift tıklayarak çalıştırın. Bu dosyanın üstüne dosya/klasör da sürükleyebilirsiniz.
cd "$(dirname "$0")"
python3 qr_paylas.py "$@"
