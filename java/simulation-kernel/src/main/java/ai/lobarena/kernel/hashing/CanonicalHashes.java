package ai.lobarena.kernel.hashing;

import ai.lobarena.exchange.v1.AddOrder;
import ai.lobarena.exchange.v1.BookSnapshot;
import ai.lobarena.exchange.v1.CancelOrder;
import ai.lobarena.exchange.v1.EventMetadata;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.ModifyOrder;
import ai.lobarena.exchange.v1.PriceLevel;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public final class CanonicalHashes {
    private static final byte[] EVENT_DOMAIN = "LOB-EVENT-V1\0".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] BOOK_DOMAIN = "LOB-BOOK-V1\0".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] STREAM_INIT_DOMAIN = "LOB-STREAM-INIT-V1\0".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] STREAM_STEP_DOMAIN = "LOB-STREAM-STEP-V1\0".getBytes(StandardCharsets.US_ASCII);
    private static final int SHA256_SIZE = 32;

    private CanonicalHashes() {}

    public static byte[] canonicalEventBytes(ExchangeEvent event) {
        CanonicalWriter writer = new CanonicalWriter();
        writer.raw(EVENT_DOMAIN);
        writeMetadata(writer, event.getMetadata());
        switch (event.getPayloadCase()) {
            case ADD -> {
                writer.u8(1);
                writeRestingOrder(writer, event.getAdd());
            }
            case MODIFY -> {
                writer.u8(2);
                ModifyOrder modify = event.getModify();
                writer.string(modify.getOrderId());
                writer.string(modify.getAgentId());
                writer.u8(modify.getSideValue());
                writer.i64(modify.getPreviousPriceTicks());
                writer.i64(modify.getPreviousQuantityLots());
                writer.i64(modify.getPriceTicks());
                writer.i64(modify.getQuantityLots());
                writer.bool(modify.getPriorityPreserved());
                writer.string(modify.getOwner());
            }
            case CANCEL -> {
                writer.u8(3);
                writeRestingOrder(writer, event.getCancel());
            }
            case EXECUTE -> {
                writer.u8(4);
                var execute = event.getExecute();
                writer.string(execute.getExecutionId());
                writer.string(execute.getAggressorOrderId());
                writer.string(execute.getRestingOrderId());
                writer.string(execute.getAggressorAgentId());
                writer.string(execute.getRestingAgentId());
                writer.u8(execute.getAggressorSideValue());
                writer.i64(execute.getPriceTicks());
                writer.i64(execute.getQuantityLots());
                writer.i64(execute.getAggressorRemainingQuantityLots());
                writer.i64(execute.getRestingRemainingQuantityLots());
            }
            case SNAPSHOT -> {
                writer.u8(5);
                writer.u32(event.getSnapshot().getDepth());
                writeBookBody(writer, event.getSnapshot().getBook());
            }
            case PAYLOAD_NOT_SET -> throw new IllegalArgumentException(
                    "exchange event must contain exactly one supported payload");
        }
        return writer.bytes();
    }

    public static byte[] eventHash(ExchangeEvent event) {
        return sha256(canonicalEventBytes(event));
    }

    public static byte[] canonicalBookBytes(BookSnapshot book) {
        CanonicalWriter writer = new CanonicalWriter();
        writer.raw(BOOK_DOMAIN);
        writeBookBody(writer, book);
        return writer.bytes();
    }

    public static byte[] bookHash(BookSnapshot book) {
        return sha256(canonicalBookBytes(book));
    }

    public static byte[] initialStreamHash(int contractVersion) {
        CanonicalWriter writer = new CanonicalWriter();
        writer.raw(STREAM_INIT_DOMAIN);
        writer.u32(contractVersion);
        return sha256(writer.bytes());
    }

    public static byte[] advanceStreamHash(byte[] previousHash, byte[] nextEventHash) {
        if (previousHash.length != SHA256_SIZE || nextEventHash.length != SHA256_SIZE) {
            throw new IllegalArgumentException("stream hash inputs must be 32-byte SHA-256 digests");
        }
        MessageDigest digest = sha256Digest();
        digest.update(STREAM_STEP_DOMAIN);
        digest.update(previousHash);
        digest.update(nextEventHash);
        return digest.digest();
    }

    public static byte[] eventStreamHash(Iterable<ExchangeEvent> events, int contractVersion) {
        byte[] digest = initialStreamHash(contractVersion);
        long expectedSequence = 1;
        for (ExchangeEvent event : events) {
            EventMetadata metadata = event.getMetadata();
            if (metadata.getSchemaVersion() != contractVersion) {
                throw new IllegalArgumentException("event schema version does not match stream contract version");
            }
            if (metadata.getSequence() != expectedSequence) {
                throw new IllegalArgumentException(
                        "expected contiguous event sequence " + expectedSequence + ", got " + metadata.getSequence());
            }
            digest = advanceStreamHash(digest, eventHash(event));
            expectedSequence = Math.incrementExact(expectedSequence);
        }
        return digest;
    }

    private static void writeMetadata(CanonicalWriter writer, EventMetadata metadata) {
        if (metadata.getSchemaVersion() != 1) {
            throw new IllegalArgumentException("canonical event hashing supports schema version 1");
        }
        if (metadata.getSequence() == 0) {
            throw new IllegalArgumentException("canonical event sequence must start at 1");
        }
        writer.u32(metadata.getSchemaVersion());
        writer.string(metadata.getEventId());
        writer.u64(metadata.getSequence());
        writer.u8(metadata.getSourceValue());
        writer.optionalU64(metadata.hasSourceSequence(), metadata.getSourceSequence());
        writer.string(metadata.getSymbol());
        writer.string(metadata.getVenue());
        writer.optionalU64(metadata.hasTick(), metadata.getTick());
        writer.optionalI64(metadata.hasExchangeTimestampNs(), metadata.getExchangeTimestampNs());
        writer.optionalI64(metadata.hasReceivedTimestampNs(), metadata.getReceivedTimestampNs());
        writer.optionalString(metadata.hasScenarioId(), metadata.getScenarioId());
        writer.optionalString(metadata.hasScenarioName(), metadata.getScenarioName());
        writer.optionalString(metadata.hasScenarioFamily(), metadata.getScenarioFamily());
    }

    private static void writeRestingOrder(CanonicalWriter writer, AddOrder order) {
        writeRestingOrder(
                writer,
                order.getOrderId(),
                order.getAgentId(),
                order.getSideValue(),
                order.getPriceTicks(),
                order.getQuantityLots(),
                order.getOwner());
    }

    private static void writeRestingOrder(CanonicalWriter writer, CancelOrder order) {
        writeRestingOrder(
                writer,
                order.getOrderId(),
                order.getAgentId(),
                order.getSideValue(),
                order.getPriceTicks(),
                order.getQuantityLots(),
                order.getOwner());
    }

    private static void writeRestingOrder(
            CanonicalWriter writer,
            String orderId,
            String agentId,
            int side,
            long priceTicks,
            long quantityLots,
            String owner) {
        writer.string(orderId);
        writer.string(agentId);
        writer.u8(side);
        writer.i64(priceTicks);
        writer.i64(quantityLots);
        writer.string(owner);
    }

    private static void writeBookBody(CanonicalWriter writer, BookSnapshot book) {
        writer.u32(book.getBidsCount());
        for (PriceLevel level : book.getBidsList()) {
            writePriceLevel(writer, level);
        }
        writer.u32(book.getAsksCount());
        for (PriceLevel level : book.getAsksList()) {
            writePriceLevel(writer, level);
        }
        writer.optionalI64(book.hasBestBidTicks(), book.getBestBidTicks());
        writer.optionalI64(book.hasBestAskTicks(), book.getBestAskTicks());
        writer.optionalI64(book.hasMidPriceTicksX2(), book.getMidPriceTicksX2());
        writer.optionalI64(book.hasSpreadTicks(), book.getSpreadTicks());
    }

    private static void writePriceLevel(CanonicalWriter writer, PriceLevel level) {
        writer.i64(level.getPriceTicks());
        writer.i64(level.getQuantityLots());
        writer.optionalString(level.hasOwner(), level.getOwner());
    }

    private static byte[] sha256(byte[] bytes) {
        return sha256Digest().digest(bytes);
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 must be available", exception);
        }
    }
}
