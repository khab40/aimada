package ai.lobarena.kernel.book;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.kernel.hashing.CanonicalHashes;
import java.util.List;
import org.junit.jupiter.api.Test;

final class IntegerMatchingEngineTest {
    @Test
    void limitMatchEmitsExecutionThenRestsExactRemainder() {
        IntegerMatchingEngine engine = engine();
        engine.submit(KernelOrder.limit("ask", "maker", Side.SIDE_SELL, 600, 100, 1));

        List<ExchangeEvent> events = engine.submit(
                KernelOrder.limit("buy", "taker", Side.SIDE_BUY, 1_000, 101, 2));

        assertEquals(List.of("execute", "add"), events.stream().map(this::payload).toList());
        assertEquals(600, events.get(0).getExecute().getQuantityLots());
        assertEquals(400, events.get(1).getAdd().getQuantityLots());
        assertEquals(List.of(2L, 3L), events.stream().map(event -> event.getMetadata().getSequence()).toList());
        assertEquals("SIM:execute:2", events.get(0).getMetadata().getEventId());
        assertEquals(400, engine.book().snapshot(5).getBids(0).getQuantityLots());
    }

    @Test
    void cancelAndModifyEventsUseActualRestingState() {
        IntegerMatchingEngine engine = engine();
        engine.submit(KernelOrder.limit("bid", "maker", Side.SIDE_BUY, 2_500, 99, 1));

        ExchangeEvent modify = engine.submit(
                KernelOrder.modify("bid", "maker", Side.SIDE_BUY, 4_000, 99L, 3)).getFirst();
        ExchangeEvent cancel = engine.submit(
                KernelOrder.cancel("bid", "requester", Side.SIDE_SELL, 4)).getFirst();

        assertEquals(2_500, modify.getModify().getPreviousQuantityLots());
        assertEquals(4_000, modify.getModify().getQuantityLots());
        assertTrue(modify.getModify().getPriorityPreserved());
        assertEquals("maker", cancel.getCancel().getAgentId());
        assertEquals(Side.SIDE_BUY, cancel.getCancel().getSide());
        assertEquals(4_000, cancel.getCancel().getQuantityLots());
        assertEquals(4, cancel.getMetadata().getTick());
        assertEquals(0, engine.book().snapshot(5).getBidsCount());
    }

    @Test
    void allPayloadsAndSnapshotProduceContiguousCanonicallyHashableStream() {
        IntegerMatchingEngine engine = engine();
        engine.submit(KernelOrder.limit("bid", "maker", Side.SIDE_BUY, 5, 99, 1));
        engine.submit(KernelOrder.modify("bid", "maker", Side.SIDE_BUY, 6, 99L, 2));
        engine.submit(KernelOrder.cancel("bid", "requester", Side.SIDE_SELL, 3));
        engine.submit(KernelOrder.limit("ask", "maker", Side.SIDE_SELL, 2, 101, 4));
        engine.submit(KernelOrder.market("buy", "taker", Side.SIDE_BUY, 2, 5));
        ExchangeEvent snapshot = engine.recordSnapshot(5, 3, null, null, "scenario-1", "test", "test");

        assertEquals(
                List.of("add", "modify", "cancel", "add", "execute", "snapshot"),
                engine.events().stream().map(this::payload).toList());
        assertEquals(3, snapshot.getSnapshot().getDepth());
        assertEquals(
                List.of(1L, 2L, 3L, 4L, 5L, 6L),
                engine.events().stream().map(event -> event.getMetadata().getSequence()).toList());
        assertEquals(32, CanonicalHashes.eventStreamHash(engine.events(), 1).length);
    }

    @Test
    void initializationAfterListenerProducesDeterministicBaselineAdds() {
        IntegerMatchingEngine engine = engine();

        engine.book().initialize(100, 2, 1, 1_500, "normal");
        ExchangeEvent snapshot = engine.recordSnapshot(7, 1, null, null, null, null, null);

        assertEquals(List.of("add", "add", "add", "add", "snapshot"),
                engine.events().stream().map(this::payload).toList());
        assertEquals(5, snapshot.getMetadata().getSequence());
        assertEquals(1, snapshot.getSnapshot().getBook().getBidsCount());
        assertEquals(1, snapshot.getSnapshot().getBook().getAsksCount());
    }

    @Test
    void unknownCancelModifyAndUnfilledMarketEmitNothing() {
        IntegerMatchingEngine engine = engine();

        assertTrue(engine.submit(KernelOrder.cancel("missing", "maker", Side.SIDE_BUY, 0)).isEmpty());
        assertTrue(engine.submit(KernelOrder.modify("missing", "maker", Side.SIDE_BUY, 1, 99L, 0)).isEmpty());
        assertTrue(engine.submit(KernelOrder.market("empty", "taker", Side.SIDE_BUY, 5, 0)).isEmpty());
        assertTrue(engine.events().isEmpty());
    }

    private IntegerMatchingEngine engine() {
        return new IntegerMatchingEngine(
                new IntegerOrderBook(1_000_000_000, 1_000_000),
                "LOB",
                "SIM",
                EventSource.EVENT_SOURCE_SIMULATION);
    }

    private String payload(ExchangeEvent event) {
        return event.getPayloadCase().name().toLowerCase();
    }
}
