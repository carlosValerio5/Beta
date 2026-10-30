import BetaKit
import Foundation
import Observation

/// App-wide state: server URL, climber profile, device id and the current climb session.
@MainActor
@Observable
final class AppModel {
    private enum Keys {
        static let apiBaseURL = "beta.apiBaseURL"
        static let profile = "beta.profile"
        static let deviceId = "beta.deviceId"
    }

    static let defaultAPIBaseURL = "http://localhost:8000"

    private(set) var apiBaseURL: String
    private(set) var profile: ClimberProfile
    let deviceId: String
    private(set) var session: ClimbSession

    @ObservationIgnored private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let url = defaults.string(forKey: Keys.apiBaseURL) ?? Self.defaultAPIBaseURL
        let device = defaults.string(forKey: Keys.deviceId) ?? Self.newDeviceId()
        defaults.set(device, forKey: Keys.deviceId)
        apiBaseURL = url
        deviceId = device
        profile = defaults.string(forKey: Keys.profile).flatMap(ClimberProfile.init(rawValue:)) ?? .default
        session = ClimbSession(api: Self.client(url: url, deviceId: device))
    }

    var api: BetaClient { Self.client(url: apiBaseURL, deviceId: deviceId) }

    func setAPIBaseURL(_ value: String) {
        apiBaseURL = value.trimmingCharacters(in: .whitespaces)
        defaults.set(apiBaseURL, forKey: Keys.apiBaseURL)
    }

    func setProfile(_ value: ClimberProfile) {
        profile = value
        defaults.set(value.rawValue, forKey: Keys.profile)
    }

    func newClimb() {
        session = ClimbSession(api: api)
    }

    private static func client(url: String, deviceId: String) -> BetaClient {
        let base = URL(string: url) ?? URL(string: defaultAPIBaseURL)!
        return BetaClient(baseURL: base, deviceId: deviceId)
    }

    private static func newDeviceId() -> String {
        "dev_" + UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(20).lowercased()
    }
}
