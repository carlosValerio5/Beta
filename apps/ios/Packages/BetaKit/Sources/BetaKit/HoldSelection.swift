import Foundation

/// State machine behind the hold-review screen: which detected holds form the problem, which are
/// the start holds (1-2) and which is the top.
public struct HoldSelection: Equatable, Sendable {
    public enum Mode: String, CaseIterable, Sendable {
        case pick, start, top
    }

    public let holds: [Hold]
    public private(set) var selected: Set<Int> = []
    public private(set) var startIds: [Int] = []
    public private(set) var topId: Int?
    public var mode: Mode = .pick

    public init(holds: [Hold]) {
        self.holds = holds
    }

    /// Colours present, most common first — the chips at the bottom of the screen.
    public var colors: [String] {
        let counts = Dictionary(grouping: holds, by: \.color).mapValues(\.count)
        return counts.keys.sorted { (counts[$0]!, $1) > (counts[$1]!, $0) }
    }

    /// Select every hold of a colour and suggest the top (highest) and starts (lowest hand-sized).
    public mutating func selectColor(_ color: String) {
        let group = holds.filter { $0.color == color }
        selected = Set(group.map(\.id))
        mode = .pick
        topId = group.min { $0.cy < $1.cy }?.id
        let areas = group.map(\.area).sorted()
        let median = areas.isEmpty ? 0 : areas[areas.count / 2]
        startIds = group
            .filter { $0.id != topId && $0.area >= 0.6 * median }
            .sorted { $0.cy > $1.cy }
            .prefix(2)
            .sorted { $0.cx < $1.cx }
            .map(\.id)
    }

    public mutating func tap(holdId: Int) {
        switch mode {
        case .pick:
            if selected.contains(holdId) {
                selected.remove(holdId)
                startIds.removeAll { $0 == holdId }
                if topId == holdId { topId = nil }
            } else {
                selected.insert(holdId)
            }
        case .start:
            selected.insert(holdId)
            if topId == holdId { topId = nil }
            if startIds.contains(holdId) {
                startIds.removeAll { $0 == holdId }
            } else {
                startIds.append(holdId)
                if startIds.count > 2 { startIds.removeFirst() }
            }
        case .top:
            selected.insert(holdId)
            topId = holdId
            startIds.removeAll { $0 == holdId }
        }
    }

    /// The hold under a tap (image pixels), with a little slack for fingers.
    public func hold(atX x: Double, y: Double) -> Hold? {
        holds
            .filter { h in
                let slack = max(12, h.size * 0.25)
                return x >= h.x - slack && x <= h.x + h.w + slack && y >= h.y - slack && y <= h.y + h.h + slack
            }
            .min { hypot($0.cx - x, $0.cy - y) < hypot($1.cx - x, $1.cy - y) }
    }

    public var isComplete: Bool {
        !startIds.isEmpty && topId != nil && selected.count >= 2
    }

    public var problemSelection: ProblemSelection? {
        guard isComplete, let topId else { return nil }
        let colors = Set(holds.filter { selected.contains($0.id) }.map(\.color))
        return ProblemSelection(
            startHoldIds: startIds,
            topHoldId: topId,
            holdIds: selected.sorted(),
            color: colors.count == 1 ? colors.first : nil
        )
    }
}
