plugins {
    `java-library`
    id("com.google.protobuf")
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

sourceSets {
    main {
        proto {
            srcDir("../../contracts/proto")
        }
    }
    test {
        resources {
            srcDir("../../contracts/golden")
        }
    }
}

dependencies {
    api("com.google.protobuf:protobuf-java:4.33.2")
    testImplementation(platform("org.junit:junit-bom:6.0.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:4.33.2"
    }
}
