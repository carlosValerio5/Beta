import Foundation

// Wire models for the Beta API v1 (apps/api/src/beta_api/schemas.py).
// Checked against contracts/api/examples/*.json by ContractDecodingTests.

public struct Hold: Codable, Sendable, Hashable, Identifiable {
    public var id: Int
    public var x: Double
    public var y: Double
    public var w: Double
    public var h: Double
    public var cx: Double
    public var cy: Double
    public var color: String
    public var type: String
    public var confidence: Double

    public init(
        id: Int, x: Double, y: Double, w: Double, h: Double, cx: Double, cy: Double,
        color: String, type: String, confidence: Double
    ) {
        self.id = id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.cx = cx
        self.cy = cy
        self.color = color
        self.type = type
        self.confidence = confidence
    }

    public var area: Double { w * h }
    public var size: Double { max(w, h) }
}

public struct Problem: Codable, Sendable, Hashable {
    public var color: String?
    public var startHoldIds: [Int]
    public var topHoldId: Int
    public var holdIds: [Int]
}

public struct Analysis: Codable, Sendable, Hashable, Identifiable {
    public var id: String
    public var createdAt: Date
    public var imageUrl: URL
    public var imageWidth: Int
    public var imageHeight: Int
    public var holds: [Hold]
    public var colorGroups: [String: [Int]]
    public var pxPerCm: Double
    public var scaleMethod: String
    public var problem: Problem?
}

public enum JobStatus: String, Codable, Sendable {
    case pending, ready, failed
}

public enum Limb: String, Codable, Sendable, CaseIterable {
    case lh, rh, lf, rf

    public var label: String {
        switch self {
        case .lh: "Left hand"
        case .rh: "Right hand"
        case .lf: "Left foot"
        case .rf: "Right foot"
        }
    }

    public var isHand: Bool { self == .lh || self == .rh }
}

public struct Contacts: Codable, Sendable, Hashable {
    public var lh: Int?
    public var rh: Int?
    public var lf: Int?
    public var rf: Int?
}

public struct Move: Codable, Sendable, Hashable, Identifiable {
    public var index: Int
    public var limb: Limb
    public var holdId: Int
    public var technique: String
    public var cue: String
    public var isCrux: Bool

    public var id: Int { index }
    public var techniqueLabel: String { technique.replacingOccurrences(of: "_", with: " ") }
}

public struct Violation: Codable, Sendable, Hashable {
    public var code: String
    public var message: String
    public var moveIndex: Int?
}

public struct Beta: Codable, Sendable, Hashable, Identifiable {
    public var id: String
    public var analysisId: String
    public var status: JobStatus
    public var start: Contacts?
    public var moves: [Move]
    public var summary: String
    public var grade: String?
    public var gradeFont: String?
    public var confidence: Double?
    public var style: String?
    public var planner: String?
    public var attempts: Int
    public var violations: [Violation]
    public var error: String?
    public var createdAt: Date
    public var updatedAt: Date
}

public enum VideoStatus: String, Codable, Sendable {
    case directing, directed, rendering, ready, failed

    public var isTerminal: Bool { self == .directed || self == .ready || self == .failed }
}

public struct Chapter: Codable, Sendable, Hashable, Identifiable {
    public var moveIndex: Int
    public var title: String
    public var startS: Double

    public init(moveIndex: Int, title: String, startS: Double) {
        self.moveIndex = moveIndex
        self.title = title
        self.startS = startS
    }

    public var id: Int { moveIndex }
}

public struct Video: Codable, Sendable, Hashable, Identifiable {
    public var id: String
    public var betaId: String
    public var status: VideoStatus
    public var videoUrl: URL?
    public var posterUrl: URL?
    public var durationS: Double?
    public var chapters: [Chapter]
    public var error: String?
    public var createdAt: Date
    public var updatedAt: Date
}

public enum FeedbackKind: String, Codable, Sendable {
    case sent
    case useful
    case notUseful = "not_useful"
    case moveLooksWrong = "move_looks_wrong"
    case rewatch
    case watchedToEnd = "watched_to_end"
}

