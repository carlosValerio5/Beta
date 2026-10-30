import Foundation
import Observation

/// View model for one climb: photo → hold review → beta → route video → feedback.
@MainActor
@Observable
public final class ClimbSession {
    public enum Phase: Equatable, Sendable {
        case idle
        case uploading
        case selecting
        case planning
        case ready
        case failed(String)
    }

    public enum VideoState: Equatable, Sendable {
        case none
        case working
        case ready(Video)
        case failed(String)
    }

    public private(set) var phase: Phase = .idle
    public private(set) var analysis: Analysis?
    public var selection: HoldSelection?
    public private(set) var beta: Beta?
    public private(set) var videoState: VideoState = .none
    /// Non-fatal guidance for the current screen (e.g. "mark the top hold").
    public private(set) var message: String?

    private let api: any BetaAPI
    private let poller: Poller

    public init(api: any BetaAPI, poller: Poller = Poller()) {
        self.api = api
        self.poller = poller
    }

    public func upload(jpeg: Data, wallHeightCm: Double?) async {
        phase = .uploading
        message = nil
        do {
            let analysis = try await api.uploadAnalysis(jpeg: jpeg, wallHeightCm: wallHeightCm)
            self.analysis = analysis
            var selection = HoldSelection(holds: analysis.holds)
            if let color = selection.colors.first { selection.selectColor(color) }
            self.selection = selection
            phase = .selecting
        } catch {
            phase = .failed(Self.describe(error))
        }
    }

    public func confirmProblem(profile: ClimberProfile) async {
        guard let analysis, let payload = selection?.problemSelection else {
            message = "Pick the problem's holds, at least one start hold and the top."
            return
        }
        phase = .planning
        message = nil
        let api = self.api
        do {
            _ = try await api.selectProblem(analysisId: analysis.id, selection: payload)
            let id = try await api.requestBeta(analysisId: analysis.id, profile: profile).id
            let done = try await poller.poll(fetch: { try await api.beta(id: id) }, until: { $0.status != .pending })
            beta = done
            phase = done.status == .ready ? .ready : .failed(done.error ?? "The beta could not be generated.")
        } catch {
            phase = .failed(Self.describe(error))
        }
    }

    public func makeVideo() async {
        guard let beta, beta.status == .ready else { return }
        videoState = .working
        let api = self.api
        do {
            let id = try await api.requestVideo(betaId: beta.id).id
            let done = try await poller.poll(fetch: { try await api.video(id: id) }, until: { $0.status.isTerminal })
            switch done.status {
            case .ready: videoState = .ready(done)
            case .directed: videoState = .failed("The server has no video renderer configured.")
            default: videoState = .failed(done.error ?? "The video could not be made.")
            }
        } catch {
            videoState = .failed(Self.describe(error))
        }
    }

    public func sendFeedback(_ kind: FeedbackKind, moveIndex: Int? = nil, note: String = "") async {
        guard let beta else { return }
        do {
            _ = try await api.sendFeedback(betaId: beta.id, kind: kind, moveIndex: moveIndex, note: note)
        } catch {
            message = Self.describe(error)
        }
    }

    public func reset() {
        phase = .idle
        analysis = nil
        selection = nil
        beta = nil
        videoState = .none
        message = nil
    }

    private static func describe(_ error: any Error) -> String {
        if let api = error as? APIError { return api.errorDescription ?? api.code }
        if error is PollingError { return "This is taking longer than expected. Try again in a minute." }
        return error.localizedDescription
    }
}
