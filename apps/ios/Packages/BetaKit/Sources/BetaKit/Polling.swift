import Foundation

public enum PollingError: Error, Equatable, Sendable {
    case timedOut
}

/// Polls a 202-accepted job until it is done (ADR-0008), backing off ×1.5 up to `maxInterval`.
/// `sleep` is injectable so tests run instantly.
public struct Poller: Sendable {
    public let initial: Duration
    public let maxInterval: Duration
    public let timeout: Duration
    private let sleep: @Sendable (Duration) async throws -> Void

    public init(
        initial: Duration = .milliseconds(800),
        maxInterval: Duration = .seconds(4),
        timeout: Duration = .seconds(240),
        sleep: @escaping @Sendable (Duration) async throws -> Void = { try await Task.sleep(for: $0) }
    ) {
        self.initial = initial
        self.maxInterval = maxInterval
        self.timeout = timeout
        self.sleep = sleep
    }

    public func poll<T: Sendable>(
        fetch: @Sendable () async throws -> T,
        until isDone: @Sendable (T) -> Bool
    ) async throws -> T {
        var interval = initial
        var waited: Duration = .zero
        while true {
            let value = try await fetch()
            if isDone(value) { return value }
            if waited + interval > timeout { throw PollingError.timedOut }
            try await sleep(interval)
            waited += interval
            interval = min(interval * 1.5, maxInterval)
        }
    }
}
