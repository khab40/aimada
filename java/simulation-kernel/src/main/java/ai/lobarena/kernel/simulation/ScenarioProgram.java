package ai.lobarena.kernel.simulation;

import ai.lobarena.exchange.v1.Side;
import ai.lobarena.kernel.book.IntegerOrderBook;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;

final class ScenarioProgram {
    private enum Stage {
        ARMED(0),
        WALL_PLACED(1),
        PRESSURE_PHASE(3),
        WALL_CANCELLED(6),
        INCIDENT_CONFIRMED(7),
        DONE(9);

        private final int atTick;

        Stage(int atTick) {
            this.atTick = atTick;
        }
    }

    private final String scenarioName;
    private final String scenarioId;
    private final String agentId;
    private final long startTick;
    private final long seed;
    private final long priceUnitNanos;
    private final long quantityUnitNanos;
    private final EnumSet<Stage> appliedStages = EnumSet.noneOf(Stage.class);
    private final List<Long> layerPrices = new ArrayList<>();
    private final List<String> layerOrderIds = new ArrayList<>();
    private long eventCounter;
    private Long wallPrice;
    private Stage currentStage = Stage.ARMED;

    ScenarioProgram(String scenarioName, long seed, long priceUnitNanos, long quantityUnitNanos) {
        this.scenarioName = scenarioName;
        this.seed = seed;
        this.priceUnitNanos = priceUnitNanos;
        this.quantityUnitNanos = quantityUnitNanos;
        this.startTick = 1;
        this.scenarioId = scenarioName + "-0001";
        this.agentId = switch (scenarioName) {
            case "spoofing_like_wall" -> "ABUSER_01";
            case "layering_like" -> "ABUSER_02";
            case "quote_stuffing" -> "ABUSER_03";
            case "liquidity_evaporation" -> "SHOCK_01";
            default -> throw new IllegalArgumentException("unknown scenario: " + scenarioName);
        };
        for (int index = 0; index < 3; index++) {
            layerOrderIds.add(scenarioId + "-layer-" + index);
        }
    }

    List<Activity> advance(IntegerOrderBook book, long tick) {
        currentStage = stageForTick(tick);
        List<Activity> activities = new ArrayList<>();
        if (appliedStages.add(currentStage)) {
            activities.addAll(onStageEnter(book, tick, currentStage));
        }
        activities.addAll(onTick(book, tick));
        return List.copyOf(activities);
    }

    String scenarioId() {
        return scenarioId;
    }

    String scenarioName() {
        return scenarioName;
    }

    String scenarioFamily() {
        return scenarioName;
    }

    private Stage stageForTick(long tick) {
        long elapsed = Math.max(0, tick - startTick);
        Stage stage = Stage.ARMED;
        for (Stage candidate : Stage.values()) {
            if (elapsed >= candidate.atTick) {
                stage = candidate;
            }
        }
        return stage;
    }

    private List<Activity> onStageEnter(IntegerOrderBook book, long tick, Stage stage) {
        return switch (scenarioName) {
            case "spoofing_like_wall" -> spoofingStage(book, tick, stage);
            case "layering_like" -> layeringStage(book, tick, stage);
            case "quote_stuffing" -> quoteStuffingStage(tick, stage);
            case "liquidity_evaporation" -> liquidityStage(book, tick, stage);
            default -> throw new IllegalStateException("unsupported scenario");
        };
    }

    private List<Activity> onTick(IntegerOrderBook book, long tick) {
        if (scenarioName.equals("quote_stuffing") && currentStage == Stage.PRESSURE_PHASE) {
            Long bestAsk = book.bestAsk();
            if (bestAsk != null) {
                for (int index = 0; index < 3; index++) {
                    long price = bestAsk + priceOffset(5 + index);
                    book.updateLevel(Side.SIDE_SELL, price, lots(new BigDecimal("0.5").add(
                            BigDecimal.valueOf(index).multiply(new BigDecimal("0.1")))), "abuser");
                    book.removeLevel(Side.SIDE_SELL, price);
                }
            }
            List<Activity> activities = new ArrayList<>();
            for (int index = 0; index < 8; index++) {
                activities.add(event(tick, "rapid place/cancel quote update", Stage.PRESSURE_PHASE, null, null));
            }
            return activities;
        }
        if (scenarioName.equals("liquidity_evaporation") && currentStage == Stage.PRESSURE_PHASE) {
            thinTop(book);
            return List.of(event(tick, "liquidity remains thin", Stage.PRESSURE_PHASE, null, null));
        }
        return List.of();
    }

    private List<Activity> spoofingStage(IntegerOrderBook book, long tick, Stage stage) {
        if (stage == Stage.WALL_PLACED) {
            if (book.bestAsk() == null) {
                return List.of();
            }
            wallPrice = book.bestAsk() + priceOffset(2);
            String orderId = scenarioId + "-wall";
            updateScenarioLevel(book, Side.SIDE_SELL, wallPrice, lots("48"), orderId, tick);
            return List.of(event(tick, "large ask wall placed away from mid", stage, orderId, Side.SIDE_SELL));
        }
        if (stage == Stage.PRESSURE_PHASE) {
            String orderId = scenarioId + "-wall";
            if (wallPrice != null) {
                updateScenarioLevel(book, Side.SIDE_SELL, wallPrice, lots("52"), orderId, tick);
            }
            return List.of(event(tick, "visible wall replenishment maintained", stage, orderId, Side.SIDE_SELL));
        }
        if (stage == Stage.WALL_CANCELLED) {
            String orderId = scenarioId + "-wall";
            book.cancel(orderId);
            return List.of(event(tick, "ask wall cancelled before execution", stage, orderId, Side.SIDE_SELL));
        }
        if (stage == Stage.INCIDENT_CONFIRMED) {
            return List.of(event(tick, "spoofing-like wall incident confirmed", stage, null, null));
        }
        return List.of(event(tick, scenarioName + " entered " + stageName(stage), stage, null, null));
    }

