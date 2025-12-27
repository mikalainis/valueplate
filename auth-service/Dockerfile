# 1 We use 1.23 here for the server, which is fine as long as go.mod says 1.21+
FROM golang:1.24-alpine
# FROM golang:1.24

#2
WORKDIR /app

# 4. Copy the definition files
COPY go.mod go.sum ./
# COPY go.mod ./

# 2. Download dependencies (This is faster/safer than 'tidy')
RUN go mod download

# 2. NOW run tidy
# It will read your main.go and graph/ folders, realize you need gqlgen, 
# and download the correct versions automatically.
# RUN go mod tidy

# 1. Copy ALL source code first (main.go, graph/, go.mod)
COPY . .

# Tidy up ensures everything is synced before building
# RUN go mod tidy

# ... (keep the top lines the same)

# Tidy up
RUN go mod tidy

# --- CHANGE CMD TO KEEP CONTAINER ALIVE ---
# We use tail -f /dev/null to make the container sit idle so we can fix it.
# CMD ["tail", "-f", "/dev/null"]

# 3. Build the application
RUN go build -o main .
# 
EXPOSE 8080
# 
CMD ["./main"]