public struct FeedbackReceipt: Codable, Sendable, Hashable {
    public var id: String
    public var kind: FeedbackKind
    public var moveIndex: Int?
    public var createdAt: Date

    public init(id: String, kind: FeedbackKind, moveIndex: Int?, createdAt: Date) {
        self.id = id
        self.kind = kind
        self.moveIndex = moveIndex
        self.createdAt = createdAt
    }
}

public struct Health: Codable, Sendable, Hashable {
    public var status: String
    public var version: String
    public var planner: String
    public var director: String
    public var renderer: Bool

    public init(status: String, version: String, planner: String, director: String, renderer: Bool) {
        self.status = status
        self.version = version
        self.planner = planner
        self.director = director
        self.renderer = renderer
    }
}

// MARK: - Requests

public enum ClimbingStyle: String, Codable, Sendable, CaseIterable {
    case `static`, dynamic, balanced
}

/// Stored with @AppStorage via `RawRepresentable` (a JSON string); encoded explicitly so the
/// stdlib's RawRepresentable Codable defaults never kick in.
public struct ClimberProfile: Codable, Sendable, Hashable, RawRepresentable {
    public var heightCm: Double
    public var apeIndexCm: Double
    public var maxGrade: String
    public var style: ClimbingStyle

    public init(heightCm: Double, apeIndexCm: Double, maxGrade: String, style: ClimbingStyle) {
        self.heightCm = heightCm
        self.apeIndexCm = apeIndexCm
        self.maxGrade = maxGrade
        self.style = style
    }

    public static let `default` = ClimberProfile(heightCm: 175, apeIndexCm: 0, maxGrade: "V3", style: .balanced)

    enum CodingKeys: String, CodingKey { case heightCm, apeIndexCm, maxGrade, style }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        heightCm = try c.decode(Double.self, forKey: .heightCm)
        apeIndexCm = try c.decode(Double.self, forKey: .apeIndexCm)
        maxGrade = try c.decode(String.self, forKey: .maxGrade)
        style = try c.decode(ClimbingStyle.self, forKey: .style)
    }

    public func encode(to encoder: any Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(heightCm, forKey: .heightCm)
        try c.encode(apeIndexCm, forKey: .apeIndexCm)
        try c.encode(maxGrade, forKey: .maxGrade)
        try c.encode(style, forKey: .style)
    }

    public init?(rawValue: String) {
        guard let value = try? BetaJSON.decoder.decode(ClimberProfile.self, from: Data(rawValue.utf8)) else {
            return nil
        }
        self = value
    }

    public var rawValue: String {
        (try? String(decoding: BetaJSON.encoder.encode(self), as: UTF8.self)) ?? "{}"
    }
}

public struct ProblemSelection: Codable, Sendable, Hashable {
    public var startHoldIds: [Int]
    public var topHoldId: Int
    public var holdIds: [Int]?
    public var color: String?

    public init(startHoldIds: [Int], topHoldId: Int, holdIds: [Int]?, color: String?) {
        self.startHoldIds = startHoldIds
        self.topHoldId = topHoldId
        self.holdIds = holdIds
        self.color = color
    }
}

public struct BetaRequestBody: Codable, Sendable {
    public var profile: ClimberProfile
    public init(profile: ClimberProfile) { self.profile = profile }
}

struct FeedbackBody: Codable, Sendable {
    var kind: FeedbackKind
    var moveIndex: Int?
    var note: String
}

// MARK: - JSON

public enum BetaJSON {
    public static var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            if let date = parseDate(text) { return date }
            throw DecodingError.dataCorrupted(
                .init(codingPath: decoder.codingPath, debugDescription: "Unrecognised date \(text)")
            )
        }
        return decoder
    }

    public static var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }

    /// The API emits ISO-8601 UTC, with or without fractional seconds.
    static func parseDate(_ text: String) -> Date? {
        let fractional = Date.ISO8601FormatStyle(includingFractionalSeconds: true)
        return (try? fractional.parse(text)) ?? (try? Date.ISO8601FormatStyle().parse(text))
    }
}
