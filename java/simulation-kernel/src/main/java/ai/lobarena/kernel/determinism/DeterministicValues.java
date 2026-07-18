package ai.lobarena.kernel.determinism;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

public final class DeterministicValues {
    private static final BigDecimal NANOS_PER_UNIT = BigDecimal.valueOf(1_000_000_000L);
    private static final byte[] STREAM_SEED_DOMAIN = "lob-arena-prng-v1\0".getBytes(StandardCharsets.US_ASCII);

    private DeterministicValues() {}

    public static long deriveStreamSeed(long rootSeedBits, String streamName) {
        requireAscii("streamName", streamName, false);
        MessageDigest digest = sha256();
        digest.update(STREAM_SEED_DOMAIN);
        digest.update(ByteBuffer.allocate(Long.BYTES).putLong(rootSeedBits).array());
        digest.update(streamName.getBytes(StandardCharsets.US_ASCII));
        return ByteBuffer.wrap(digest.digest(), 0, Long.BYTES).getLong();
    }

    public static long decimalToUnits(String value, long unitSizeNanos) {
        if (unitSizeNanos <= 0) {
            throw new IllegalArgumentException("unitSizeNanos must be positive");
        }
        try {
            return new BigDecimal(value)
                    .multiply(NANOS_PER_UNIT)
                    .divide(BigDecimal.valueOf(unitSizeNanos), 0, RoundingMode.UNNECESSARY)
                    .longValueExact();
        } catch (ArithmeticException exception) {
            throw new IllegalArgumentException(
                    value + " is not an exact int64 multiple of unit size " + unitSizeNanos + " nanos",
                    exception);
        }
    }

    public static long quantizeMetric(String value, int decimalScale) {
        if (decimalScale < 0 || decimalScale > 18) {
            throw new IllegalArgumentException("decimalScale must be in the range 0..18");
        }
        try {
            return new BigDecimal(value)
                    .movePointRight(decimalScale)
                    .setScale(0, RoundingMode.HALF_EVEN)
                    .longValueExact();
        } catch (ArithmeticException exception) {
            throw new IllegalArgumentException("quantized metric does not fit signed int64", exception);
        }
    }

    public static long midpointTicksX2(long bestBidTicks, long bestAskTicks) {
        return Math.addExact(bestBidTicks, bestAskTicks);
    }

    public static String simulationEventId(String venue, String eventType, long sequence) {
        if (sequence <= 0) {
            throw new IllegalArgumentException("sequence must start at 1");
        }
        requireAscii("venue", venue, true);
        requireAscii("eventType", eventType, true);
        return venue + ":" + eventType.toLowerCase(Locale.ROOT) + ":" + sequence;
    }

    static void requireAscii(String fieldName, String value, boolean rejectColon) {
        if (value == null || value.isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be empty");
        }
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (character > 0x7f) {
                throw new IllegalArgumentException(fieldName + " must contain ASCII characters only");
            }
            if (rejectColon && character == ':') {
                throw new IllegalArgumentException(fieldName + " must not contain ':'");
            }
        }
    }

    static BigInteger unsignedLongToBigInteger(long value) {
        byte[] bytes = ByteBuffer.allocate(Long.BYTES).putLong(value).array();
        return new BigInteger(1, bytes);
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 must be available", exception);
        }
    }
}
