import Foundation
@testable import BetaKit

enum Fixtures {
    /// Repository root, found from this file: Tests/BetaKitTests/<file> → … → beta/.
    static let repoRoot: URL = {
        var url = URL(fileURLWithPath: #filePath)
        for _ in 0..<7 { url.deleteLastPathComponent() }
        return url
    }()

    static func contract(_ path: String) throws -> Data {
        try Data(contentsOf: repoRoot.appending(path: "contracts/\(path)"))
    }

    static func decode<T: Decodable>(_ type: T.Type, _ path: String) throws -> T {
        try BetaJSON.decoder.decode(type, from: contract(path))
    }

    static func hold(_ id: Int, cx: Double, cy: Double, color: String = "yellow", size: Double = 40) -> Hold {
        Hold(
            id: id, x: cx - size / 2, y: cy - size / 2, w: size, h: size,
            cx: cx, cy: cy, color: color, type: "unknown", confidence: 1
        )
    }

    /// A small yellow problem: two start jugs, two small footholds, one intermediate, a top; one blue distractor.
    static let holds: [Hold] = [
        hold(0, cx: 450, cy: 1050),
        hold(1, cx: 560, cy: 1050),
        hold(2, cx: 430, cy: 1350, size: 20),
        hold(3, cx: 580, cy: 1350, size: 20),
        hold(4, cx: 420, cy: 930),
        hold(5, cx: 500, cy: 450),
        hold(6, cx: 250, cy: 900, color: "blue"),
    ]
}
