FROM eclipse-temurin:25-jdk-noble AS build

WORKDIR /workspace
COPY java/ java/
COPY contracts/proto/ contracts/proto/
RUN cd java && ./gradlew :control-plane:bootJar --no-daemon

FROM eclipse-temurin:25-jre-noble AS runtime

RUN groupadd --system lobarena \
    && useradd --system --gid lobarena --home-dir /app --shell /usr/sbin/nologin lobarena \
    && mkdir -p /app \
    && chown lobarena:lobarena /app
WORKDIR /app
COPY --from=build --chown=lobarena:lobarena /workspace/java/control-plane/build/libs/control-plane-*.jar app.jar

USER lobarena
EXPOSE 8080 50051
ENV LOB_KERNEL_GRPC_ENABLED=true \
    LOB_KERNEL_GRPC_PORT=50051 \
    LOB_KERNEL_OTLP_ENABLED=false \
    LOB_KERNEL_OTLP_METRICS_ENABLED=false
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
