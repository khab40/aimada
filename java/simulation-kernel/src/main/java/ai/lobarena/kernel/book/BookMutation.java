package ai.lobarena.kernel.book;

public record BookMutation(Type type, KernelOrder before, KernelOrder after, boolean priorityPreserved) {
    public enum Type {
        ADD,
        MODIFY,
        CANCEL
    }

    public static BookMutation add(KernelOrder order) {
        return new BookMutation(Type.ADD, null, order, false);
    }

    public static BookMutation modify(KernelOrder before, KernelOrder after, boolean priorityPreserved) {
        return new BookMutation(Type.MODIFY, before, after, priorityPreserved);
    }

    public static BookMutation cancel(KernelOrder order) {
        return new BookMutation(Type.CANCEL, order, null, false);
    }
}
