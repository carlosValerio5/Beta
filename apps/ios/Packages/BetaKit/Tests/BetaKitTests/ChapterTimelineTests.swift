import Testing
@testable import BetaKit

@Suite struct ChapterTimelineTests {
    let timeline = ChapterTimeline(
        chapters: [
            Chapter(moveIndex: 0, title: "1. Left hand · reach", startS: 1.5),
            Chapter(moveIndex: 1, title: "2. Right hand · reach", startS: 2.7),
            Chapter(moveIndex: 2, title: "3. Left foot · step", startS: 3.9),
        ],
        duration: 6
    )

    @Test(arguments: [(0.5, nil), (1.5, 0), (3.0, 1), (5.9, 2)] as [(Double, Int?)])
    func chapterAtTime(time: Double, expected: Int?) {
        #expect(timeline.index(at: time) == expected)
    }

    @Test func nextChapter() {
        #expect(timeline.next(after: 0.2) == 0)
        #expect(timeline.next(after: 2.0) == 1)
        #expect(timeline.next(after: 4.5) == nil)
    }

    @Test func previousRestartsOrStepsBack() {
        #expect(timeline.previous(before: 3.5) == 1)  // well into move 2: restart it
        #expect(timeline.previous(before: 3.0) == 0)  // just started move 2: go back to move 1
        #expect(timeline.previous(before: 1.6) == 0)  // nothing earlier
    }

    @Test func progress() {
        #expect(timeline.progress(at: 3.0) == 0.5)
        #expect(timeline.progress(at: 99) == 1)
    }
}
