// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "StreamTV-tvOS",
    platforms: [
        .tvOS(.v15)
    ],
    products: [
        .library(
            name: "StreamTVClient",
            targets: ["StreamTVClient"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "StreamTVClient",
            dependencies: []
        )
    ]
)
