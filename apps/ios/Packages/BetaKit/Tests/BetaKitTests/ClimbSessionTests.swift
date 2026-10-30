import Foundation
import Testing
@testable import BetaKit

/// In-memory API built from the contract examples.
actor FakeAPI: BetaAPI {
    var analysis: Analysis
    var readyBeta: Beta
    var readyVideo: Video
    var betaOverride: Beta?
    private(set) var feedback: [(FeedbackKind, Int?)] = []
    private(set) var selections: [ProblemSelection] = []

    init() throws {
        analysis = try Fixtures.decode(Analysis.self, "api/examples/analysis.json")
        readyBeta = try Fixtures.decode(Beta.self, "api/examples/beta.json")
        readyVideo = try Fixtures.decode(Video.self, "api/examples/video.json")
    }

    func failBetas(with message: String) {
        var failed = readyBeta
        failed.status = .failed
        failed.moves = []
        failed.error = message
        betaOverride = failed
    }

    func health() async throws -> Health {
        Health(status: "ok", version: "test", planner: "fake", director: "fake", renderer: true)
    }
    func uploadAnalysis(jpeg: Data, wallHeightCm: Double?) async throws -> Analysis { analysis }
    func analysis(id: String) async throws -> Analysis { analysis }
    func selectProblem(analysisId: String, selection: ProblemSelection) async throws -> Analysis {
        selections.append(selection)
        return analysis
    }
    func requestBeta(analysisId: String, profile: ClimberProfile) async throws -> Beta {
        var pending = readyBeta
        pending.status = .pending
        pending.moves = []
        return pending
    }
    func beta(id: String) async throws -> Beta { betaOverride ?? readyBeta }
    func requestVideo(betaId: String) async throws -> Video {
        var directing = readyVideo
        directing.status = .directing
        directing.videoUrl = nil
        return directing
    }
    func video(id: String) async throws -> Video { readyVideo }
    func sendFeedback(betaId: String, kind: FeedbackKind, moveIndex: Int?, note: String) async throws -> FeedbackReceipt {
        feedback.append((kind, moveIndex))
        return FeedbackReceipt(id: "fbk_1", kind: kind, moveIndex: moveIndex, createdAt: .now)
    }
}

@MainActor
@Suite struct ClimbSessionTests {
    let profile = ClimberProfile(heightCm: 175, apeIndexCm: 0, maxGrade: "V4", style: .balanced)

    func session(_ api: FakeAPI) -> ClimbSession {
        ClimbSession(api: api, poller: Poller(initial: .milliseconds(1), maxInterval: .milliseconds(1), timeout: .seconds(5)) { _ in })
    }

    @Test func happyPathFromPhotoToVideo() async throws {
        let api = try FakeAPI()
        let s = session(api)
        await s.upload(jpeg: Data([0xFF]), wallHeightCm: nil)
        #expect(s.phase == .selecting)
        #expect(s.selection?.holds.isEmpty == false)

        s.selection?.selectColor("yellow")
        await s.confirmProblem(profile: profile)
        #expect(s.phase == .ready)
        #expect(s.beta?.status == .ready)
        #expect(await api.selections.count == 1)

        await s.makeVideo()
        guard case .ready(let video) = s.videoState else {
            Issue.record("video not ready: \(s.videoState)")
            return
        }
        #expect(video.videoUrl != nil)
    }

    @Test func incompleteSelectionIsNotSent() async throws {
        let api = try FakeAPI()
        let s = session(api)
        await s.upload(jpeg: Data([0xFF]), wallHeightCm: nil)
        s.selection?.selectColor("yellow")
        if let top = s.selection?.topId { s.selection?.tap(holdId: top) }  // remove the top hold
        await s.confirmProblem(profile: profile)
        #expect(s.phase == .selecting)
        #expect(s.message != nil)
        #expect(await api.selections.isEmpty)
    }

    @Test func failedBetaSurfacesTheReason() async throws {
        let api = try FakeAPI()
        await api.failBetas(with: "beta failed validation")
        let s = session(api)
        await s.upload(jpeg: Data([0xFF]), wallHeightCm: nil)
        s.selection?.selectColor("yellow")
        await s.confirmProblem(profile: profile)
        #expect(s.phase == .failed("beta failed validation"))
    }

    @Test func feedbackIsForwarded() async throws {
        let api = try FakeAPI()
        let s = session(api)
        await s.upload(jpeg: Data([0xFF]), wallHeightCm: nil)
        s.selection?.selectColor("yellow")
        await s.confirmProblem(profile: profile)
        await s.sendFeedback(.moveLooksWrong, moveIndex: 2)
        let sent = await api.feedback
        #expect(sent.count == 1)
        #expect(sent.first?.0 == .moveLooksWrong)
        #expect(sent.first?.1 == 2)
    }
}
