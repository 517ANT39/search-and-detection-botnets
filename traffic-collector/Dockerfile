FROM golang:1.26-alpine AS builder

RUN apk add --no-cache git ca-certificates
RUN apk add --no-cache make
WORKDIR /app
COPY . .

RUN make build

FROM alpine:latest

COPY --from=builder /app/bin/traffic-collector .
COPY config.yaml .

CMD [ "./traffic-collector" ]