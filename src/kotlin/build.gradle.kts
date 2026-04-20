plugins {
    kotlin("jvm") version "1.9.24"
}

repositories {
    mavenCentral()
}

dependencies {
    implementation(kotlin("stdlib"))
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")
    testImplementation(kotlin("test"))
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        kotlin.srcDir(".")
        kotlin.exclude("QuizEngineTest.kt")
    }
    test {
        kotlin.srcDir(".")
        kotlin.include("QuizEngineTest.kt")
    }
}
