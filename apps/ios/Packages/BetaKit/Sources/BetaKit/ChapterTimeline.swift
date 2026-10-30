import Foundation

/// Move-by-move navigation inside a route video. Chapter times come from the MotionSpec.
public struct ChapterTimeline: Sendable, Equatable {
    /// Pressing "previous" this soon after a chapter starts goes to the chapter before it.
    public static let restartGrace = 0.5

    public let chapters: [Chapter]
    public let duration: Double

    public init(chapters: [Chapter], duration: Double) {
        self.chapters = chapters.sorted { $0.startS < $1.startS }
        self.duration = duration
    }

    public init(video: Video) {
        let fallback = (video.chapters.map(\.startS).max() ?? 0) + 2
        self.init(chapters: video.chapters, duration: video.durationS ?? fallback)
    }

    /// The chapter playing at `time`, or nil during the opening start pose.
    public func index(at time: Double) -> Int? {
        chapters.lastIndex { $0.startS <= time }
    }

    public func startTime(of index: Int) -> Double {
        chapters[index].startS
    }

    public func next(after time: Double) -> Int? {
        chapters.firstIndex { $0.startS > time + 0.001 }
    }

    public func previous(before time: Double) -> Int? {
        guard let current = index(at: time) else { return nil }
        if time - chapters[current].startS > Self.restartGrace { return current }
        return max(current - 1, 0)
    }

    public func progress(at time: Double) -> Double {
        guard duration > 0 else { return 0 }
        return min(max(time / duration, 0), 1)
    }
}
