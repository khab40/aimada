package ai.lobarena.kernel.determinism;

import java.math.BigInteger;

public final class SplitMix64 {
    private static final long GAMMA = 0x9E3779B97F4A7C15L;
    private static final long MIX_1 = 0xBF58476D1CE4E5B9L;
    private static final long MIX_2 = 0x94D049BB133111EBL;
    private static final BigInteger UINT64_RANGE = BigInteger.ONE.shiftLeft(64);
    private static final BigInteger MAX_BOUND = BigInteger.ONE.shiftLeft(63);

    private long state;

    public SplitMix64(long seedBits) {
        state = seedBits;
    }

    /** Returns the next unsigned 64-bit value in a Java long bit pattern. */
    public long nextUnsignedLong() {
        state += GAMMA;
        long value = state;
        value = (value ^ (value >>> 30)) * MIX_1;
        value = (value ^ (value >>> 27)) * MIX_2;
        return value ^ (value >>> 31);
    }

    public long nextInt(long bound) {
        if (bound <= 0) {
            throw new IllegalArgumentException("bound must be positive");
        }
        return nextInt(BigInteger.valueOf(bound));
    }

    /** Supports the complete frozen bound range 1..2^63 using rejection sampling. */
    public long nextInt(BigInteger bound) {
        if (bound.signum() <= 0 || bound.compareTo(MAX_BOUND) > 0) {
            throw new IllegalArgumentException("bound must be in the range 1..2^63");
        }
        BigInteger rejectionLimit = UINT64_RANGE.subtract(UINT64_RANGE.mod(bound));
        while (true) {
            BigInteger candidate = DeterministicValues.unsignedLongToBigInteger(nextUnsignedLong());
            if (candidate.compareTo(rejectionLimit) < 0) {
                return candidate.mod(bound).longValueExact();
            }
        }
    }
}
