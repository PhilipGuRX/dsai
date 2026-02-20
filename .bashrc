#!/bin/bash

# Local .bashrc for this repository
# This file contains project-specific bash configurations

# Add LM Studio to PATH for this project (uncomment and update if you install LM Studio)
# export PATH="$PATH:/Applications/LM Studio.app/Contents/MacOS"

# Add Ollama to PATH for this project (uncomment if you install Ollama)
# export PATH="$PATH:/usr/local/bin"
# alias ollama='/usr/local/bin/ollama'

# Add R to your Path for this project
export PATH="$PATH:/usr/local/bin"
alias Rscript='/usr/local/bin/Rscript'
# Add R libraries to your path for this project
export R_LIBS_USER="/Library/Frameworks/R.framework/Versions/4.2/Resources/library"

# Add Python to your Path for this project
export PATH="$PATH:/Library/Frameworks/Python.framework/Versions/3.12/bin"
alias python='/Library/Frameworks/Python.framework/Versions/3.12/bin/python3'
alias pip='/Library/Frameworks/Python.framework/Versions/3.12/bin/pip3'

echo "✅ Local .bashrc loaded."
