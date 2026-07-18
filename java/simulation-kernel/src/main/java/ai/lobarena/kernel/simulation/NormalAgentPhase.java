package ai.lobarena.kernel.simulation;

import ai.lobarena.exchange.v1.BookSnapshot;
import ai.lobarena.exchange.v1.PriceLevel;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.kernel.determinism.DeterministicValues;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

final class NormalAgentPhase {
    private final int agentCount;
    private final long quantityUnitNanos;

    NormalAgentPhase(int agentCount, long quantityUnitNanos) {
        this.agentCount = agentCount;
        this.quantityUnitNanos = quantityUnitNanos;
    }

    List<AgentIntent> decide(long tick, BookSnapshot book) {
        List<AgentIntent> intents = new ArrayList<>();
        if (agentCount >= 1) {
            marketMaker(tick, book, "MM_01", intents);
        }
        if (agentCount >= 2) {
            noiseTrader(tick, book, "NOISE_01", 0, 1, intents);
        }
        if (agentCount >= 3) {
            liquidityTaker(tick, "TAKER_01", 0, 4, "0.5", intents);
        }
        for (int index = 4; index <= agentCount; index++) {
            if (index % 8 == 0) {
                String quantity = BigDecimal.valueOf(0.05 + (index % 4) * 0.025)
                        .setScale(3, java.math.RoundingMode.HALF_EVEN)
                        .stripTrailingZeros()
                        .toPlainString();
                liquidityTaker(tick, "TAKER_%03d".formatted(index), index, 8 + index % 5, quantity, intents);
            } else {
                noiseTrader(tick, book, "NOISE_%03d".formatted(index), index, 2 + index % 6, intents);
            }
        }
        Collections.sort(intents);
        return List.copyOf(intents);
    }

    private void marketMaker(long tick, BookSnapshot book, String agentId, List<AgentIntent> intents) {
        if (!book.hasBestBidTicks() || !book.hasBestAskTicks()) {
            return;
        }
        BigDecimal bid = BigDecimal.valueOf(2).add(BigDecimal.valueOf(tick % 5).multiply(new BigDecimal("0.25")));
        BigDecimal ask = new BigDecimal("2.1")
                .add(BigDecimal.valueOf((tick + 2) % 5).multiply(new BigDecimal("0.25")));
        intents.add(new AgentIntent(
                tick, agentId, AgentIntent.Kind.SET_LEVEL, 0, 0, "market_maker", Side.SIDE_BUY,
                book.getBestBidTicks(), lots(bid), "refreshed best bid depth"));
        intents.add(new AgentIntent(
                tick, agentId, AgentIntent.Kind.SET_LEVEL, 1, 0, "market_maker", Side.SIDE_SELL,
                book.getBestAskTicks(), lots(ask), "refreshed best ask depth"));
    }

    private void noiseTrader(
            long tick,
            BookSnapshot book,
            String agentId,
            int offset,
            int cadence,
            List<AgentIntent> intents) {
        if ((tick + offset) % cadence != 0) {
            return;
        }
        Side side = (tick + offset) % 2 != 0 ? Side.SIDE_BUY : Side.SIDE_SELL;
        List<PriceLevel> levels = side == Side.SIDE_BUY ? book.getBidsList() : book.getAsksList();
        if (levels.isEmpty()) {
            return;
        }
        int levelIndex = Math.min((int) ((tick + offset + 2) % 5), levels.size() - 1);
        BigDecimal quantity = new BigDecimal("0.35")
                .add(BigDecimal.valueOf((tick + offset) % 5).multiply(new BigDecimal("0.075")));
        intents.add(new AgentIntent(
                tick, agentId, AgentIntent.Kind.SET_LEVEL, 0, offset % 5, "normal", side,
                levels.get(levelIndex).getPriceTicks(), lots(quantity), "small visible depth changed"));
    }

    private void liquidityTaker(
            long tick,
            String agentId,
            int offset,
            int cadence,
            String quantity,
            List<AgentIntent> intents) {
        if ((tick + offset) % cadence != 0) {
            return;
        }
        Side side = ((tick + offset) / cadence) % 2 != 0 ? Side.SIDE_BUY : Side.SIDE_SELL;
        intents.add(new AgentIntent(
                tick, agentId, AgentIntent.Kind.MARKET, 0, offset % 7, "normal", side,
                null, lots(new BigDecimal(quantity)), "consumed small top-of-book quantity"));
    }

    private long lots(BigDecimal quantity) {
        return DeterministicValues.decimalToUnits(quantity.stripTrailingZeros().toPlainString(), quantityUnitNanos);
    }
}
