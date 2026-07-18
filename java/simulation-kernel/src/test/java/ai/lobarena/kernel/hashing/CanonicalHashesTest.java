package ai.lobarena.kernel.hashing;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import ai.lobarena.exchange.v1.ExchangeEvent;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import org.junit.jupiter.api.Test;

final class CanonicalHashesTest {
    @Test
    void eventBookAndStreamHashesMatchGoldenVectors() {
        List<ExchangeEvent> events = ProtoFixtures.allEventTypes();
        List<String> expectedEventHashes = List.of(
                "0e80c5c1d3962ccd91407dc33ef8725af306630df7a430d16f05e580e7e38a9f",
                "b5ada63f13d5f40ca6b0f7bc704a2b96eb8fade4858b0e03e19dd293dc088390",
                "7c44643ee57aa71372e92c14fa4f75d62849b7e6ac2a0faa427bfbb55abced27",
                "9033f62d69753a839b0e41f2e7e02cceaeb87c98a47f851e093dc884ac9e5ff2",
                "28318a0287b789e7e7ef700a7330eb9c0ec1ced9260d69cdd749edf614dd271d");
        List<String> expectedRollingHashes = List.of(
                "0d337121ba36fad6bb435d4f281a6d8061f39f65b86be3065a1db7d9f443d8dd",
                "54b81992828b61a6d6cb4baff98a051131c3c709b66757c3651f2e6709df3ed5",
                "bc3259274124a8e1f2472abfc7dc3f9745d70fdd1f2ad98dfa619f9e3762ef23",
                "6ad4b1ba954b3661142978327431940058fc24efb545c1627dc836347a237b47",
                "76e92472b803677185bd7e3e1922a8528c91ebca9ce5df95cf5575569cb67875");

        assertArrayEquals(
                HexFormat.of().parseHex("b3b8fbf44d4621f6e7c374fe9f0d806f1bf54e543a679988d76da820be37426d"),
                CanonicalHashes.initialStreamHash(1));
        byte[] rollingHash = CanonicalHashes.initialStreamHash(1);
        for (int index = 0; index < events.size(); index++) {
            byte[] itemHash = CanonicalHashes.eventHash(events.get(index));
            assertArrayEquals(
                    HexFormat.of().parseHex(expectedEventHashes.get(index)),
                    itemHash);
            rollingHash = CanonicalHashes.advanceStreamHash(rollingHash, itemHash);
            assertArrayEquals(HexFormat.of().parseHex(expectedRollingHashes.get(index)), rollingHash);
        }
        assertArrayEquals(
                HexFormat.of().parseHex("76e92472b803677185bd7e3e1922a8528c91ebca9ce5df95cf5575569cb67875"),
                CanonicalHashes.eventStreamHash(events, 1));
        assertArrayEquals(
                HexFormat.of().parseHex("86739da89ebd7770f910207126c2b063e93ccaf981febcdec1c329084f6d0943"),
                CanonicalHashes.bookHash(ProtoFixtures.sampleBook()));
        assertArrayEquals(
                HexFormat.of().parseHex(
                        "4c4f422d4556454e542d563100000000010000000b53494d3a6576656e743a3100000000000000010100000000034c4f420000000353494d0100000000000000070000010000000a7363656e6172696f2d31010000001273706f6f66696e675f6c696b655f77616c6c010000001273706f6f66696e675f6c696b655f77616c6c01000000026f31000000056d616b65720100000000000000630000000000000005000000066e6f726d616c"),
                CanonicalHashes.canonicalEventBytes(events.getFirst()));
    }

    @Test
    void presencePayloadAndWireEncodingRemainDistinct() {
        ExchangeEvent baseline = ProtoFixtures.allEventTypes().getFirst();
        ExchangeEvent absentTick = baseline.toBuilder()
                .setMetadata(baseline.getMetadata().toBuilder().clearTick())
                .build();
        ExchangeEvent changedQuantity = baseline.toBuilder()
                .setAdd(baseline.getAdd().toBuilder().setQuantityLots(6))
                .build();

        assertFalse(java.util.Arrays.equals(CanonicalHashes.eventHash(absentTick), CanonicalHashes.eventHash(baseline)));
        assertFalse(
                java.util.Arrays.equals(CanonicalHashes.eventHash(changedQuantity), CanonicalHashes.eventHash(baseline)));
        assertNotEquals(
                HexFormat.of().formatHex(baseline.toByteArray()),
                HexFormat.of().formatHex(CanonicalHashes.canonicalEventBytes(baseline)));
    }

    @Test
    void invalidSequenceVersionAndUnicodeAreRejected() {
        List<ExchangeEvent> badSequence = new ArrayList<>(ProtoFixtures.allEventTypes());
        badSequence.set(1, badSequence.get(1).toBuilder()
                .setMetadata(badSequence.get(1).getMetadata().toBuilder().setSequence(3))
                .build());
        List<ExchangeEvent> badVersion = new ArrayList<>(ProtoFixtures.allEventTypes());
        badVersion.set(0, badVersion.getFirst().toBuilder()
                .setMetadata(badVersion.getFirst().getMetadata().toBuilder().setSchemaVersion(2))
                .build());
        ExchangeEvent badUnicode = ProtoFixtures.allEventTypes().getFirst().toBuilder()
                .setMetadata(ProtoFixtures.allEventTypes().getFirst().getMetadata().toBuilder().setScenarioName("e\u0301"))
                .build();

        assertThrows(IllegalArgumentException.class, () -> CanonicalHashes.eventStreamHash(badSequence, 1));
        assertThrows(IllegalArgumentException.class, () -> CanonicalHashes.eventStreamHash(badVersion, 1));
        assertThrows(IllegalArgumentException.class, () -> CanonicalHashes.canonicalEventBytes(badUnicode));
    }
}
