FROM gradle:8.5-jdk17 AS builder

WORKDIR /app
COPY build.gradle .
COPY src/ src/
COPY routes/ routes/

RUN gradle build --no-daemon -x test

FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Kopiowanie zbudowanej aplikacji
COPY --from=builder /app/build/libs/*.jar app.jar
COPY --from=builder /app/routes/ routes/

# Katalogi dla plików
RUN mkdir -p /app/outbox /app/inbox /app/processed

# Zmienne środowiskowe
ENV EDORECZENIA_API_URL=http://edoreczenia-simulator:8080
ENV EDORECZENIA_ADDRESS=AE:PL-12345-67890-ABCDE-12
ENV EDORECZENIA_CLIENT_ID=test_client_id
ENV EDORECZENIA_CLIENT_SECRET=test_client_secret
ENV IMAP_HOST=dovecot
ENV IMAP_PORT=143
ENV IMAP_USER=mailuser
ENV IMAP_PASSWORD=mailpass123
ENV SMTP_HOST=edoreczenia-proxy
ENV SMTP_PORT=1025
ENV SMTP_USER=testuser
ENV SMTP_PASSWORD=testpass123
ENV AUTO_SYNC=false
ENV FILE_WATCH=false

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:8090/api/v1/messages || exit 1

CMD ["java", "-jar", "app.jar"]
