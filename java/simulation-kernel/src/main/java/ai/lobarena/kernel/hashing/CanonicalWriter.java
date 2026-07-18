package ai.lobarena.kernel.hashing;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;

final class CanonicalWriter {
    private final ByteArrayOutputStream output = new ByteArrayOutputStream();

    void raw(byte[] value) {
        output.writeBytes(value);
    }

    void bool(boolean value) {
        output.write(value ? 1 : 0);
    }

    void u8(int value) {
        if (value < 0 || value > 0xff) {
            throw new IllegalArgumentException("value does not fit uint8");
        }
        output.write(value);
    }

    void u32(long value) {
        if (value < 0 || value > 0xffff_ffffL) {
            throw new IllegalArgumentException("value does not fit uint32");
        }
        output.write((int) (value >>> 24));
        output.write((int) (value >>> 16));
        output.write((int) (value >>> 8));
        output.write((int) value);
    }

    void u64(long valueBits) {
        i64(valueBits);
    }

    void i64(long value) {
        output.write((int) (value >>> 56));
        output.write((int) (value >>> 48));
        output.write((int) (value >>> 40));
        output.write((int) (value >>> 32));
        output.write((int) (value >>> 24));
        output.write((int) (value >>> 16));
        output.write((int) (value >>> 8));
        output.write((int) value);
    }

    void string(String value) {
        if (!Normalizer.isNormalized(value, Normalizer.Form.NFC)) {
            throw new IllegalArgumentException("canonical strings must already be Unicode NFC");
        }
        byte[] encoded = value.getBytes(StandardCharsets.UTF_8);
        u32(encoded.length);
        raw(encoded);
    }

    void optionalU64(boolean present, long value) {
        bool(present);
        if (present) {
            u64(value);
        }
    }

    void optionalI64(boolean present, long value) {
        bool(present);
        if (present) {
            i64(value);
        }
    }

    void optionalString(boolean present, String value) {
        bool(present);
        if (present) {
            string(value);
        }
    }

    byte[] bytes() {
        return output.toByteArray();
    }
}