    private List<Activity> layeringStage(IntegerOrderBook book, long tick, Stage stage) {
        Side side = (seed & 1L) == 0 ? Side.SIDE_SELL : Side.SIDE_BUY;
        if (stage == Stage.WALL_PLACED) {
            Long touch = side == Side.SIDE_SELL ? book.bestAsk() : book.bestBid();
            if (touch == null) {
                return List.of();
            }
            layerPrices.clear();
            for (int index = 0; index < 3; index++) {
                long offset = priceOffset(2 + index);
                long price = side == Side.SIDE_SELL ? touch + offset : touch - offset;
                layerPrices.add(price);
                updateScenarioLevel(book, side, price, lots(Long.toString(22 + index * 4L)), layerOrderIds.get(index), tick);
            }
            return layerActivities(tick, "same-side " + bookSide(side) + " layer placed", stage, side);
        }
        if (stage == Stage.PRESSURE_PHASE) {
            for (int index = 0; index < layerPrices.size(); index++) {
                updateScenarioLevel(
                        book, side, layerPrices.get(index), lots(Long.toString(26 + index * 4L)),
                        layerOrderIds.get(index), tick);
            }
            return layerActivities(tick, "layered " + bookSide(side) + " replenishment maintained", stage, side);
        }
        if (stage == Stage.WALL_CANCELLED) {
            layerOrderIds.forEach(book::cancel);
            return layerActivities(tick, "layered " + bookSide(side) + " liquidity cancelled", stage, side);
        }
        if (stage == Stage.INCIDENT_CONFIRMED) {
            return List.of(event(tick, "layering-like pattern incident confirmed", stage, null, null));
        }
        return List.of(event(tick, scenarioName + " entered " + stageName(stage), stage, null, null));
    }

    private List<Activity> quoteStuffingStage(long tick, Stage stage) {
        String message = switch (stage) {
            case WALL_PLACED -> "quote stuffing burst armed";
            case PRESSURE_PHASE -> "high message-rate quote burst active";
            case WALL_CANCELLED -> "quote stuffing burst stopped";
            case INCIDENT_CONFIRMED -> "quote stuffing incident confirmed";
            default -> scenarioName + " entered " + stageName(stage);
        };
        return List.of(event(tick, message, stage, null, null));
    }

    private List<Activity> liquidityStage(IntegerOrderBook book, long tick, Stage stage) {
        String message;
        if (stage == Stage.WALL_PLACED) {
            message = "liquidity shock armed";
        } else if (stage == Stage.PRESSURE_PHASE) {
            thinTop(book);
            message = "top-of-book depth collapsed";
        } else if (stage == Stage.WALL_CANCELLED) {
            Long bid = book.bestBid();
            Long ask = book.bestAsk();
            if (bid != null) {
                book.removeLevel(Side.SIDE_BUY, bid);
            }
            if (ask != null) {
                book.removeLevel(Side.SIDE_SELL, ask);
            }
            message = "spread widened after depth collapse";
        } else if (stage == Stage.INCIDENT_CONFIRMED) {
            message = "liquidity evaporation incident confirmed";
        } else {
            message = scenarioName + " entered " + stageName(stage);
        }
        return List.of(event(tick, message, stage, null, null));
    }

    private void thinTop(IntegerOrderBook book) {
        for (Side side : List.of(Side.SIDE_BUY, Side.SIDE_SELL)) {
            for (long price : book.prices(side, 3)) {
                double current = book.levelQuantityAsReferenceDouble(side, price);
                book.updateLevel(side, price, lots(thinQuantity(current)), "normal");
            }
        }
    }

    static BigDecimal thinQuantity(double current) {
        BigDecimal target = new BigDecimal(current * 0.35).setScale(3, RoundingMode.HALF_EVEN);
        return target.max(new BigDecimal("0.2"));
    }

    private void updateScenarioLevel(
            IntegerOrderBook book, Side side, long price, long quantity, String orderId, long tick) {
        book.updateAgentLevel(
                side, price, quantity, agentId, "abuser", orderId, tick,
                scenarioId, scenarioName, scenarioName);
    }

    private List<Activity> layerActivities(long tick, String message, Stage stage, Side side) {
        List<Activity> activities = new ArrayList<>();
        for (String orderId : layerOrderIds) {
            activities.add(event(tick, message, stage, orderId, side));
        }
        return activities;
    }

    private Activity event(long tick, String message, Stage stage, String orderId, Side side) {
        eventCounter++;
        return new Activity(
                "red_team",
                scenarioId + "-event-%04d".formatted(eventCounter),
                orderId,
                agentId,
                side,
                stageName(stage),
                message);
    }

    private long priceOffset(long wholeUnits) {
        return ai.lobarena.kernel.determinism.DeterministicValues.decimalToUnits(
                Long.toString(wholeUnits), priceUnitNanos);
    }

    private long lots(String value) {
        return ai.lobarena.kernel.determinism.DeterministicValues.decimalToUnits(value, quantityUnitNanos);
    }

    private long lots(BigDecimal value) {
        return lots(value.stripTrailingZeros().toPlainString());
    }

    private static String stageName(Stage stage) {
        return stage.name().toLowerCase();
    }

    private static String bookSide(Side side) {
        return side == Side.SIDE_BUY ? "bid" : "ask";
    }
}
