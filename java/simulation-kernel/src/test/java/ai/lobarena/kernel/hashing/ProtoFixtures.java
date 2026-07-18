package ai.lobarena.kernel.hashing;

import ai.lobarena.exchange.v1.AddOrder;
import ai.lobarena.exchange.v1.BookSnapshot;
import ai.lobarena.exchange.v1.CancelOrder;
import ai.lobarena.exchange.v1.EventMetadata;
import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.ExecuteOrder;
import ai.lobarena.exchange.v1.LobSnapshot;
import ai.lobarena.exchange.v1.ModifyOrder;
import ai.lobarena.exchange.v1.PriceLevel;
import ai.lobarena.exchange.v1.Side;
import java.util.List;

final class ProtoFixtures {
    private ProtoFixtures() {}

    static List<ExchangeEvent> allEventTypes() {
        return List.of(
                ExchangeEvent.newBuilder()
                        .setMetadata(metadata(1))
                        .setAdd(AddOrder.newBuilder()
                                .setOrderId("o1")
                                .setAgentId("maker")
                                .setSide(Side.SIDE_BUY)
                                .setPriceTicks(99)
                                .setQuantityLots(5)
                                .setOwner("normal"))
                        .build(),
                ExchangeEvent.newBuilder()
                        .setMetadata(metadata(2))
                        .setModify(ModifyOrder.newBuilder()
                                .setOrderId("o1")
                                .setAgentId("maker")
                                .setSide(Side.SIDE_BUY)
                                .setPreviousPriceTicks(99)
                                .setPreviousQuantityLots(5)
                                .setPriceTicks(100)
                                .setQuantityLots(4)
                                .setPriorityPreserved(false)
                                .setOwner("normal"))
                        .build(),
                ExchangeEvent.newBuilder()
                        .setMetadata(metadata(3))
                        .setCancel(CancelOrder.newBuilder()
                                .setOrderId("o1")
                                .setAgentId("maker")
                                .setSide(Side.SIDE_BUY)
                                .setPriceTicks(100)
                                .setQuantityLots(4)
                                .setOwner("normal"))
                        .build(),
                ExchangeEvent.newBuilder()
                        .setMetadata(metadata(4))
                        .setExecute(ExecuteOrder.newBuilder()
                                .setExecutionId("x1")
                                .setAggressorOrderId("buy-1")
                                .setRestingOrderId("sell-1")
                                .setAggressorAgentId("taker")
                                .setRestingAgentId("maker")
                                .setAggressorSide(Side.SIDE_BUY)
                                .setPriceTicks(101)
                                .setQuantityLots(2)
                                .setAggressorRemainingQuantityLots(0)
                                .setRestingRemainingQuantityLots(3))
                        .build(),
                ExchangeEvent.newBuilder()
                        .setMetadata(metadata(5))
                        .setSnapshot(LobSnapshot.newBuilder().setDepth(5).setBook(sampleBook()))
                        .build());
    }

    static BookSnapshot sampleBook() {
        return BookSnapshot.newBuilder()
                .addBids(PriceLevel.newBuilder().setPriceTicks(99).setQuantityLots(4).setOwner("normal"))
                .addAsks(PriceLevel.newBuilder().setPriceTicks(101).setQuantityLots(5).setOwner("abuser"))
                .setBestBidTicks(99)
                .setBestAskTicks(101)
                .setMidPriceTicksX2(200)
                .setSpreadTicks(2)
                .build();
    }

    private static EventMetadata metadata(long sequence) {
        return EventMetadata.newBuilder()
                .setSchemaVersion(1)
                .setEventId("SIM:event:" + sequence)
                .setSequence(sequence)
                .setSource(EventSource.EVENT_SOURCE_SIMULATION)
                .setSymbol("LOB")
                .setVenue("SIM")
                .setTick(7)
                .setScenarioId("scenario-1")
                .setScenarioName("spoofing_like_wall")
                .setScenarioFamily("spoofing_like_wall")
                .build();
    }
}
