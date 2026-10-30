import BetaKit
import SwiftUI

struct ProfileView: View {
    @Environment(AppModel.self) private var model
    @State private var connection: String?

    private static let grades = ["VB"] + (0...12).map { "V\($0)" }

    var body: some View {
        NavigationStack {
            Form {
                Section("Your body") {
                    Stepper(
                        "Height: \(Int(model.profile.heightCm)) cm",
                        value: binding(\.heightCm),
                        in: 120...230
                    )
                    Stepper(
                        "Ape index: \(model.profile.apeIndexCm >= 0 ? "+" : "")\(Int(model.profile.apeIndexCm)) cm",
                        value: binding(\.apeIndexCm),
                        in: -20...30
                    )
                    Text("Ape index is your wingspan minus your height.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("Climbing") {
                    Picker("Hardest grade", selection: binding(\.maxGrade)) {
                        ForEach(Self.grades, id: \.self) { Text($0).tag($0) }
                    }
                    Picker("Style", selection: binding(\.style)) {
                        ForEach(ClimbingStyle.allCases, id: \.self) { Text($0.rawValue.capitalized).tag($0) }
                    }
                }

                Section("Server") {
                    TextField(
                        "API URL",
                        text: Binding(get: { model.apiBaseURL }, set: { model.setAPIBaseURL($0) })
                    )
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    Button("Check connection") {
                        Task {
                            do {
                                let health = try await model.api.health()
                                connection = "Connected · planner \(health.planner)" + (health.renderer ? " · videos on" : "")
                            } catch {
                                connection = error.localizedDescription
                            }
                        }
                    }
                    if let connection { Text(connection).font(.footnote) }
                }

                Section {
                    Text(
                        "Beta suggests movement; it cannot see everything you can on the wall. Climb within " +
                        "your ability, check landings and pads, and treat every beta as a hypothesis."
                    )
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Profile")
        }
    }

    private func binding<T>(_ keyPath: WritableKeyPath<ClimberProfile, T>) -> Binding<T> {
        Binding(
            get: { model.profile[keyPath: keyPath] },
            set: { value in
                var profile = model.profile
                profile[keyPath: keyPath] = value
                model.setProfile(profile)
            }
        )
    }
}
