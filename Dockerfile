FROM ghcr.io/quarto-dev/quarto-full:latest

# System deps for R packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libcurl4-openssl-dev \
        libssl-dev \
        libxml2-dev \
        python3 python3-pip python3-venv git \
    && rm -rf /var/lib/apt/lists/*

# Use the SAME R and SAME lib that Quarto reports:
#   Path: /opt/R/4.3.3/lib/R
#   LibPaths: /opt/R/4.3.3/lib/R/library
ENV R_HOME=/opt/R/4.3.3
ENV R_LIBS_USER=/opt/R/4.3.3/lib/R/library

# Install knitr + rmarkdown + tidyverse + shiny + helpers
RUN /opt/R/4.3.3/bin/R -q -e "install.packages( \
      c('rmarkdown', 'knitr', 'tidyverse', 'shiny', 'plotly', 'DT'), \
      repos = 'https://cloud.r-project.org', \
      lib = '/opt/R/4.3.3/lib/R/library' \
    )"

# Optional: Python tooling
RUN pip3 install --no-cache-dir jupyter ipykernel matplotlib && \
    python3 -m ipykernel install --name=python3 --display-name 'Python 3'

# Shiny / Quarto apps typically listen on a port (e.g. 3838)
EXPOSE 3838

WORKDIR /project
