package ai.lobarena.kernel.book;

import ai.lobarena.exchange.v1.Side;

public record Execution(
        String aggressorOrderId,
        String restingOrderId,
        String aggressorAgentId,
        String restingAgentId,
        Side aggressorSide,
        long priceTicks,
        long quantityLots,
        long aggressorRemainingQuantityLots,
        long restingRemainingQuantityLots,
        long timestamp,
        String scenarioId,
        String scenarioName,
        String scenarioFamily) {}
