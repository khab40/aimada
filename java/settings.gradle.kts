pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "lob-arena-java"

include("exchange-proto")
include("simulation-kernel")
include("kernel-grpc")
include("control-plane")
