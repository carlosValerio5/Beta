// swift-tools-version: 6.0
// BetaKit: everything in the iOS app that doesn't need UIKit — wire models, API client, polling,
// hold selection, chapter timeline and the climb-session view model. Testable with `swift test`
// on macOS (Command Line Tools are enough; no Xcode required).
import PackageDescription

let package = Package(
    name: "BetaKit",
    platforms: [.iOS(.v18), .macOS(.v15)],
    products: [
        .library(name: "BetaKit", targets: ["BetaKit"]),
    ],
    targets: [
        .target(name: "BetaKit"),
        .testTarget(name: "BetaKitTests", dependencies: ["BetaKit"]),
    ]
)
