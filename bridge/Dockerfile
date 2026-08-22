FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY . .
RUN CGO_ENABLED=0 go test ./... && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /arena-bridge ./cmd/arena-bridge

FROM alpine:3.21
RUN adduser -D -h /home/arena arena
USER arena
WORKDIR /home/arena
COPY --from=build /arena-bridge /usr/local/bin/arena-bridge
ENTRYPOINT ["arena-bridge"]
