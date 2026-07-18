package ai.lobarena.kernel.simulation;

import ai.lobarena.exchange.v1.Side;

record Activity(
        String type,
        String eventId,
        String orderId,
        String agentId,
        Side side,
        String stage,
        String message) {}
