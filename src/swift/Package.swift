// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "LearningEngine",
    products: [
        .library(name: "LearningEngine", targets: ["LearningEngine"])
    ],
    targets: [
        .target(name: "LearningEngine"),
        .testTarget(
            name: "LearningEngineTests",
            dependencies: ["LearningEngine"]
        )
    ]
)
