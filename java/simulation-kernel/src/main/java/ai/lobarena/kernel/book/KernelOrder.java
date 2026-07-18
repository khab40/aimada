package ai.lobarena.kernel.book;

import ai.lobarena.exchange.v1.Side;

public record KernelOrder(
        String orderId,
        String agentId,
        Side side,
        long quantityLots,
        Long priceTicks,
        OrderType orderType,
        long timestamp,
        String scenarioId,
        String scenarioName,
        String scenarioFamily,
        String owner) {
    public KernelOrder {
        requireText("orderId", orderId);
        requireText("agentId", agentId);
        requireText("owner", owner);
        if (side != Side.SIDE_BUY && side != Side.SIDE_SELL) {
            throw new IllegalArgumentException("side must be buy or sell");
        }
        if (quantityLots < 0) {
            throw new IllegalArgumentException("quantityLots must be non-negative");
        }
        if (timestamp < 0) {
            throw new IllegalArgumentException("timestamp must be non-negative");
        }
        if (orderType == null) {
            throw new IllegalArgumentException("orderType must not be null");
        }
        if (orderType == OrderType.LIMIT && (priceTicks == null || priceTicks <= 0 || quantityLots <= 0)) {
            throw new IllegalArgumentException("limit order requires positive price and quantity");
        }
        if (orderType == OrderType.MARKET && quantityLots <= 0) {
            throw new IllegalArgumentException("market order requires positive quantity");
        }
        if (orderType == OrderType.MODIFY && quantityLots <= 0) {
            throw new IllegalArgumentException("modify order quantity must be positive; use cancel to remove an order");
        }
        if (priceTicks != null && priceTicks <= 0) {
            throw new IllegalArgumentException("priceTicks must be positive when present");
        }
    }

    public static KernelOrder limit(
            String orderId, String agentId, Side side, long quantityLots, long priceTicks, long timestamp) {
        return new KernelOrder(
                orderId, agentId, side, quantityLots, priceTicks, OrderType.LIMIT, timestamp,
                null, null, null, "normal");
    }

    public static KernelOrder market(
            String orderId, String agentId, Side side, long quantityLots, long timestamp) {
        return new KernelOrder(
                orderId, agentId, side, quantityLots, null, OrderType.MARKET, timestamp,
                null, null, null, "normal");
    }

    public static KernelOrder modify(
            String orderId, String agentId, Side side, long quantityLots, Long priceTicks, long timestamp) {
        return new KernelOrder(
                orderId, agentId, side, quantityLots, priceTicks, OrderType.MODIFY, timestamp,
                null, null, null, "normal");
    }

    public static KernelOrder cancel(String orderId, String agentId, Side side, long timestamp) {
        return new KernelOrder(
                orderId, agentId, side, 0, null, OrderType.CANCEL, timestamp,
                null, null, null, "normal");
    }

    public KernelOrder withQuantity(long newQuantityLots) {
        return new KernelOrder(
                orderId, agentId, side, newQuantityLots, priceTicks, orderType, timestamp,
                scenarioId, scenarioName, scenarioFamily, owner);
    }

    KernelOrder asResting(long newQuantityLots, long newPriceTicks, long newTimestamp) {
        return new KernelOrder(
                orderId, agentId, side, newQuantityLots, newPriceTicks, OrderType.LIMIT, newTimestamp,
                scenarioId, scenarioName, scenarioFamily, owner);
    }

    private static void requireText(String name, String value) {
        if (value == null || value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
    }
}
