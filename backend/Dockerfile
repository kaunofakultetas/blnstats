FROM python:3.14.2

WORKDIR /app


# Dependencies
RUN  apt-get update && \
    # Basic utilities
    apt-get -y install nano procps sqlite3 graphviz && \
    # LaTeX fonts
    apt-get -y install texlive texlive-latex-extra texlive-fonts-recommended dvipng cm-super && \ 
    # Clean up
    rm -rf /var/lib/apt/lists/*




# Various libraries
RUN pip install --no-cache-dir                  \
    requests==2.32.5                            \
    bs4==0.0.2                                  \
    joblib==1.5.3                               \
    bcrypt==5.0.0                               \
    python-dotenv==1.2.1                        \
    pandas==2.3.3

# Flask
RUN pip install --no-cache-dir                  \
    Flask==3.1.2                                \
    Flask-RESTful==0.3.10                       \
    Flask-Cors==6.0.2                           \
    Flask-SocketIO==5.6.0                       \
    Flask-Login==0.6.3

# Bitcoin specific
RUN pip install --no-cache-dir                  \
    pyln-proto==26.6.6                          \
    jsonrpclib-pelix==1.0.0                     \
    bech32==1.2.0                               \
    python-bitcoinrpc==1.0

# Charts
RUN pip install --no-cache-dir                  \
    matplotlib==3.10.8

# Tests
RUN pip install --no-cache-dir                  \
    pytest==9.0.2

# Mysql
RUN pip install --no-cache-dir                  \
    mysql-connector-python==9.5.0

# Prefect
RUN pip install --no-cache-dir                  \
    prefect==3.6.11



# Copy app source code
COPY . .


# Serve the API
EXPOSE 8000
CMD ["python3", "-u", "main.py", "--serve-api"]
