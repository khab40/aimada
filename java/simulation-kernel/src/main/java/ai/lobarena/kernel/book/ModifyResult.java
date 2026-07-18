package ai.lobarena.kernel.book;

public record ModifyResult(KernelOrder before, KernelOrder after, boolean priorityPreserved) {}
