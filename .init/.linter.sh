#!/bin/bash
cd /home/kavia/workspace/code-generation/vericheck-fact-verification-platform-211511-211520/fact_checking_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

